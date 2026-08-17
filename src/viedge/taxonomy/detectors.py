"""
Detector tự động cho taxonomy lỗi E1-E6.

QUAN TRỌNG VỀ PHƯƠNG PHÁP — đọc trước khi viết báo cáo:

Các detector ở đây KHÔNG phải nhãn cuối cùng. Chúng là lớp *triage*:
chạy trên toàn bộ đầu ra để có phân bố quy mô lớn, đồng thời chọn mẫu cho
người gán nhãn. Nhãn dùng trong kết luận của đề tài là nhãn NGƯỜI, trên mẫu
ngẫu nhiên, có báo cáo AC1.

Lý do phải làm vậy: tài liệu đã chỉ ra chỉ số tự động đánh giá thấp nghiêm
trọng mức thiệt hại của lượng tử hoá (Marchisio et al., 2024) — nếu ta chỉ
dùng detector, ta lặp lại chính sai lầm mà đề tài đang phê phán.

Trong báo cáo phải có bảng: độ khớp giữa detector và nhãn người (precision/
recall của từng detector). Đó vừa là kiểm định công cụ, vừa là một đóng góp
nhỏ tự thân.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from viedge import vitext
from viedge.rag import citations as cit

# Cặp thuật ngữ hành chính dễ bị nhầm — mỗi cặp khác nhau về thủ tục,
# hồ sơ hoặc mức phí, nên nhầm là sai thực chất chứ không phải sai văn phong.
# Bổ sung thêm khi gặp trong pilot; mỗi lần bổ sung phải ghi vào WEEKLOG.
ADMIN_CONFUSION_PAIRS: list[tuple[str, str]] = [
    ("cấp đổi", "cấp lại"),
    ("tạm giữ", "tước quyền sử dụng"),
    ("phạt tiền", "phạt bổ sung"),
    ("giấy phép lái xe", "giấy đăng ký xe"),
    ("đăng ký lần đầu", "đăng ký sang tên"),
    ("kiểm định", "đăng kiểm lại"),
    ("biển số định danh", "biển số trúng đấu giá"),
]

E_LABELS = {
    "E1": "Vỡ dấu / mojibake",
    "E2": "Mất dấu hoặc sai dấu thanh",
    "E3": "Bịa số hiệu văn bản / trích dẫn không tồn tại",
    "E4": "Sai thuật ngữ hành chính",
    "E5": "Chuyển ngữ ngoài ý muốn",
    "E6": "Suy sụp mạch lạc",
}


@dataclass
class Signals:
    """Tín hiệu thô cho một đầu ra. Mọi ngưỡng nằm ở `flags`, không ở đây."""

    n_chars: int = 0
    n_words: int = 0
    diacritic_ratio: float = 0.0
    mojibake_hits: list[str] = field(default_factory=list)
    tone_loss_tokens: list[str] = field(default_factory=list)
    unknown_citations: list[str] = field(default_factory=list)
    n_citations: int = 0
    confusion_terms: list[str] = field(default_factory=list)
    foreign_script: list[str] = field(default_factory=list)
    english_runs: list[str] = field(default_factory=list)
    max_ngram_repeat: float = 0.0
    max_line_repeat: float = 0.0
    truncated: bool = False
    # True nếu sinh bị CẮT vì hết ngân sách max_tokens (finish_reason="length"),
    # không phải model tự dừng giữa câu. Câu cụt do hết token KHÔNG phải bằng
    # chứng suy sụp mạch lạc — bug đã bắt được trên dữ liệu thật: 135/150 cờ E6
    # ở BF16 (mốc CHƯA nén) đều do cắt ngang vì max_tokens, không phải nén.
    hit_length_limit: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Thresholds:
    """Ngưỡng gắn cờ. CHỐT SAU PILOT — đừng dùng số mặc định trong báo cáo
    mà không hiệu chuẩn lại trên dữ liệu thật của mình (xem scripts/08)."""

    # E2: cờ khi tỉ lệ dấu tụt dưới ngưỡng tuyệt đối HOẶC tụt tương đối so
    # với đầu ra tham chiếu BF16 trên cùng prompt.
    diacritic_ratio_floor: float = 0.10
    diacritic_relative_drop: float = 0.25
    tone_loss_min_tokens: int = 2
    # E6 — hai chỉ số bổ sung nhau: ngram bắt vòng lặp NGẮN (chu kỳ < 5 từ),
    # line bắt vòng lặp DÀI (nguyên câu/đoạn, chu kỳ > 5 từ mà ngram bỏ sót).
    ngram_repeat_ceiling: float = 0.15
    min_words_for_repeat: int = 40
    line_repeat_ceiling: float = 0.30
    min_lines_for_repeat: int = 5


def compute_signals(
    text: str,
    lexicon: Optional[vitext.VietLexicon] = None,
    index: Optional[cit.CitationIndex] = None,
    finish_reason: Optional[str] = None,
) -> Signals:
    """finish_reason: từ backend sinh (vd. vLLM "stop"/"length"). None nếu
    không rõ (dữ liệu cũ chưa ghi trường này) — khi đó giữ hành vi cũ
    (truncated vẫn tính là bằng chứng E6), vì không có cách nào phân biệt
    ngược lại từ chính văn bản."""
    cits = cit.extract(text)
    verifiable = [c for c in cits if c.kind in ("doc", "dieu", "bienbao")]
    unknown = index.unknown(cits) if index is not None else []
    low = text.lower()
    confusion = [t for pair in ADMIN_CONFUSION_PAIRS for t in pair if t in low]
    return Signals(
        n_chars=len(text),
        n_words=len(vitext.words(text)),
        diacritic_ratio=vitext.diacritic_ratio(text),
        mojibake_hits=vitext.mojibake_hits(text),
        tone_loss_tokens=lexicon.tone_loss_tokens(text) if lexicon else [],
        unknown_citations=[c.raw for c in unknown],
        n_citations=len(verifiable),
        confusion_terms=confusion,
        foreign_script=vitext.foreign_script_hits(text),
        english_runs=vitext.english_run_hits(text),
        max_ngram_repeat=vitext.max_ngram_repeat(text),
        max_line_repeat=vitext.max_line_repeat(text),
        truncated=vitext.looks_truncated(text),
        hit_length_limit=(finish_reason == "length"),
    )


def flags(
    sig: Signals,
    thresholds: Thresholds | None = None,
    reference_diacritic_ratio: float | None = None,
) -> dict[str, bool]:
    """Bật/tắt từng mã lỗi từ tín hiệu.

    reference_diacritic_ratio: tỉ lệ dấu của đầu ra BF16 trên CÙNG prompt.
    Truyền vào thì E2 nhạy hơn nhiều, vì so tương đối mạnh hơn so tuyệt đối.
    """
    th = thresholds or Thresholds()

    e2 = len(sig.tone_loss_tokens) >= th.tone_loss_min_tokens
    if sig.n_words > 0 and sig.diacritic_ratio < th.diacritic_ratio_floor:
        e2 = True
    if reference_diacritic_ratio and reference_diacritic_ratio > 0:
        rel_drop = (reference_diacritic_ratio - sig.diacritic_ratio) / reference_diacritic_ratio
        if rel_drop >= th.diacritic_relative_drop:
            e2 = True

    # Câu cụt vì HẾT NGÂN SÁCH TOKEN không phải bằng chứng suy sụp mạch lạc —
    # đó là giới hạn của người thí nghiệm (max_tokens), không phải lỗi model.
    # LƯU Ý: hit_length_limit KHÔNG được dùng để dập tín hiệu lặp thật bên
    # dưới — một mẫu có thể vừa bị cắt vì hết token VỪA suy sụp mạch lạc thật
    # (ca thật: qwen2.5-1.5b-it@int8, số câu bị cắt KHÔNG đổi giữa max_tokens
    # 1024 và 2048 — bằng chứng model lặp vô hạn, không phải thiếu ngân sách).
    e6 = sig.truncated and not sig.hit_length_limit
    if sig.n_words >= th.min_words_for_repeat and sig.max_ngram_repeat >= th.ngram_repeat_ceiling:
        e6 = True
    # Lặp DÒNG (câu/đoạn dài) — bắt chu kỳ lặp dài hơn cửa sổ 5 từ mà
    # max_ngram_repeat bỏ sót (ca thật: A001, ratio ngram 5,1% nhưng 92,5%
    # số dòng lặp y hệt).
    if sig.max_line_repeat >= th.line_repeat_ceiling:
        e6 = True

    return {
        "E1": bool(sig.mojibake_hits),
        "E2": e2,
        "E3": bool(sig.unknown_citations),
        # E4 chỉ báo "có mặt thuật ngữ trong cặp dễ nhầm" — KHÔNG kết luận
        # được sai/đúng bằng máy. Cờ này chỉ để đưa mẫu cho người gán nhãn.
        "E4": False,
        "E5": bool(sig.foreign_script) or bool(sig.english_runs),
        "E6": e6,
    }


def needs_human_review(sig: Signals, fl: dict[str, bool]) -> bool:
    """Mẫu nào bắt buộc đưa cho người xem.

    Gồm: mọi mẫu bị gắn cờ, cộng mọi mẫu có thuật ngữ dễ nhầm (E4 không
    tự động được), cộng mẫu có trích dẫn nhưng không rõ đúng sai.
    """
    return any(fl.values()) or bool(sig.confusion_terms)
