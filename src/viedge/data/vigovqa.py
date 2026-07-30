"""
ViGovQA-GT: bộ đánh giá tự xây (thủ tục hành chính + pháp luật giao thông).

Đây là sản phẩm chuyển giao số 1 của đề tài. Phát hành mở kèm DOI Zenodo
biến "dữ liệu nội bộ" thành "kết quả chuyển giao" — trực tiếp ăn vào hạng
mục 20 điểm "giải pháp, kiến nghị có giá trị" của rubric Euréka.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

QUESTION_TYPES = {"muc_phat", "thu_tuc", "y_nghia_bien_bao", "dieu_kien"}
DIFFICULTIES = {"single_hop", "multi_hop"}
SOURCES = {"real_forum", "synthesized"}


@dataclass
class CitationRef:
    doc: str
    dieu: str
    khoan: str = ""
    diem: str = ""

    def unit_id(self) -> str:
        return f"{self.doc}::dieu-{self.dieu}"


@dataclass
class QAItem:
    id: str
    question: str
    answer_reference: str
    citations: list[CitationRef] = field(default_factory=list)
    question_type: str = "thu_tuc"
    difficulty: str = "single_hop"
    source_of_question: str = "synthesized"
    annotator_a: str = ""
    annotator_b: str = ""
    resolved: bool = False
    notes: str = ""

    def gold_units(self) -> list[str]:
        return sorted({c.unit_id() for c in self.citations})

    def to_dict(self) -> dict:
        return asdict(self)


def validate(item: dict) -> list[str]:
    """Trả về danh sách lỗi. Rỗng = hợp lệ. Dùng trong CI để chặn dữ liệu rác."""
    errs: list[str] = []
    for f in ("id", "question", "answer_reference"):
        if not str(item.get(f, "")).strip():
            errs.append(f"thiếu trường bắt buộc: {f}")
    if item.get("question_type") not in QUESTION_TYPES:
        errs.append(f"question_type không hợp lệ: {item.get('question_type')}")
    if item.get("difficulty") not in DIFFICULTIES:
        errs.append(f"difficulty không hợp lệ: {item.get('difficulty')}")
    if item.get("source_of_question") not in SOURCES:
        errs.append(f"source_of_question không hợp lệ: {item.get('source_of_question')}")
    cits = item.get("citations") or []
    if not cits:
        errs.append("không có trích dẫn — mọi câu phải truy được về điều/khoản gốc")
    for i, c in enumerate(cits):
        if not str(c.get("doc", "")).strip():
            errs.append(f"citations[{i}] thiếu doc")
        if not str(c.get("dieu", "")).strip():
            errs.append(f"citations[{i}] thiếu dieu")
    if item.get("difficulty") == "multi_hop" and len(cits) < 2:
        errs.append("multi_hop nhưng chỉ có 1 trích dẫn")
    q = str(item.get("question", ""))
    if q and not q.rstrip().endswith("?"):
        errs.append("câu hỏi không kết thúc bằng dấu ?")
    return errs


def load(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save(items: list[dict], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def dataset_stats(items: list[dict]) -> dict:
    from collections import Counter
    return {
        "n_items": len(items),
        "by_type": dict(Counter(i.get("question_type") for i in items)),
        "by_difficulty": dict(Counter(i.get("difficulty") for i in items)),
        "by_source": dict(Counter(i.get("source_of_question") for i in items)),
        "avg_citations": round(
            sum(len(i.get("citations") or []) for i in items) / len(items), 2
        ) if items else 0,
        "pct_resolved": round(
            100 * sum(1 for i in items if i.get("resolved")) / len(items), 1
        ) if items else 0,
    }
