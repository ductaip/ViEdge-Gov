"""Pipeline trợ lý: truy hồi -> sinh -> kiểm trích dẫn."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from viedge.data.amendments import AmendmentIndex, augment_context
from viedge.rag import citations as cit
from viedge.rag.retrieval import HybridRetriever

DISCLAIMER = (
    "Kết quả chỉ mang tính tham khảo, không thay thế văn bản quy phạm pháp luật "
    "hiện hành. Vui lòng đối chiếu điều khoản được trích dẫn."
)

SYSTEM_PROMPT = """Bạn là trợ lý tra cứu thủ tục hành chính và pháp luật giao thông đường bộ Việt Nam.

QUY TẮC BẮT BUỘC:
1. Chỉ trả lời dựa trên các điều luật được cung cấp trong phần NGỮ CẢNH. Không suy đoán.
2. Mọi khẳng định phải kèm trích dẫn theo dạng: (Điều <số>, khoản <số>, <tên văn bản>).
3. Nếu NGỮ CẢNH không đủ căn cứ, trả lời đúng câu: "Không đủ căn cứ trong văn bản được cung cấp."
4. Không nêu số hiệu văn bản nào không xuất hiện trong NGỮ CẢNH.
5. Nếu một điều luật có kèm khối [SỬA ĐỔI], nội dung sửa đổi là nội dung ĐANG
   có hiệu lực. Trả lời theo bản sửa đổi và trích dẫn CẢ HAI văn bản.
6. Trả lời bằng tiếng Việt có dấu đầy đủ, ngắn gọn."""


class Generator(Protocol):
    def __call__(self, system: str, user: str) -> str: ...


@dataclass
class Answer:
    text: str
    retrieved: list[str] = field(default_factory=list)
    verdict: cit.CitationVerdict | None = None
    blocked: bool = False
    block_reason: str = ""

    def render(self) -> str:
        body = self.text if not self.blocked else (
            "Không đủ căn cứ đáng tin cậy để trả lời câu hỏi này.\n"
            f"(Lý do hệ thống chặn: {self.block_reason})"
        )
        return f"{body}\n\n---\n{DISCLAIMER}"


@dataclass
class Assistant:
    retriever: HybridRetriever
    generator: Generator
    index: cit.CitationIndex
    unit_text: dict[str, str]
    block_on_bad_citation: bool = True
    max_context_chars: int = 6000

    def _context(self, unit_ids: list[str]) -> str:
        parts, total = [], 0
        for uid in unit_ids:
            t = self.unit_text.get(uid, "")
            if not t:
                continue
            if total + len(t) > self.max_context_chars:
                break
            parts.append(t)
            total += len(t)
        return "\n\n".join(parts)

    def answer(self, question: str) -> Answer:
        hits = self.retriever.retrieve(question)
        unit_ids = [d for d, _ in hits]
        if not unit_ids:
            return Answer(
                text="", retrieved=[], blocked=True,
                block_reason="không tìm thấy điều luật liên quan",
            )
        user = f"NGỮ CẢNH:\n{self._context(unit_ids)}\n\nCÂU HỎI: {question}"
        raw = self.generator(SYSTEM_PROMPT, user)
        verdict = cit.check_answer(raw, self.index, require_citation=True)
        ans = Answer(text=raw, retrieved=unit_ids, verdict=verdict)
        if self.block_on_bad_citation and not verdict.ok:
            ans.blocked = True
            ans.block_reason = (
                f"phát hiện {len(verdict.unknown)} trích dẫn không tồn tại"
                if verdict.unknown else "câu trả lời không kèm căn cứ pháp lý"
            )
        return ans
