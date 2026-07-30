import pytest
from viedge.taxonomy import agreement as A

def test_perfect_agreement():
    r = A.evaluate(["1","0","1","0"]*5, ["1","0","1","0"]*5, n_boot=100)
    assert r.percent_agreement == 1.0
    assert r.ac1 == pytest.approx(1.0)
    assert r.cohen_kappa == pytest.approx(1.0)

def test_kappa_paradox_ac1_more_stable():
    """Prevalence lệch mạnh: kappa sụp giả tạo, AC1 không.
    Đây là lý do đề tài chọn AC1 làm chỉ số chính — phải bảo vệ được."""
    a = ["1"]*95 + ["0"]*5
    b = ["1"]*92 + ["0"]*8   # 3 mẫu bất đồng, prevalence lệch 95/5
    r = A.evaluate(a, b, n_boot=200)
    assert r.percent_agreement >= 0.95
    assert r.ac1 > r.cohen_kappa

def test_ci_brackets_point_estimate():
    r = A.evaluate(["1"]*80+["0"]*20, ["1"]*75+["0"]*25, n_boot=500)
    lo, hi = r.ac1_ci
    assert lo <= r.ac1 <= hi

def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        A.evaluate(["1"], ["1","0"])
    with pytest.raises(ValueError):
        A.evaluate([], [])

def test_per_label_multilabel():
    a = {"x": {"E1": True, "E2": False}, "y": {"E1": False, "E2": True}}
    b = {"x": {"E1": True, "E2": False}, "y": {"E1": False, "E2": True}}
    res = A.per_label_binary(a, b, ["E1", "E2"], n_boot=50)
    assert set(res) == {"E1", "E2"}
    assert all(r.percent_agreement == 1.0 for r in res.values())

def test_interpret_scale():
    assert A.interpret(0.85) == "cao"
    assert A.interpret(0.10) == "rất thấp"
