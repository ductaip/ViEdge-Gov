"""
Tách từ cho văn bản PDF bị DÍNH CHỮ.

VÌ SAO CẦN: nhiều PDF văn bản pháp quy Việt Nam (kể cả bản chính thức trên
datafiles.chinhphu.vn) nhúng font theo cách khiến trình trích xuất mất khoảng
trắng. Kết quả:

    "Quychuẩnnày quyđịnh vềbáohiệuđườngbộ"   thay vì
    "Quy chuẩn này quy định về báo hiệu đường bộ"

Nếu để nguyên, hỏng dây chuyền:
  - BM25 tokenize ra "quychuẩnnày" -> không truy vấn nào khớp
  - VietLexicon dựng từ rác -> detector E2 vô dụng
  - parser Điều/khoản vẫn chạy nhưng nội dung không tra cứu được

CÁCH LÀM: tiếng Việt đơn âm tiết — mỗi âm tiết là một đơn vị viết rời. Nên
bài toán là tách chuỗi thành dãy âm tiết hợp lệ. Dùng quy hoạch động, ưu tiên
ít âm tiết nhất (tức âm tiết dài nhất) và phạt nặng ký tự không ghép được.

THỨ TỰ ƯU TIÊN: luôn thử nhiều trình trích xuất trước (xem scripts/00).
Chỉ dùng module này khi mọi trình trích xuất đều trả về văn bản dính.
"""

from __future__ import annotations

import re
from functools import lru_cache

# Phụ âm đầu. Xếp dài trước ngắn để khớp tham lam đúng (ngh trước ng trước n).
ONSETS = [
    "ngh", "nghi",
    "ch", "gh", "gi", "kh", "ng", "nh", "ph", "qu", "th", "tr",
    "b", "c", "d", "đ", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v", "x",
    "",
]
ONSETS = sorted(set(ONSETS), key=len, reverse=True)

# Nguyên âm (đã gồm mọi dấu).
VOWELS = "aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵ"

# Âm cuối.
CODAS = ["ch", "ng", "nh", "c", "m", "n", "p", "t", ""]
CODAS = sorted(set(CODAS), key=len, reverse=True)

