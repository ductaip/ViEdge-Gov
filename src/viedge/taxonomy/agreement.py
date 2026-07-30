"""
Độ đồng thuận giữa hai người gán nhãn.

Vì sao AC1 (Gwet) chứ không phải Cohen's kappa làm chỉ số chính:
taxonomy lỗi có **prevalence rất lệch** — E1 (vỡ dấu) có thể chỉ xuất hiện
ở 2-3% mẫu. Cohen's kappa sụp về gần 0 trong tình huống lệch prevalence dù
hai người thực chất đồng ý gần như hoàn toàn (nghịch lý kappa). AC1 không
mắc nghịch lý đó. Báo cáo CẢ HAI, và giải thích đúng một câu như trên —
hội đồng phản biện sẽ hỏi tại sao chọn AC1, phải trả lời được.

Mọi chỉ số kèm khoảng tin cậy bootstrap. Con số trần trụi không có CI trong
báo cáo NCKH là chỗ dễ bị bắt lỗi nhất.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

Label = str


@dataclass
class AgreementResult:
    n_items: int
    n_categories: int
    percent_agreement: float
    ac1: float
    cohen_kappa: float
    ac1_ci: tuple[float, float] | None = None
    kappa_ci: tuple[float, float] | None = None

    def format(self) -> str:
        def ci(x):
            return f" [{x[0]:.3f}, {x[1]:.3f}]" if x else ""

        return (
            f"n={self.n_items}, K={self.n_categories}\n"
            f"  Đồng thuận thô : {self.percent_agreement:.3f}\n"
            f"  Gwet AC1       : {self.ac1:.3f}{ci(self.ac1_ci)}\n"
            f"  Cohen kappa    : {self.cohen_kappa:.3f}{ci(self.kappa_ci)}"
        )


def _percent_agreement(a: Sequence[Label], b: Sequence[Label]) -> float:
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


def _marginals(a: Sequence[Label], b: Sequence[Label], cats: list[Label]):
    n = len(a)
    p1 = {c: sum(1 for x in a if x == c) / n for c in cats}
    p2 = {c: sum(1 for y in b if y == c) / n for c in cats}
    return p1, p2


def gwet_ac1(a: Sequence[Label], b: Sequence[Label]) -> float:
    """Hệ số đồng thuận bậc nhất của Gwet."""
    cats = sorted(set(a) | set(b))
    K = len(cats)
    if K < 2:
        return 1.0
    pa = _percent_agreement(a, b)
    p1, p2 = _marginals(a, b, cats)
    pi = {c: (p1[c] + p2[c]) / 2 for c in cats}
    pe = sum(pi[c] * (1 - pi[c]) for c in cats) / (K - 1)
    if pe >= 1.0:
        return 1.0
    return (pa - pe) / (1 - pe)


def cohen_kappa(a: Sequence[Label], b: Sequence[Label]) -> float:
    cats = sorted(set(a) | set(b))
    if len(cats) < 2:
        return 1.0
    pa = _percent_agreement(a, b)
    p1, p2 = _marginals(a, b, cats)
    pe = sum(p1[c] * p2[c] for c in cats)
    if pe >= 1.0:
        return 1.0
    return (pa - pe) / (1 - pe)


def bootstrap_ci(
    a: Sequence[Label],
    b: Sequence[Label],
    fn,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 20260825,
) -> tuple[float, float]:
    """Khoảng tin cậy percentile bằng bootstrap lấy mẫu lại theo ITEM."""
    rng = random.Random(seed)
    n = len(a)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        try:
            vals.append(fn([a[i] for i in idx], [b[i] for i in idx]))
        except ZeroDivisionError:  # pragma: no cover
            continue
    if not vals:
        return (float("nan"), float("nan"))
    vals.sort()
    lo = vals[int((alpha / 2) * len(vals))]
    hi = vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))]
    return (lo, hi)


def evaluate(
    a: Sequence[Label],
    b: Sequence[Label],
    n_boot: int = 2000,
    seed: int = 20260825,
) -> AgreementResult:
    if len(a) != len(b):
        raise ValueError(f"Hai chuỗi nhãn khác độ dài: {len(a)} vs {len(b)}")
    if not a:
        raise ValueError("Không có mẫu nào để tính đồng thuận")
    cats = sorted(set(a) | set(b))
    res = AgreementResult(
        n_items=len(a),
        n_categories=len(cats),
        percent_agreement=_percent_agreement(a, b),
        ac1=gwet_ac1(a, b),
        cohen_kappa=cohen_kappa(a, b),
    )
    if n_boot > 0:
        res.ac1_ci = bootstrap_ci(a, b, gwet_ac1, n_boot=n_boot, seed=seed)
        res.kappa_ci = bootstrap_ci(a, b, cohen_kappa, n_boot=n_boot, seed=seed)
    return res


def per_label_binary(
    ann_a: dict[str, dict[str, bool]],
    ann_b: dict[str, dict[str, bool]],
    labels: Sequence[str],
    n_boot: int = 1000,
) -> dict[str, AgreementResult]:
    """Taxonomy là ĐA NHÃN — một đầu ra có thể vừa E2 vừa E6.

    Vì vậy chỉ số đồng thuận phải tính RIÊNG cho từng mã lỗi dưới dạng
    nhị phân, không gộp thành một biến hạng mục. Báo cáo bảng 6 dòng.
    """
    ids = sorted(set(ann_a) & set(ann_b))
    if not ids:
        raise ValueError("Không có id trùng nhau giữa hai người gán nhãn")
    out: dict[str, AgreementResult] = {}
    for lab in labels:
        a = ["1" if ann_a[i].get(lab) else "0" for i in ids]
        b = ["1" if ann_b[i].get(lab) else "0" for i in ids]
        out[lab] = evaluate(a, b, n_boot=n_boot)
    return out


def interpret(ac1: float) -> str:
    """Thang diễn giải Landis-Koch, dùng để viết nhận xét trong báo cáo."""
    if ac1 < 0.0:
        return "kém hơn ngẫu nhiên"
    if ac1 < 0.20:
        return "rất thấp"
    if ac1 < 0.40:
        return "thấp"
    if ac1 < 0.60:
        return "trung bình"
    if ac1 < 0.80:
        return "khá"
    return "cao"
