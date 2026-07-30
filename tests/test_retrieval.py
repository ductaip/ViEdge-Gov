import pytest
from viedge.data import corpus as CO
from viedge.rag import retrieval as R

DOC = """Điều 6. Mức phạt vi phạm
1. Phạt tiền từ 800.000 đồng đối với hành vi không mang giấy phép lái xe.
Điều 7. Biển báo cấm
1. Biển báo cấm B.7a có ý nghĩa cấm xe tải đi vào.
"""

@pytest.fixture
def units():
    arts = CO.parse_document(DOC, "ND")
    return {a.unit_id: a.retrieval_text() for a in arts}

def test_parser_hierarchy():
    arts = CO.parse_document(DOC, "ND")
    assert [a.dieu for a in arts] == ["6", "7"]
    assert arts[0].title == "Mức phạt vi phạm"
    assert len(arts[0].khoan) == 1
    assert arts[1].bienbao == ["B.7a"]

def test_bm25_diacritic_insensitive(units):
    bm = R.BM25().fit(units)
    with_marks = bm.search("biển báo cấm xe tải", top_k=2)
    without = bm.search("bien bao cam xe tai", top_k=2)
    assert with_marks[0][0].endswith("dieu-7")
    assert without and without[0][0].endswith("dieu-7")

def test_rrf_rank_based_not_score_based():
    """RRF hợp nhất theo hạng, nên thang điểm lệch nhau không ảnh hưởng."""
    run_a = [("x", 1000.0), ("y", 1.0)]
    run_b = [("x", 0.9), ("y", 0.8)]
    fused = R.rrf_fuse([run_a, run_b])
    assert fused[0][0] == "x"
    scaled = R.rrf_fuse([[("x", 1e9), ("y", 1e-9)], run_b])
    assert [d for d, _ in fused] == [d for d, _ in scaled]

def test_rrf_weight_validation():
    with pytest.raises(ValueError):
        R.rrf_fuse([[("a", 1.0)]], weights=[1.0, 1.0])

def test_dynamic_top_k_bounds():
    fused = [("a", 1.0), ("b", 0.9), ("c", 0.2), ("d", 0.1)]
    out = R.dynamic_top_k(fused, min_k=1, max_k=10, drop_ratio=0.55)
    assert [d for d, _ in out] == ["a", "b"]
    assert len(R.dynamic_top_k(fused, min_k=3, max_k=10, drop_ratio=0.55)) >= 3
    assert R.dynamic_top_k([], min_k=1, max_k=5) == []

def test_prf_beta2_favours_recall():
    high_recall = R.prf(["a", "b", "c", "d"], ["a", "b"], beta=2.0)
    high_prec = R.prf(["a"], ["a", "b"], beta=2.0)
    assert high_recall["recall"] == 1.0
    assert high_recall["f2"] > high_prec["f2"]
    assert R.prf(["a"], [])["f2"] == 0.0
