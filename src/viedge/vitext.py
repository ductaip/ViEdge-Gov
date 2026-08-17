"""
Tiện ích xử lý tiếng Việt dùng chung cho toàn bộ pipeline.

Điểm quan trọng về phương pháp: mọi thứ ở đây là *không có từ điển ngoài*.
Từ vựng tham chiếu được dựng từ chính kho văn bản pháp luật (vốn đã được
gõ đúng dấu), nên phép đo không phụ thuộc một nguồn từ điển bên thứ ba mà
hội đồng có thể chất vấn về chất lượng.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable

# ---------------------------------------------------------------------------
# Dấu tiếng Việt
# ---------------------------------------------------------------------------

# Các ký tự nguyên âm/phụ âm mang dấu của tiếng Việt (đã dựng sẵn, NFC).
VN_DIACRITIC_CHARS = set(
    "àáảãạăằắẳẵặâầấẩẫậ"
    "èéẻẽẹêềếểễệ"
    "ìíỉĩị"
    "òóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữự"
    "ỳýỷỹỵ"
    "đ"
)
VN_DIACRITIC_CHARS |= {c.upper() for c in VN_DIACRITIC_CHARS}

# Dấu thanh dạng combining (xuất hiện sau khi NFD).
COMBINING_MARKS = {
    "\u0300",  # huyền
    "\u0301",  # sắc
    "\u0303",  # ngã
    "\u0309",  # hỏi
    "\u0323",  # nặng
    "\u0302",  # dấu mũ
    "\u0306",  # dấu breve (ă)
    "\u031b",  # dấu horn (ơ, ư)
}

WORD_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)

# Dấu hiệu vỡ mã hoá.
#
# Cách phát hiện gồm hai lớp, vì mojibake do lượng tử hoá thường là VỠ MỘT PHẦN
# (lẫn ký tự đúng và ký tự vỡ trong cùng câu), khác với mojibake do đọc sai file
# (vỡ toàn bộ, round-trip được):
#   lớp 1 — round-trip: nếu encode latin-1 rồi decode utf-8 ra văn bản có tỉ lệ
#           dấu CAO HƠN, thì bản gốc là mojibake toàn phần.
#   lớp 2 — bigram: một ký tự mang dấu tiếng Việt đứng ngay trước một ký tự
#           dấu câu/ký hiệu vùng Latin-1 (vd. "á" + "»") gần như không bao giờ
#           là tiếng Việt hợp lệ. Bắt được ca vỡ một phần.
REPLACEMENT_CHAR = "\ufffd"

# Vùng U+00A0–U+00BF: dấu câu và ký hiệu Latin-1 (», «, ¡, £, ©, ...).
LATIN1_PUNCT = "".join(chr(c) for c in range(0xA0, 0xC0))

# Tiền tố kinh điển của UTF-8 bị đọc thành Latin-1/CP1252.
MOJIBAKE_LEAD = "ÃÂÆÄÅÐÑ"

_MOJI_BIGRAM_RE = re.compile(
    f"[{re.escape(''.join(sorted(VN_DIACRITIC_CHARS)) + MOJIBAKE_LEAD)}]"
    f"[{re.escape(LATIN1_PUNCT)}]"
)
_MOJI_LEAD_RE = re.compile(f"[{re.escape(MOJIBAKE_LEAD)}][{re.escape(LATIN1_PUNCT)}\u0080-\u009f]")


def demojibake(text: str) -> str | None:
    """Thử phục hồi văn bản bị đọc sai mã hoá. None nếu không phải mojibake toàn phần."""
    try:
        cand = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None
    return cand if cand != text else None

# Khối chữ viết không thuộc tiếng Việt — tín hiệu chuyển ngữ ngoài ý muốn (E5).
FOREIGN_SCRIPT_RE = re.compile(
    "["
    "\u3040-\u30ff"  # hiragana / katakana
    "\u3400-\u4dbf"  # CJK ext A
    "\u4e00-\u9fff"  # CJK
    "\uac00-\ud7af"  # hangul
    "\u0400-\u04ff"  # cyrillic
    "\u0e00-\u0e7f"  # thai
    "\u0600-\u06ff"  # arabic
    "]"
)

# Từ chức năng tiếng Anh hay lọt vào giữa câu tiếng Việt.
EN_FUNCTION_WORDS = {
    "the", "and", "of", "to", "in", "is", "are", "that", "this", "with",
    "for", "as", "was", "be", "have", "has", "you", "your", "which",
    "according", "therefore", "however", "please", "note", "answer",
    "question", "based", "following", "must", "should", "can", "will",
}


def strip_marks(text: str) -> str:
    """Bỏ toàn bộ dấu tiếng Việt, giữ nguyên chữ cái gốc (ASCII fold)."""
    decomposed = unicodedata.normalize("NFD", text)
    out = []
    for ch in decomposed:
        if ch in COMBINING_MARKS:
            continue
        if ch in ("đ", "Đ"):
            out.append("d" if ch == "đ" else "D")
            continue
        out.append(ch)
    folded = unicodedata.normalize("NFC", "".join(out))
    return folded.replace("đ", "d").replace("Đ", "D")


def fold(text: str) -> str:
    """Chuẩn hoá để so khớp: bỏ dấu + hạ chữ thường."""
    return strip_marks(text).lower()


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def diacritic_ratio(text: str) -> float:
    """Tỉ lệ ký tự mang dấu trên tổng ký tự chữ cái.

    Đây là chỉ số nền cho E2 (mất dấu). Văn bản pháp luật tiếng Việt chuẩn
    thường rơi vào khoảng 0.18-0.30; tụt sâu dưới ngưỡng đó là tín hiệu.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    marked = sum(1 for c in letters if c in VN_DIACRITIC_CHARS)
    return marked / len(letters)