_SYL_RE = re.compile(
    rf"^(?:{'|'.join(o for o in ONSETS if o)})?"
    rf"[{VOWELS}]{{1,3}}"
    rf"(?:{'|'.join(c for c in CODAS if c)})?$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Kho âm tiết mồi
# ---------------------------------------------------------------------------
# Hợp lệ về CẤU TRÚC là chưa đủ: "quych" khớp mẫu (qu + y + ch) nhưng không
# phải âm tiết thật, và bộ tách sẽ ưu tiên nó vì nó dài. Vì vậy phải chấm điểm
# theo âm tiết CÓ THẬT chứ không chỉ theo cấu trúc.
#
# Danh sách dưới là mồi: từ chức năng + từ vựng pháp lý/giao thông. Sau khi có
# văn bản sạch đầu tiên (nguồn HTML không bị dính chữ), hãy MỞ RỘNG bằng
# SyllableModel.from_texts() — mô hình học từ corpus luôn tốt hơn danh sách tay.
SEED_SYLLABLES = set("""
và của có là được các cho trong với khi này đó những một hai ba bốn năm sáu bảy
tám chín mười người thì đã sẽ không phải để từ theo về tại ra vào trên dưới đến
sau trước nếu mà hoặc cũng đều chỉ còn nhưng do bởi vì nên thế như sự việc cách
khác nhau cùng mỗi mọi tất cả nhiều ít lớn nhỏ cao thấp dài ngắn rộng hẹp mới cũ
tốt xấu nơi chỗ trường hợp khi nào bao gồm gồm cần thiết phù hợp bảo đảm đảm bảo
quy chuẩn định luật nghị thông tư điều khoản điểm chương phần mục phụ lục ban
hành hiệu lực áp dụng thực hiện chấp tuân thủ vi phạm xử phạt tiền mức đối tượng
điều chỉnh trách nhiệm quyền nghĩa vụ cơ quan tổ chức cá nhân nhà nước chính phủ
bộ trưởng thẩm định biên soạn kỹ thuật quốc gia ký hiệu số hình vẽ chữ viết màu
sắc kích thước bảng biểu mẫu danh mục
giao vận tải công an sát hạch cấp đổi lại giấy phép lái xe đăng hồ sơ thủ tục
hành khai thác quản đầu xây dựng bảo vệ trì sử kết cấu hạ tầng
đường bộ phương tiện biển báo tín đèn vạch kẻ làn tốc độ tối đa thiểu an toàn
trật tự ô tô mô gắn máy đạp thô khách kéo moóc rơ sơ mi cấm lệnh dẫn nguy hiểm
cảnh chỉ nhánh nút cầu hầm cống dốc đèo quanh co ngoặt ưu tiên nhường vượt quay
đầu dừng đỗ đậu chiều ngược kilômét cọc tiêu mốc lộ giới dải phân cách lan can
phòng hộ gương lồi tường rào chắn đinh phản quang cột cần vươn giá long môn
thị trấn thành phố tỉnh huyện xã phường thôn ấp khu dân cư đông nội ngoại
cộng hoà hòa hội chủ việt nam hà nội cục
xanh vàng đỏ trắng đen nâu lam lá cây huỳnh trên mặt phần lề vỉa hè tim đoạn
tuyến mạng lưới hệ thống thứ tự vị trí khoảng góc bên trái tay chân đỉnh mép
đáy cạnh trung bình lưu lượng ngày đêm tầm nhìn thiết
""".split())

MAX_SYL_LEN = 7  # "nghiêng", "nguyễn" ...


@lru_cache(maxsize=1 << 16)
def is_syllable(s: str) -> bool:
    """Âm tiết tiếng Việt hợp lệ về mặt cấu trúc (không tra từ điển)."""
    if not s or len(s) > MAX_SYL_LEN:
        return False
    return bool(_SYL_RE.match(s))


class SyllableModel:
    """Kho âm tiết dùng để chấm điểm. Mở rộng được từ văn bản sạch."""

    def __init__(self, known: set[str] | None = None):
        self.known: set[str] = set(known or SEED_SYLLABLES)

    @classmethod
    def from_texts(cls, texts, seed: bool = True) -> "SyllableModel":
        """Học âm tiết từ văn bản SẠCH (nguồn HTML, không bị dính chữ).

        Dùng ngay khi có văn bản sạch đầu tiên — chất lượng tách tăng rõ rệt
        so với danh sách mồi viết tay.
        """
        known = set(SEED_SYLLABLES) if seed else set()
        for t in texts:
            for w in re.findall(r"[^\W\d_]+", t, flags=re.UNICODE):
                lw = w.lower()
                if is_syllable(lw):
                    known.add(lw)
        return cls(known)

    def cost(self, piece: str) -> float:
        p = piece.lower()
        if p in self.known:
            return 1.0          # âm tiết có thật — rẻ nhất
        if is_syllable(p):
            return 4.0          # hợp cấu trúc nhưng chưa gặp — chấp nhận, đắt hơn
        return 15.0 + len(p)    # không phải âm tiết — phạt nặng

    def segment(self, tok: str) -> tuple[str, ...]:
        n = len(tok)
        if n == 0:
            return ()
        INF = float("inf")
        cost = [INF] * (n + 1)
        back = [0] * (n + 1)
        cost[0] = 0.0
        for i in range(1, n + 1):
            for L in range(1, min(MAX_SYL_LEN, i) + 1):
                j = i - L
                if cost[j] == INF:
                    continue
                c = cost[j] + self.cost(tok[j:i])
                if c < cost[i]:
                    cost[i] = c
                    back[i] = L
        out: list[str] = []
        i = n
        while i > 0:
            L = back[i] or 1
            out.append(tok[i - L : i])
            i -= L
        return tuple(reversed(out))


_DEFAULT_MODEL = SyllableModel()


def glue_ratio(text: str) -> float:
    """Tỉ lệ token *không* là âm tiết đơn — ước lượng mức dính chữ.

    Văn bản sạch thường < 0.15. Trên 0.35 gần như chắc chắn bị dính chữ.
    Dùng chỉ số này để CHỌN trình trích xuất PDF tốt nhất (xem scripts/00).
    """
    toks = re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)
    if not toks:
        return 0.0
    bad = sum(1 for t in toks if not is_syllable(t.lower()))
    return bad / len(toks)


def desegment(text: str, min_glue_ratio: float = 0.25,
              model: "SyllableModel | None" = None) -> str:
    """Tách lại toàn văn bản. Giữ nguyên nếu không có dấu hiệu dính chữ."""
    if glue_ratio(text) < min_glue_ratio:
        return text
    m = model or _DEFAULT_MODEL

    def fix(mt: re.Match) -> str:
        tok = mt.group(0)
        if tok.lower() in m.known or (is_syllable(tok.lower()) and len(tok) <= 4):
            return tok
        return " ".join(m.segment(tok))

    return re.sub(r"[^\W\d_]+", fix, text, flags=re.UNICODE)


def report(before: str, after: str) -> dict:
    return {
        "glue_ratio_before": round(glue_ratio(before), 4),
        "glue_ratio_after": round(glue_ratio(after), 4),
        "n_words_before": len(re.findall(r"[^\W\d_]+", before, flags=re.UNICODE)),
        "n_words_after": len(re.findall(r"[^\W\d_]+", after, flags=re.UNICODE)),
    }