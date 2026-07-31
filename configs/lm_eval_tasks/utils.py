"""
Hàm hỗ trợ cho task VMLU trong lm-eval.

Viết PHÒNG THỦ: schema VMLU giữa các bản phát hành có khác nhau về tên cột
(`choices` vs `A/B/C/D` rời, `answer` vs `answer_key`). Thay vì đoán, ta dò
tại chỗ. Chạy `python scripts/02b_inspect_vmlu.py` để in schema thật trước
khi tin vào file này.
"""

from __future__ import annotations

LETTERS = ["A", "B", "C", "D", "E"]


def _choices(doc: dict) -> list[str]:
    """Trả về danh sách phương án, đã bỏ tiền tố 'A. ' nếu có."""
    raw = doc.get("choices")
    if raw is None:
        raw = [doc[k] for k in LETTERS if k in doc and doc[k] is not None]
    if isinstance(raw, str):
        raw = [l.strip() for l in raw.splitlines() if l.strip()]
    out = []
    for i, c in enumerate(raw):
        c = str(c).strip()
        for pref in (f"{LETTERS[i]}. ", f"{LETTERS[i]}) ", f"{LETTERS[i]}.", f"{LETTERS[i]})"):
            if c.startswith(pref):
                c = c[len(pref):].strip()
                break
        out.append(c)
    return out


def doc_to_text(doc: dict) -> str:
    """Prompt tiếng Việt. Giữ nguyên văn phong bản địa — KHÔNG dịch sang tiếng Anh.

    Lý do: prompt tiếng Anh cho câu hỏi tiếng Việt tạo ra hiệu ứng chuyển ngữ
    và làm nhiễu chính hiện tượng đề tài đang đo.
    """
    lines = [f"Câu hỏi: {str(doc.get('question', '')).strip()}"]
    for letter, choice in zip(LETTERS, _choices(doc)):
        lines.append(f"{letter}. {choice}")
    lines.append("Đáp án:")
    return "\n".join(lines)


def doc_to_choice(doc: dict) -> list[str]:
    return [f" {l}" for l in LETTERS[: len(_choices(doc))]]


def doc_to_target(doc: dict) -> int:
    ans = doc.get("answer", doc.get("answer_key", doc.get("label")))
    if ans is None:
        raise KeyError(f"không tìm thấy cột đáp án trong: {sorted(doc)}")
    if isinstance(ans, int):
        return ans
    ans = str(ans).strip().upper()
    if ans and ans[0] in LETTERS:
        return LETTERS.index(ans[0])
    if ans.isdigit():
        return int(ans)
    raise ValueError(f"không đọc được đáp án: {ans!r}")


def process_docs(dataset):
    """Giữ nguyên; chỗ này để lọc/chuẩn hoá nếu bản VMLU có mẫu hỏng."""
    return dataset