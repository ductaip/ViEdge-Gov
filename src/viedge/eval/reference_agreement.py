"""
Đo suy giảm KHÔNG CẦN ĐÁP ÁN, bằng cách so với chính mô hình gốc.

Ý TƯỞNG. VMLU có 9.833 câu không đáp án. Nhìn theo cách cũ thì đó là dữ liệu bỏ
đi. Nhưng đề tài này KHÔNG hỏi "model trả lời đúng không" — đề tài hỏi "nén làm
model thay đổi thế nào". Câu hỏi đó trả lời được mà không cần biết đáp án đúng:

    Cho cùng một câu hỏi, BF16 chọn A. Sau khi nén xuống INT4, model chọn C.
    Đó là một lần ĐỔI DỰ ĐOÁN. Đếm tỉ lệ đổi trên 9.833 câu -> flip rate.

Flip rate là thước đo **độ trung thành với mô hình gốc** (fidelity). Nó không thay
thế accuracy, nhưng bổ sung ba thứ mà accuracy trên 1.047 câu không có:

  1. CỠ MẪU LỚN HƠN 9 LẦN -> khoảng tin cậy hẹp hơn nhiều, phát hiện được suy
     giảm nhỏ ở bậc INT8 nơi accuracy 1.047 câu không đủ nhạy.
  2. PHỦ RỘNG HƠN -> 9.833 câu phủ đủ 58 môn với ~170 câu/môn, đủ để nói suy
     giảm tập trung ở môn nào. Với 1.047 câu thì mỗi môn chỉ 10-20 câu, không
     tách theo môn được.
  3. KHÔNG DÍNH TRẦN NĂNG LỰC. Accuracy bị chặn bởi việc model có biết đáp án
     hay không; flip rate đo trực tiếp tác động của việc nén.

CẢNH BÁO PHẢI GHI TRONG BÁO CÁO. Flip rate KHÔNG phải accuracy:
  - đổi dự đoán có thể là đổi từ SAI sang ĐÚNG (nén đôi khi may mắn)
  - flip rate cao mà accuracy không giảm nghĩa là model "lung lay" nhưng chưa tệ đi
=> Vì vậy phải KIỂM CHỨNG proxy: trên 1.047 câu CÓ đáp án, tính cả hai chỉ số và
   xem chúng có đi cùng nhau không (hàm validate_proxy). Có tương quan thì flip
   rate trên 9.833 câu mới đáng tin để suy rộng. Không có thì chỉ báo cáo riêng.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass
from typing import Sequence


@dataclass
class FlipResult:
    n: int
    n_flip: int
    flip_rate: float
    ci95: tuple[float, float]
    by_direction: dict[str, int]

    def format(self) -> str:
        lo, hi = self.ci95
        return (f"n={self.n} | đổi dự đoán {self.n_flip} ({self.flip_rate:.2%}) "
                f"CI95 [{lo:.2%}, {hi:.2%}]")


def flip_rate(
    ref_preds: Sequence[str],
    cmp_preds: Sequence[str],
    n_boot: int = 2000,
    seed: int = 20260825,
) -> FlipResult:
    """Tỉ lệ câu mà mô hình nén chọn khác mô hình gốc.

    ref_preds / cmp_preds: nhãn đã chọn ("A".."E") cho TỪNG CÂU, cùng thứ tự.
    Không cần đáp án đúng.
    """
    if len(ref_preds) != len(cmp_preds):
        raise ValueError(f"lệch độ dài: {len(ref_preds)} vs {len(cmp_preds)}")
    if not ref_preds:
        raise ValueError("không có mẫu nào")

    flips = [a != b for a, b in zip(ref_preds, cmp_preds)]
    n, k = len(flips), sum(flips)

    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        boots.append(sum(flips[i] for i in idx) / n)
    boots.sort()
    lo = boots[int(0.025 * n_boot)]
    hi = boots[min(n_boot - 1, int(0.975 * n_boot))]

    direction = Counter(f"{a}->{b}" for a, b in zip(ref_preds, cmp_preds) if a != b)
    return FlipResult(n=n, n_flip=k, flip_rate=k / n, ci95=(lo, hi),
                      by_direction=dict(direction.most_common(10)))


def flip_by_group(
    ref_preds: Sequence[str],
    cmp_preds: Sequence[str],
    groups: Sequence[str],
    min_n: int = 30,
) -> list[dict]:
    """Flip rate tách theo nhóm (môn học).

    Đây là thứ 1.047 câu KHÔNG làm được: mỗi môn chỉ 10-20 câu, tách ra thì mỗi ô
    quá nhỏ để nói gì. Với 9.833 câu (~170 câu/môn) thì tách được, và câu hỏi
    "nén làm hỏng môn nào nhiều nhất" trở thành trả lời được — một kết quả phụ
    có giá trị cho RQ2.
    """
    buckets: dict[str, list[bool]] = {}
    for a, b, g in zip(ref_preds, cmp_preds, groups):
        buckets.setdefault(str(g), []).append(a != b)
    out = []
    for g, fl in sorted(buckets.items()):
        if len(fl) < min_n:
            continue
        out.append({"group": g, "n": len(fl), "n_flip": sum(fl),
                    "flip_rate": round(sum(fl) / len(fl), 4)})
    return sorted(out, key=lambda r: -r["flip_rate"])


@dataclass
class ProxyValidation:
    n: int
    flip_rate: float
    acc_ref: float
    acc_cmp: float
    acc_drop: float
    flip_down: int              # đúng -> sai
    flip_up: int                # sai -> đúng
    harmful_share: float        # quan sát được
    harmful_expected: float     # kỳ vọng NẾU đổi là ngẫu nhiên
    excess: float               # quan sát − kỳ vọng
    p_value: float
    verdict: str

    def format(self) -> str:
        return (f"n={self.n} | flip {self.flip_rate:.2%} | "
                f"acc {self.acc_ref:.1%}→{self.acc_cmp:.1%} (Δ{-self.acc_drop:+.1%})\n"
                f"  đúng→sai {self.flip_down}, sai→đúng {self.flip_up} | "
                f"harmful {self.harmful_share:.1%} vs kỳ vọng ngẫu nhiên "
                f"{self.harmful_expected:.1%} (chênh {self.excess:+.1%}, p={self.p_value:.3g})\n"
                f"  {self.verdict}")


def _binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) với X ~ Binomial(n, p). Một phía, dùng cho 'nhiều hơn kỳ vọng'."""
    if n == 0:
        return 1.0
    k = max(0, min(k, n))
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def expected_harmful_share(acc_ref: float, n_choices: float) -> float:
    """Tỉ lệ 'đúng→sai' KỲ VỌNG nếu việc đổi dự đoán là hoàn toàn ngẫu nhiên.

    ĐÂY LÀ MẤU CHỐT, và là chỗ bản đầu tiên của module này SAI.

    Đổi một câu ĐANG ĐÚNG thì chắc chắn thành sai (xác suất 1). Đổi một câu ĐANG
    SAI thì chỉ thành đúng với xác suất 1/(k−1). Nên ngay cả khi việc đổi hoàn
    toàn vô hướng, tỉ lệ 'đúng→sai' đã tự nhiên rất cao:

        acc=0,65, k=4  ->  kỳ vọng ≈ 0,85

    Ngưỡng cũ "harmful > 0,65 là proxy tốt" vì thế LUÔN ĐÚNG với mọi dữ liệu —
    một phép kiểm không bao giờ trượt thì không kiểm gì cả. Phải so với kỳ vọng
    ngẫu nhiên này, không so với 0,5.
    """
    if n_choices <= 1:
        return 1.0
    stay_wrong_to_right = (1 - acc_ref) / (n_choices - 1)
    denom = acc_ref + stay_wrong_to_right
    return acc_ref / denom if denom > 0 else 1.0


