import pytest
from viedge.data import vmlu, vigovqa

POP = [{"id": f"q{i}", "subject": f"mon{i % 58}"} for i in range(10880)]

def test_stratified_sample_reproducible_and_covers_all_subjects():
    s1 = vmlu.stratified_sample(POP, 2000, seed=20260825)
    s2 = vmlu.stratified_sample(POP, 2000, seed=20260825)
    assert len(s1) == 2000
    assert [r["id"] for r in s1] == [r["id"] for r in s2]
    assert not vmlu.coverage_report(s1, POP)["missing_subjects"]

def test_different_seed_gives_different_sample():
    a = vmlu.stratified_sample(POP, 500, seed=1)
    b = vmlu.stratified_sample(POP, 500, seed=2)
    assert [r["id"] for r in a] != [r["id"] for r in b]

def test_sample_larger_than_population_returns_all():
    assert len(vmlu.stratified_sample(POP[:10], 100)) == 10

def test_sampling_error_shrinks_with_n():
    small = vmlu.sampling_error_note(500, 10880)["margin_of_error_abs"]
    big = vmlu.sampling_error_note(4000, 10880)["margin_of_error_abs"]
    assert small > big

def test_missing_subject_key_raises():
    with pytest.raises(KeyError):
        vmlu.detect_subject_key([{"id": "x", "q": "y"}])

VALID = {
    "id": "gt-1", "question": "Mức phạt là bao nhiêu?", "answer_reference": "800.000đ",
    "citations": [{"doc": "ND", "dieu": "6", "khoan": "1"}],
    "question_type": "muc_phat", "difficulty": "single_hop", "source_of_question": "real_forum",
}

def test_valid_item_passes():
    assert vigovqa.validate(VALID) == []

@pytest.mark.parametrize("patch,expect", [
    ({"citations": []}, "trích dẫn"),
    ({"question_type": "sai"}, "question_type"),
    ({"question": "Không có dấu hỏi"}, "dấu ?"),
    ({"difficulty": "multi_hop"}, "multi_hop"),
    ({"answer_reference": ""}, "answer_reference"),
])
def test_invalid_items_caught(patch, expect):
    errs = vigovqa.validate({**VALID, **patch})
    assert any(expect in e for e in errs), errs

def test_gold_units_dedup():
    item = vigovqa.QAItem(id="x", question="q?", answer_reference="a", citations=[
        vigovqa.CitationRef(doc="ND", dieu="6", khoan="1"),
        vigovqa.CitationRef(doc="ND", dieu="6", khoan="2"),
    ])
    assert item.gold_units() == ["ND::dieu-6"]