def mojibake_hits(text: str) -> list[str]:
    """Bằng chứng vỡ mã hoá (E1). Rỗng = sạch."""
    hits: list[str] = []

    if REPLACEMENT_CHAR in text:
        hits.append(f"U+FFFD x{text.count(REPLACEMENT_CHAR)}")

    # Ký tự điều khiển (trừ tab/newline/CR).
    for ch in text:
        if unicodedata.category(ch) == "Cc" and ch not in "\t\n\r":
            hits.append(f"ctrl {ch!r}")

    # Lớp 1 — round-trip.
    fixed = demojibake(text)
    if fixed is not None and diacritic_ratio(fixed) > diacritic_ratio(text) + 0.02:
        hits.append(f"round-trip: {fixed[:40]!r}")

    # Lớp 2 — bigram vỡ một phần.
    hits.extend(f"bigram {m.group(0)!r}" for m in _MOJI_BIGRAM_RE.finditer(text))
    hits.extend(f"lead {m.group(0)!r}" for m in _MOJI_LEAD_RE.finditer(text))

    # Loại trùng nhưng giữ thứ tự để log đọc được.
    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def foreign_script_hits(text: str) -> list[str]:
    return [m.group(0) for m in FOREIGN_SCRIPT_RE.finditer(text)]


def english_run_hits(text: str, min_run: int = 3) -> list[str]:
    """Chuỗi >= min_run từ chức năng tiếng Anh liền nhau (E5)."""
    toks = [w.lower() for w in words(text)]
    hits, run = [], []
    for tok in toks:
        if tok in EN_FUNCTION_WORDS:
            run.append(tok)
        else:
            if len(run) >= min_run:
                hits.append(" ".join(run))
            run = []
    if len(run) >= min_run:
        hits.append(" ".join(run))
    return hits


def max_ngram_repeat(text: str, n: int = 5) -> float:
    """Tỉ lệ lặp n-gram cao nhất — chỉ số suy sụp mạch lạc (E6).

    1.0 nghĩa là toàn bộ văn bản chỉ là một n-gram lặp lại.
    """
    toks = words(text.lower())
    if len(toks) < n * 2:
        return 0.0
    grams = [tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)]
    counts = Counter(grams)
    return counts.most_common(1)[0][1] / len(grams)