def validate_proxy(
    ref_preds: Sequence[str],
    cmp_preds: Sequence[str],
    gold: Sequence[str],
    n_choices: float = 4.0,
) -> ProxyValidation:
    """Kiểm chứng flip rate trên phần CÓ đáp án trước khi dùng để suy rộng.

    Câu hỏi cần trả lời: việc nén có phá hỏng câu đúng NHIỀU HƠN mức mà một
    nhiễu ngẫu nhiên cùng cường độ sẽ gây ra không?

    n_choices: số lựa chọn trung bình. VMLU có câu 3/4/5 -> truyền
    1/vmlu.random_baseline(rows) thay vì để mặc định 4.
    """
    if not (len(ref_preds) == len(cmp_preds) == len(gold)):
        raise ValueError("ba chuỗi phải cùng độ dài")
    n = len(gold)
    if n == 0:
        raise ValueError("không có mẫu nào")

    ok_ref = [p == g for p, g in zip(ref_preds, gold)]
    ok_cmp = [p == g for p, g in zip(cmp_preds, gold)]
    down = sum(1 for a, b in zip(ok_ref, ok_cmp) if a and not b)
    up = sum(1 for a, b in zip(ok_ref, ok_cmp) if b and not a)
    n_flip = sum(1 for a, b in zip(ref_preds, cmp_preds) if a != b)

    acc_ref = sum(ok_ref) / n
    observed = down / (down + up) if (down + up) else 0.0
    expected = expected_harmful_share(acc_ref, n_choices)
    p_val = _binom_sf(down, down + up, expected) if (down + up) else 1.0

    if down + up < 20:
        verdict = "chưa đủ lần đổi để kết luận — cần thêm mẫu hoặc bậc nén sâu hơn"
    elif p_val < 0.05:
        verdict = ("✅ nén phá hỏng câu đúng NHIỀU HƠN nhiễu ngẫu nhiên — "
                   "flip rate dùng được làm proxy suy giảm")
    else:
        verdict = ("⚠️ mức phá hỏng KHÔNG vượt kỳ vọng ngẫu nhiên — flip rate chỉ đo "
                   "ĐỘ LUNG LAY của mô hình, KHÔNG suy ra được suy giảm chất lượng")

    return ProxyValidation(
        n=n, flip_rate=n_flip / n,
        acc_ref=acc_ref, acc_cmp=sum(ok_cmp) / n,
        acc_drop=acc_ref - sum(ok_cmp) / n,
        flip_down=down, flip_up=up,
        harmful_share=observed, harmful_expected=expected,
        excess=observed - expected, p_value=p_val, verdict=verdict,
    )


def moe(n: int, p: float = 0.5) -> float:
    """Sai số 95% cho một tỉ lệ — dùng để so cỡ mẫu 1.047 với 9.833."""
    return 1.959963985 * math.sqrt(p * (1 - p) / n) if n > 0 else float("nan")
