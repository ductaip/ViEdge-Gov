import pytest
from viedge.rag import citations as C

ARTS = [
    {"doc_id": "Nghị định 168/2024/NĐ-CP", "dieu": "6", "khoan": ["1", "2"], "bienbao": ["B.7a"]},
    {"doc_id": "QCVN 41:2024/BGTVT", "dieu": "22", "khoan": ["1"], "bienbao": ["P.106a", "W.201"]},
]

@pytest.fixture
def index():
    return C.CitationIndex.from_articles(ARTS)

def test_extract_all_kinds():
    kinds = {c.kind for c in C.extract(
        "Điều 6 khoản 1 điểm a Nghị định 168/2024/NĐ-CP, biển B.7a và QCVN 41:2024/BGTVT")}
    assert kinds == {"dieu", "khoan", "diem", "doc", "bienbao"}

def test_sign_codes_with_one_to_three_digits():
    vals = {c.value for c in C.extract("B.7a W.201 P.106a") if c.kind == "bienbao"}
    assert vals == {"B.7a", "W.201", "P.106a"}

def test_norm_doc_is_case_insensitive(index):
    """Bug đã gặp: index lowercase toàn bộ còn extract giữ nguyên 'NĐ-CP'."""
    assert index.unknown(C.extract("Nghị định 168/2024/NĐ-CP Điều 6")) == []
    assert index.unknown(C.extract("nghị định 168/2024/nđ-cp Điều 6")) == []

def test_detects_fabricated(index):
    bad = index.unknown(C.extract("Điều 999 Nghị định 100/2019/NĐ-CP biển Z.888"))
    assert len(bad) >= 2

def test_check_answer_gate(index):
    good = "Phạt tiền theo Điều 6, khoản 1, Nghị định 168/2024/NĐ-CP."
    assert C.check_answer(good, index).ok
    assert not C.check_answer("Theo Điều 999 Nghị định 100/2019/NĐ-CP.", index).ok
    assert not C.check_answer("Bạn nên hỏi cơ quan chức năng.", index).ok
    assert C.check_answer("Bạn nên hỏi cơ quan chức năng.", index, require_citation=False).ok

def test_hallucination_rate(index):
    v = C.check_answer("Điều 999 Nghị định 100/2019/NĐ-CP", index)
    assert v.hallucination_rate == 1.0
