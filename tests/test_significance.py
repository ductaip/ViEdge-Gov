"""Kiểm định bắt cặp — chỉ số chính của Bảng 3 (ADR-013)."""
import random
import pytest
from viedge.eval.significance import (mcnemar, paired_bootstrap_ci,
                                      min_detectable_delta)


def _pair(n=744, base=0.60, p_down=0.065, p_up=0.035, seed=7):
    """Sinh cặp kết quả bắt cặp. Dùng RNG RIÊNG cho phần lật để thay đổi
    p_down/p_up không kéo theo thay đổi chuỗi gốc `a`."""
    rng = random.Random(seed)
    a = [rng.random() < base for _ in range(n)]
    flip = random.Random(seed + 4)
    b = []
    for x in a:
        if x and flip.random() < p_down:
            b.append(False)
        elif not x and flip.random() < p_up:
            b.append(True)
        else:
            b.append(x)
    return a, b


def test_detects_real_degradation():
    a, b = _pair()
    r = mcnemar(a, b)
    assert r.delta < 0 and r.significant
    assert r.b > r.c


def test_no_difference_not_significant():
    a = [i % 3 != 0 for i in range(500)]
    r = mcnemar(a, list(a))
    assert r.b == 0 and r.c == 0
    assert r.p_value == 1.0 and not r.significant


@pytest.mark.parametrize("p_down,p_up", [(0.065, 0.035), (0.040, 0.025)])
def test_paired_beats_independent_moe(p_down, p_up):
    """Điểm cốt lõi của ADR-013: ở cùng cỡ mẫu, kiểm định bắt cặp phát hiện được
    khác biệt mà sai số lấy mẫu ĐỘC LẬP tuyên bố là 'không kết luận được'.

    Đây là lý do đề tài vẫn đứng vững dù VMLU chỉ cho ~1.000 câu chấm được:
    chọn đúng chỉ số thống kê quan trọng hơn tăng cỡ mẫu."""
    a, b = _pair(n=744, p_down=p_down, p_up=p_up)
    r = mcnemar(a, b)
    moe = min_detectable_delta(744)
    assert abs(r.delta) < moe, (
        f"Δ={r.delta:.2%} phải nằm TRONG vùng MoE ±{moe:.2%} thì ca thử mới có ý nghĩa")
    assert r.significant, (
        f"bắt cặp phải phát hiện được: p={r.p_value:.4g}")


def test_exact_binomial_for_small_discordance():
    a = [True] * 100
    b = list(a); b[0] = False; b[1] = False
    r = mcnemar(a, b)
    assert r.method == "nhị thức chính xác"
    assert 0.0 < r.p_value <= 1.0


def test_ci_brackets_delta():
    a, b = _pair()
    r = mcnemar(a, b)
    lo, hi = paired_bootstrap_ci(a, b, n_boot=1500)
    assert lo <= r.delta <= hi
    assert lo < 0 < hi or hi < 0


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        mcnemar([True], [True, False])
    with pytest.raises(ValueError):
        mcnemar([], [])


def test_moe_shrinks_with_n():
    assert min_detectable_delta(500) > min_detectable_delta(2000)


# --- Cửa kiểm SÀN cho từng bậc nén (ADR-018) ---

from viedge.eval.significance import at_floor  # noqa: E402


def test_clear_ability_not_at_floor():
    f = at_floor(0.520, 1047, 0.2524)
    assert not f.at_floor and f.p_value < 0.001


def test_accuracy_near_random_flagged_as_floor():
    f = at_floor(0.270, 200, 0.2524)
    assert f.at_floor
    assert "CHẠM SÀN" in f.note


def test_same_accuracy_more_samples_escapes_floor():
    """Cỡ mẫu lớn hơn đẩy được ngưỡng phát hiện xuống thấp hơn — lý do chạy
    eval trên toàn bộ 1.047 câu chứ không chỉ 200 câu lúc sàng."""
    assert at_floor(0.295, 200, 0.2524).at_floor
    assert not at_floor(0.295, 1047, 0.2524).at_floor


def test_narrow_margin_gets_caution_note():
    f = at_floor(0.290, 1047, 0.2524)
    assert not f.at_floor
    assert "sát sàn" in f.note


def test_zero_samples_is_floor():
    assert at_floor(0.5, 0, 0.25).at_floor


def test_floor_threshold_depends_strongly_on_sample_size():
    """Ngưỡng sàn tính trên cỡ mẫu THĂM DÒ không được áp cho cỡ mẫu CHÍNH THỨC —
    suýt loại oan Gemma-3-1B vì lỗi này (ADR-019)."""
    from viedge.eval.significance import floor_accuracy
    f200 = floor_accuracy(200, 0.2524)
    f1047 = floor_accuracy(1047, 0.2524)
    assert f200 > f1047
    assert f1047 == pytest.approx(0.274, abs=0.003)


def test_headroom_report_drop_budget():
    from viedge.eval.significance import headroom_report
    r = headroom_report(0.395, 1047, 0.2524)
    assert r["drop_budget_pts"] == pytest.approx(12.1, abs=0.3)
    assert headroom_report(0.520, 1047, 0.2524)["drop_budget_pts"] > r["drop_budget_pts"]


# --- Hiệu chỉnh so sánh bội (ADR-022) ---

from viedge.eval.significance import holm_bonferroni, benjamini_hochberg  # noqa: E402

# p-value THẬT từ lần chạy 11/08 trên Modal L4
REAL_P = {
    "gemma3-1b@fp8": 1.0,
    "gemma3-1b@int4_awq": 1e-06,
    "gemma3-1b@int8": 0.06204,
    "qwen2.5-1.5b@fp8": 0.01712,
    "qwen2.5-1.5b@int4_awq": 0.01757,
    "qwen2.5-1.5b@int8": 0.5982,
}


def test_holm_keeps_only_strongest_on_real_data():
    """Trên dữ liệu THẬT: 3 kết quả có ý nghĩa thô, chỉ 1 sống sót Holm.
    Đây là lý do phải hiệu chỉnh trước khi viết kết luận vào quyển."""
    corr = holm_bonferroni(REAL_P)
    assert sum(c.significant_raw for c in corr) == 3
    assert sum(c.significant_adj for c in corr) == 1
    survivor = [c for c in corr if c.significant_adj][0]
    assert survivor.label == "gemma3-1b@int4_awq"


def test_holm_adjusted_p_is_monotonic():
    corr = holm_bonferroni(REAL_P)
    adj = [c.p_adj for c in corr]
    assert adj == sorted(adj), "p hiệu chỉnh phải không giảm theo thứ tự p thô"


def test_holm_never_lowers_p():
    for c in holm_bonferroni(REAL_P):
        assert c.p_adj >= c.p_raw


def test_bh_is_less_conservative_than_holm():
    """BH kiểm soát FDR nên lỏng hơn — dùng cho khám phá (tách theo 58 môn),
    KHÔNG dùng cho Bảng 3 nơi mỗi kết luận thành khuyến nghị triển khai."""
    n_holm = sum(c.significant_adj for c in holm_bonferroni(REAL_P))
    n_bh = sum(c.significant_adj for c in benjamini_hochberg(REAL_P))
    assert n_bh >= n_holm
    assert n_bh == 3


def test_single_test_unchanged():
    corr = holm_bonferroni({"only": 0.02})
    assert corr[0].p_adj == pytest.approx(0.02)
    assert corr[0].significant_adj


def test_p_adj_capped_at_one():
    assert all(c.p_adj <= 1.0 for c in holm_bonferroni({f"t{i}": 0.9 for i in range(10)}))
