"""Đo suy giảm không cần đáp án — dùng 9.833 câu test của VMLU (ADR-016)."""
import random
import pytest
from viedge.eval.reference_agreement import (flip_rate, flip_by_group,
                                             validate_proxy,
                                             expected_harmful_share, moe)

L = "ABCD"


def _make(n, p_flip, bias, seed, acc=0.65):
    """bias > 1 = nén nhắm vào câu đang ĐÚNG (tệ hơn nhiễu ngẫu nhiên)."""
    r = random.Random(seed)
    gold = [L[r.randrange(4)] for _ in range(n)]
    ref = [g if r.random() < acc else r.choice([c for c in L if c != g]) for g in gold]
    cmp = []
    for g, a in zip(gold, ref):
        p = min(1.0, p_flip * (bias if a == g else 1.0))
        cmp.append(r.choice([c for c in L if c != a]) if r.random() < p else a)
    return gold, ref, cmp


def test_flip_rate_counts_changes():
    r = flip_rate(["A", "B", "C", "D"], ["A", "B", "D", "D"], n_boot=200)
    assert r.n == 4 and r.n_flip == 1 and r.flip_rate == 0.25
    assert "C->D" in r.by_direction


def test_flip_rate_zero_when_identical():
    preds = ["A", "B", "C"] * 50
    r = flip_rate(preds, list(preds), n_boot=200)
    assert r.n_flip == 0 and r.flip_rate == 0.0


def test_flip_rate_ci_brackets_estimate():
    _, a, b = _make(2000, 0.10, 1.0, 5)
    r = flip_rate(a, b, n_boot=1000)
    assert r.ci95[0] <= r.flip_rate <= r.ci95[1]


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        flip_rate(["A"], ["A", "B"])
    with pytest.raises(ValueError):
        flip_rate([], [])


@pytest.mark.parametrize("acc,k,expected", [
    (0.50, 4, 0.75),
    (0.65, 4, 0.848),
    (0.80, 4, 0.923),
    (0.30, 4, 0.562),
])
def test_expected_harmful_share_is_high_even_under_pure_noise(acc, k, expected):
    """MẤU CHỐT: đổi câu ĐÚNG thì chắc chắn thành sai; đổi câu SAI chỉ thành đúng
    với xác suất 1/(k−1). Nên 'harmful share' tự nhiên đã rất cao ngay cả khi
    việc đổi hoàn toàn vô hướng. Ngưỡng cố định kiểu '>0.65 là xấu' vì thế LUÔN
    đúng — một phép kiểm không bao giờ trượt thì không kiểm gì cả."""
    assert expected_harmful_share(acc, k) == pytest.approx(expected, abs=0.002)
    assert expected_harmful_share(acc, k) > 0.55


def test_proxy_not_flagged_when_flips_are_pure_noise():
    gold, ref, cmp = _make(1047, 0.09, bias=1.0, seed=3)
    v = validate_proxy(ref, cmp, gold, n_choices=4.0)
    assert v.p_value >= 0.05
    assert "KHÔNG suy ra được" in v.verdict


def test_proxy_flagged_when_compression_targets_correct_answers():
    gold, ref, cmp = _make(1047, 0.09, bias=2.5, seed=3)
    v = validate_proxy(ref, cmp, gold, n_choices=4.0)
    assert v.p_value < 0.05
    assert v.excess > 0
    assert "dùng được làm proxy" in v.verdict


def test_proxy_reports_insufficient_flips():
    gold, ref, cmp = _make(300, 0.01, 1.0, 7)
    v = validate_proxy(ref, cmp, gold, n_choices=4.0)
    assert "chưa đủ lần đổi" in v.verdict


def test_larger_sample_gives_more_power():
    """Lý do dùng 9.833 câu không đáp án: cùng mức thiên lệch, cỡ mẫu lớn hơn
    cho p-value nhỏ hơn hẳn."""
    p = []
    for n in (1047, 9833):
        gold, ref, cmp = _make(n, 0.09, 2.5, 3)
        p.append(validate_proxy(ref, cmp, gold, 4.0).p_value)
    assert p[1] < p[0]


def test_flip_by_group_filters_small_groups():
    """Nhóm dưới min_n bị loại: với 10-20 câu/môn (cỡ của tập 1.047 câu) thì
    flip rate từng môn chỉ là nhiễu. Đây chính là lý do phải dùng tập 9.833 câu
    khi muốn tách theo môn."""
    n = 1200
    _, a, b = _make(n, 0.10, 1.0, 5)
    groups = [str(i % 12) if i < 1188 else "hiem" for i in range(n)]   # 'hiem' chỉ 12 câu
    out = flip_by_group(a, b, groups, min_n=30)
    assert all(r["n"] >= 30 for r in out)
    assert "hiem" not in {r["group"] for r in out}
    assert out == sorted(out, key=lambda r: -r["flip_rate"])


def test_moe_shrinks_with_n():
    assert moe(1047) > moe(9833)
    assert moe(1047) / moe(9833) == pytest.approx((9833 / 1047) ** 0.5, rel=0.01)
