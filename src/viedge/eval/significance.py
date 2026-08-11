"""
Kiểm định ý nghĩa thống kê cho hiệu số accuracy giữa các bậc nén.

VÌ SAO PHẢI CÓ MODULE NÀY (và vì sao nó CỨU đề tài khi cỡ mẫu nhỏ):

VMLU công bố 10.880 câu, nhưng **đáp án của split test KHÔNG công khai** — chỉ
dev/validation có đáp án. Nghĩa là cỡ mẫu chấm được nhỏ hơn kế hoạch ban đầu
rất nhiều (~1.000 thay vì 2.000).

Nếu dùng sai số lấy mẫu độc lập (MoE), n=744 cho ±3,6% ở mức tin cậy 95% — nghĩa
là suy giảm dưới 3,6 điểm sẽ "không phân biệt được với nhiễu", và đề tài mất khả
năng kết luận ở đúng vùng thú vị nhất (bậc INT8, nơi suy giảm thường nhỏ).

NHƯNG MoE độc lập là chỉ số SAI cho thiết kế này. Ta chấm **CÙNG một bộ câu hỏi**
qua các bậc nén — đây là thiết kế BẮT CẶP (paired). Với dữ liệu bắt cặp, phần
lớn phương sai giữa các câu hỏi bị triệt tiêu; chỉ những câu ĐỔI kết quả mới
mang thông tin. Kiểm định McNemar khai thác đúng điều đó và mạnh hơn nhiều.

Ví dụ cụ thể: n=744, BF16 đúng 60,0%, INT4 đúng 57,5% (chênh 2,5 điểm).
  - MoE độc lập  -> ±3,6%, "không kết luận được"
  - McNemar bắt cặp -> nếu 30 câu đúng->sai và 11 câu sai->đúng, p ≈ 0,004,
    kết luận CÓ ý nghĩa thống kê.

Cùng một dữ liệu, hai kết luận trái ngược. Chọn sai chỉ số là tự vứt bỏ phát hiện.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence


@dataclass
class McNemarResult:
    n: int
    acc_a: float
    acc_b: float
    delta: float
    b: int          # A đúng, B sai
    c: int          # A sai, B đúng
    statistic: float
    p_value: float
    method: str

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05

    def format(self) -> str:
        return (
            f"n={self.n} | acc {self.acc_a:.1%} -> {self.acc_b:.1%} "
            f"(Δ {self.delta:+.1%})\n"
            f"  đúng→sai: {self.b}   sai→đúng: {self.c}   "
            f"({self.method}) p={self.p_value:.4g} "
            f"{'CÓ ý nghĩa' if self.significant else 'KHÔNG có ý nghĩa'} ở α=0,05"
        )


def _binom_two_sided(b: int, c: int) -> float:
    """Kiểm định nhị thức chính xác — dùng khi b+c nhỏ (chi-square không đáng tin)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def _chi2_sf_1df(x: float) -> float:
    """P(X > x) với X ~ chi-square 1 bậc tự do = erfc(sqrt(x/2))."""
    return math.erfc(math.sqrt(x / 2.0))


def mcnemar(correct_a: Sequence[bool], correct_b: Sequence[bool]) -> McNemarResult:
    """So hai hệ thống trên CÙNG bộ câu hỏi.

    correct_a/b: đúng/sai từng câu. Thứ tự phải khớp nhau — đây là điều kiện
    của thiết kế bắt cặp; lệch thứ tự thì kết quả vô nghĩa mà vẫn ra số.
    """
    if len(correct_a) != len(correct_b):
        raise ValueError(f"hai chuỗi khác độ dài: {len(correct_a)} vs {len(correct_b)}")
    if not correct_a:
        raise ValueError("không có mẫu nào")

    b = sum(1 for x, y in zip(correct_a, correct_b) if x and not y)
    c = sum(1 for x, y in zip(correct_a, correct_b) if y and not x)
    n = len(correct_a)
    acc_a = sum(correct_a) / n
    acc_b = sum(correct_b) / n

    if b + c < 25:
        # Mẫu bất đồng ít -> dùng nhị thức chính xác, không dùng xấp xỉ chi-square
        p = _binom_two_sided(b, c)
        stat = float(min(b, c))
        method = "nhị thức chính xác"
    else:
        # Hiệu chỉnh liên tục Yates
        stat = (abs(b - c) - 1) ** 2 / (b + c)
        p = _chi2_sf_1df(stat)
        method = "chi-square (Yates)"

    return McNemarResult(n=n, acc_a=acc_a, acc_b=acc_b, delta=acc_b - acc_a,
                         b=b, c=c, statistic=stat, p_value=p, method=method)


