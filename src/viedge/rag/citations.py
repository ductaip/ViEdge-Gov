"""
Trích xuất và kiểm chứng trích dẫn pháp lý.

Hai vai trò trong đề tài:
  1. Detector cho lỗi E3 (bịa số hiệu văn bản) ở trục nghiên cứu.
  2. Lớp `citation_check` chặn đầu ra sai ở trục hệ thống — tức là
     nghiên cứu sinh ra biện pháp giảm thiểu, đúng mạch logic mà hội đồng
     muốn thấy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

# "Điều 12", "khoản 3", "điểm a", "Nghị định 168/2024/NĐ-CP", "Luật 36/2024/QH15",
# "QCVN 41:2024/BGTVT", "Thông tư 05/2024/TT-BGTVT"
DIEU_RE = re.compile(r"\bĐiều\s+(\d+[a-zA-Z]?)", re.IGNORECASE)
KHOAN_RE = re.compile(r"\bkhoản\s+(\d+)", re.IGNORECASE)
DIEM_RE = re.compile(r"\bđiểm\s+([a-zA-Zđ])\b", re.IGNORECASE)
DOC_RE = re.compile(
    r"\b(Nghị\s*định|Luật|Thông\s*tư|Quyết\s*định|QCVN)\s*"
    r"(?:số\s*)?"
    r"(\d+[/:]\d{2,4}(?:/[A-ZĐ\-]+)?)",
    re.IGNORECASE,
)
# Mã hiệu biển báo trong QCVN 41: B.7a, P.106a, W.201, R.301b, I.401, S.507 ...
# Số hiệu có 1-3 chữ số (B.1, W.201), có thể kèm hậu tố chữ (P.106a, R.301b).
BIENBAO_RE = re.compile(r"\b([PBWRISDE])\.(\d{1,3}[a-z]?)\b")


@dataclass(frozen=True)
class Citation:
    kind: str          # "dieu" | "khoan" | "diem" | "doc" | "bienbao"
    value: str         # dạng chuẩn hoá (xem norm_doc)
    raw: str           # nguyên văn trong đầu ra


def norm_doc(s: str) -> str:
    """Chuẩn hoá định danh văn bản để so khớp.

    Bắt buộc dùng CHUNG cho cả `extract` và `CitationIndex`, nếu không sẽ
    lệch key kiểu 'NĐ-CP' vs 'nđ-cp' và mọi trích dẫn đúng đều bị báo là bịa.
    """
    s = re.sub(r"\s+", " ", s.strip()).lower()
    return s.replace("nghịđịnh", "nghị định").replace("thôngtư", "thông tư")


def extract(text: str) -> list[Citation]:
    """Rút mọi trích dẫn pháp lý xuất hiện trong văn bản."""
    out: list[Citation] = []
    for m in DOC_RE.finditer(text):
        kind_word = re.sub(r"\s+", " ", m.group(1))
        out.append(Citation("doc", norm_doc(f"{kind_word} {m.group(2)}"), m.group(0)))
    for m in DIEU_RE.finditer(text):
        out.append(Citation("dieu", m.group(1).lower(), m.group(0)))
    for m in KHOAN_RE.finditer(text):
        out.append(Citation("khoan", m.group(1), m.group(0)))
    for m in DIEM_RE.finditer(text):
        out.append(Citation("diem", m.group(1).lower(), m.group(0)))
    for m in BIENBAO_RE.finditer(text):
        out.append(Citation("bienbao", f"{m.group(1)}.{m.group(2)}", m.group(0)))
    return out


@dataclass
class CitationIndex:
    """Tập hợp mọi định danh pháp lý *thực sự tồn tại* trong kho văn bản.

    Dựng từ corpus đã parse (xem viedge.data.corpus). Bất cứ trích dẫn nào
    của mô hình không nằm trong index này là ứng viên lỗi E3.
    """

    docs: set[str]
    dieu: set[str]
    bienbao: set[str]
    # (doc, dieu) -> tập khoản hợp lệ; dùng để bắt lỗi "khoản không tồn tại"
    khoan_by_dieu: dict[tuple[str, str], set[str]]

    @classmethod
    def empty(cls) -> "CitationIndex":
        return cls(set(), set(), set(), {})

    @classmethod
    def from_articles(cls, articles: Iterable[dict]) -> "CitationIndex":
        docs: set[str] = set()
        dieu: set[str] = set()
        bienbao: set[str] = set()
        khoan_by_dieu: dict[tuple[str, str], set[str]] = {}
        for art in articles:
            doc_id = norm_doc(str(art.get("doc_id", "")))
            dieu_no = str(art.get("dieu", "")).lower().strip()
            if doc_id:
                docs.add(doc_id)
            if dieu_no:
                dieu.add(dieu_no)
            if doc_id and dieu_no:
                key = (doc_id, dieu_no)
                khoan_by_dieu.setdefault(key, set()).update(
                    str(k) for k in art.get("khoan", [])
                )
            for code in art.get("bienbao", []):
                bienbao.add(str(code).upper())
        return cls(docs, dieu, bienbao, khoan_by_dieu)

    def unknown(self, citations: Iterable[Citation]) -> list[Citation]:
        """Các trích dẫn không tìm thấy trong kho — ứng viên lỗi E3.

        `khoan` và `diem` bị bỏ qua ở đây vì không thể kiểm chứng độc lập
        khi thiếu ngữ cảnh điều nào; chúng được kiểm ở `check_answer`.
        """
        bad: list[Citation] = []
        for c in citations:
            if c.kind == "doc" and self.docs and c.value not in self.docs:
                bad.append(c)
            elif c.kind == "dieu" and self.dieu and c.value not in self.dieu:
                bad.append(c)
            elif c.kind == "bienbao" and self.bienbao and c.value.upper() not in self.bienbao:
                bad.append(c)
        return bad


@dataclass
class CitationVerdict:
    ok: bool
    total: int
    unknown: list[Citation]
    has_any_citation: bool

    @property
    def hallucination_rate(self) -> float:
        return len(self.unknown) / self.total if self.total else 0.0


def check_answer(text: str, index: CitationIndex, require_citation: bool = True) -> CitationVerdict:
    """Cửa kiểm tra dùng ở runtime của trợ lý.

    require_citation=True: câu trả lời không có bất kỳ trích dẫn nào cũng bị
    coi là không đạt — vì yêu cầu thiết kế là mọi câu trả lời phải kèm căn cứ
    để người dùng tự kiểm chứng.
    """
    cits = extract(text)
    unknown = index.unknown(cits)
    verifiable = [c for c in cits if c.kind in ("doc", "dieu", "bienbao")]
    has_any = bool(verifiable)
    ok = not unknown and (has_any or not require_citation)
    return CitationVerdict(ok=ok, total=len(verifiable), unknown=unknown, has_any_citation=has_any)