def max_line_repeat(text: str, min_lines: int = 5) -> float:
    """Tỉ lệ dòng lặp lại y hệt — bắt lặp CỤM DÀI (cả câu/đoạn) mà
    max_ngram_repeat (cửa sổ 5 từ) bỏ sót.

    PHÁT HIỆN THẬT trên dữ liệu RQ2 (qwen2.5-1.5b-it@int8, mẫu A001): một câu
    ~16 từ lặp lại 62/67 dòng (92,5%) — suy sụp mạch lạc rõ ràng. Nhưng chu kỳ
    lặp (16 từ) dài hơn cửa sổ đo của max_ngram_repeat (5 từ), nên không có
    5-gram đơn lẻ nào chiếm đa số: tỉ lệ đo được chỉ 5,1%, dưới hẳn ngưỡng 15%.
    Đo theo DÒNG thay vì cụm-5-từ-cố-định thì bắt đúng ngay lập tức.

    Hai chỉ số bổ sung cho nhau, không thay thế nhau: max_ngram_repeat mạnh
    với vòng lặp NGẮN (2-4 từ, chu kỳ nhỏ hơn cửa sổ); max_line_repeat mạnh
    với vòng lặp DÀI (nguyên câu/đoạn, chu kỳ lớn hơn cửa sổ 5 từ).
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < min_lines:
        return 0.0
    counts = Counter(lines)
    return counts.most_common(1)[0][1] / len(lines)


def looks_truncated(text: str) -> bool:
    """Câu cụt: không kết thúc bằng dấu câu kết thúc."""
    stripped = text.rstrip()
    if not stripped:
        return True
    return stripped[-1] not in ".!?:;)\"'”’…"


# ---------------------------------------------------------------------------
# Từ vựng tham chiếu dựng từ kho văn bản
# ---------------------------------------------------------------------------


@dataclass
class VietLexicon:
    """Bản đồ dạng-bỏ-dấu -> các dạng có dấu thật gặp trong kho văn bản.

    Dùng để phát hiện mất dấu (E2) mà không cần từ điển ngoài:
    nếu output chứa dạng bỏ dấu `phuong` mà trong toàn bộ kho văn bản
    `phuong` chỉ từng xuất hiện dưới dạng `phương` / `phường`, thì
    `phuong` trong output là dấu hiệu mất dấu.
    """

    folded_to_surfaces: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    surface_counts: Counter = field(default_factory=Counter)

    @classmethod
    def from_texts(cls, texts: Iterable[str]) -> "VietLexicon":
        lex = cls()
        for text in texts:
            for w in words(text):
                lw = w.lower()
                lex.surface_counts[lw] += 1
                lex.folded_to_surfaces[fold(w)].add(lw)
        return lex

    def is_bare_form_suspicious(self, token: str, min_support: int = 2) -> bool:
        """True nếu `token` là dạng bỏ dấu của một từ mà kho văn bản luôn viết có dấu."""
        lw = token.lower()
        if any(c in VN_DIACRITIC_CHARS for c in lw):
            return False  # đã có dấu -> không phải mất dấu
        surfaces = self.folded_to_surfaces.get(lw)
        if not surfaces:
            return False  # từ lạ, không kết luận
        if lw in surfaces and self.surface_counts[lw] >= min_support:
            return False  # dạng không dấu là hợp lệ trong kho (vd. tên viết tắt)
        marked = {s for s in surfaces if any(c in VN_DIACRITIC_CHARS for c in s)}
        return bool(marked)

    def tone_loss_tokens(self, text: str, min_support: int = 2) -> list[str]:
        return [w for w in words(text) if self.is_bare_form_suspicious(w, min_support)]

    def __len__(self) -> int:  # pragma: no cover - tiện debug
        return len(self.folded_to_surfaces)