def paired_bootstrap_ci(
    correct_a: Sequence[bool],
    correct_b: Sequence[bool],
    n_boot: int = 5000,
    alpha: float = 0.05,
    seed: int = 20260825,
) -> tuple[float, float]:
    """Khoảng tin cậy cho hiệu accuracy, lấy mẫu lại theo CÂU HỎI (giữ cặp).

    Báo cáo CI này cạnh mỗi Δ trong Bảng 3. Con số trần trụi không có CI là chỗ
    dễ bị bắt lỗi nhất trong báo cáo NCKH.
    """
    rng = random.Random(seed)
    n = len(correct_a)
    diffs = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        a = sum(correct_a[i] for i in idx) / n
        b = sum(correct_b[i] for i in idx) / n
        diffs.append(b - a)
    diffs.sort()
    lo = diffs[int((alpha / 2) * n_boot)]
    hi = diffs[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (lo, hi)


def min_detectable_delta(n: int, p: float = 0.5, alpha: float = 0.05) -> float:
    """Sai số lấy mẫu ĐỘC LẬP — để đối chiếu cho thấy vì sao bắt cặp mạnh hơn.

    Đưa cả hai con số vào phụ lục: nó chứng minh nhóm hiểu vì sao chọn McNemar.
    """
    z = 1.959963985
    return z * math.sqrt(p * (1 - p) / n) if n > 0 else float("nan")


@dataclass
class FloorCheck:
    acc: float
    baseline: float
    n: int
    z: float
    p_value: float
    at_floor: bool
    note: str


def at_floor(acc: float, n: int, baseline: float, alpha: float = 0.05) -> FloorCheck:
    """Accuracy này có còn PHÂN BIỆT ĐƯỢC với đoán mò không?

    VÌ SAO CẦN, VÀ CẦN Ở BẬC NÉN CHỨ KHÔNG CHỈ Ở KHÂU SÀNG MODEL:

    Sàng model (ADR-012) chỉ kiểm TRẦN ở BF16. Nhưng một model qua được sàng vẫn
    có thể TỤT XUỐNG SÀN sau khi nén. Ví dụ thật của đề tài này: Gemma-3-1B có
    trần 39,5%, đoán mò 25,2% -> headroom chỉ +14,3 điểm. Nếu INT4 làm tụt 10
    điểm, nó còn 29,5% — đã sát sàn.

    Khi một biến thể chạm sàn, mọi so sánh SAU đó vô nghĩa: "INT4 tệ hơn INT8
    5 điểm" không nói lên gì nếu cả hai đều không khác đoán mò. Phải đánh dấu
    và DỪNG diễn giải, thay vì vẽ tiếp đường cong xuống dưới.

    Dùng kiểm định z một phía cho tỉ lệ: acc có LỚN HƠN baseline không?
    """
    if n <= 0:
        return FloorCheck(acc, baseline, n, float("nan"), float("nan"), True,
                          "không có mẫu")
    se = math.sqrt(baseline * (1 - baseline) / n)
    z = (acc - baseline) / se if se > 0 else 0.0
    p = 0.5 * math.erfc(z / math.sqrt(2))          # một phía: P(Z > z)
    floor = p >= alpha
    if floor:
        note = ("ĐÃ CHẠM SÀN — không phân biệt được với đoán mò. "
                "Ghi nhận là 'mất năng lực', KHÔNG diễn giải mức tụt tiếp theo.")
    elif acc - baseline < 0.05:
        note = "sát sàn — còn phân biệt được nhưng biên rất hẹp, diễn giải thận trọng"
    else:
        note = "còn cách sàn, so sánh có ý nghĩa"
    return FloorCheck(acc=acc, baseline=baseline, n=n, z=z, p_value=p,
                      at_floor=floor, note=note)


def floor_accuracy(n: int, baseline: float, alpha: float = 0.05) -> float:
    """Accuracy THẤP NHẤT còn phân biệt được với đoán mò, ở cỡ mẫu n.

    Dùng để tính TRƯỚC biên an toàn của một model: nếu trần BF16 cách ngưỡng này
    càng xa thì càng nhiều chỗ cho suy giảm biểu hiện trước khi chạm sàn.

    Lưu ý quan trọng khi đọc kết quả sàng model: ngưỡng này phụ thuộc MẠNH vào n.
    Sàng chạy trên 200 câu cho ngưỡng cao hơn hẳn so với eval chính thức trên
    1.047 câu — nên một model trông "sát sàn" lúc sàng có thể vẫn còn nhiều biên
    khi chạy đủ mẫu. Đừng loại model dựa trên ngưỡng của cỡ mẫu nhỏ.
    """
    if n <= 0:
        return 1.0
    z = 1.6448536269514722          # một phía, alpha = 0.05
    se = math.sqrt(baseline * (1 - baseline) / n)
    return baseline + z * se


def headroom_report(acc_bf16: float, n: int, baseline: float) -> dict:
    """Biên an toàn của một model: còn tụt được bao nhiêu điểm trước khi chạm sàn."""
    floor = floor_accuracy(n, baseline)
    return {
        "acc_bf16": round(acc_bf16, 4),
        "random_baseline": round(baseline, 4),
        "n": n,
        "floor_accuracy": round(floor, 4),
        "drop_budget_pts": round((acc_bf16 - floor) * 100, 1),
    }
