import pytest
from viedge import vitext as V
from viedge.rag import citations as C
from viedge.taxonomy import detectors as D

CLEAN = "Người điều khiển phương tiện phải tuân thủ quy định về tốc độ theo Điều 6."

@pytest.fixture
def ctx():
    lex = V.VietLexicon.from_texts([CLEAN] * 3)
    idx = C.CitationIndex.from_articles([{"doc_id": "ND", "dieu": "6", "khoan": ["1"]}])
    return lex, idx

def test_clean_text_not_flagged(ctx):
    lex, idx = ctx
    fl = D.flags(D.compute_signals(CLEAN, lexicon=lex, index=idx),
                 reference_diacritic_ratio=V.diacritic_ratio(CLEAN))
    assert not any(fl[c] for c in ("E1", "E2", "E3", "E5"))

@pytest.mark.parametrize("code,text", [
    ("E1", "Ngưá»i Ä'iá»u khiá»n"),
    ("E2", V.strip_marks(CLEAN)),
    ("E3", "Căn cứ Điều 4242 Nghị định 999/1999/NĐ-CP."),
    ("E5", "The answer is that you should note the following which is based on this."),
    ("E6", "Phạt tiền từ 800.000 đồng. " * 30),
])
def test_each_code_fires(ctx, code, text):
    lex, idx = ctx
    fl = D.flags(D.compute_signals(text, lexicon=lex, index=idx),
                 reference_diacritic_ratio=V.diacritic_ratio(CLEAN))
    assert fl[code], f"{code} không bật trên: {text[:40]}"

def test_e4_is_never_automatic(ctx):
    """E4 (sai thuật ngữ) KHÔNG thể tự động hoá — phải do người phán."""
    lex, idx = ctx
    sig = D.compute_signals("Thủ tục cấp đổi và cấp lại giấy phép lái xe.", lexicon=lex, index=idx)
    assert sig.confusion_terms
    assert D.flags(sig)["E4"] is False
    assert D.needs_human_review(sig, D.flags(sig)) is True

def test_relative_diacritic_drop_triggers_e2(ctx):
    lex, idx = ctx
    partial = "Người dieu khien phuong tien phai tuan thu quy dinh"
    sig = D.compute_signals(partial, lexicon=lex, index=idx)
    assert D.flags(sig, reference_diacritic_ratio=0.30)["E2"]

def test_signals_serialisable(ctx):
    lex, idx = ctx
    d = D.compute_signals(CLEAN, lexicon=lex, index=idx).to_dict()
    assert "diacritic_ratio" in d and isinstance(d["mojibake_hits"], list)
