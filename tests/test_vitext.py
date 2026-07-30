import pytest
from viedge import vitext as V

def test_strip_marks_and_fold():
    assert V.strip_marks("Phương tiện Đường bộ") == "Phuong tien Duong bo"
    assert V.fold("ĐIỀU KHOẢN") == "dieu khoan"
    assert V.fold("abc") == "abc"

def test_diacritic_ratio():
    assert V.diacritic_ratio("Người điều khiển") > 0.2
    assert V.diacritic_ratio("Nguoi dieu khien") == 0.0
    assert V.diacritic_ratio("123 !!!") == 0.0

def test_mojibake_detection():
    # vỡ một phần (lẫn ký tự đúng và ký tự vỡ) — ca hay gặp khi nén mô hình
    assert V.mojibake_hits("Ngưá»i Ä'iá»u khiá»n")
    # vỡ toàn phần, round-trip phục hồi được
    broken = "Người điều khiển".encode("utf-8").decode("latin-1")
    assert V.mojibake_hits(broken)
    assert V.demojibake(broken) == "Người điều khiển"
    # văn bản sạch không bị gắn cờ
    assert not V.mojibake_hits("Người điều khiển phương tiện phải tuân thủ.")
    assert not V.mojibake_hits("Phạt tiền từ 800.000 đồng đến 1.000.000 đồng.")
    assert not V.mojibake_hits("Tốc độ tối đa 60 km/h, nhiệt độ 35°C.")
    assert V.mojibake_hits("bình thường\x00xấu")
    assert V.mojibake_hits("lỗi \ufffd ở đây")

def test_ngram_repeat_and_truncation():
    assert V.max_ngram_repeat("Phạt tiền từ 800.000 đồng. " * 20) > 0.15
    assert V.max_ngram_repeat("Một câu văn hoàn toàn bình thường không lặp lại gì cả nhé bạn ơi.") < 0.15
    assert V.looks_truncated("Người điều khiển phương tiện phải")
    assert not V.looks_truncated("Người điều khiển phương tiện phải tuân thủ.")

def test_lexicon_no_false_positive_on_clean_text():
    clean = "Người điều khiển phương tiện phải tuân thủ quy định về tốc độ."
    lex = V.VietLexicon.from_texts([clean] * 3)
    assert lex.tone_loss_tokens(clean) == []
    assert len(lex.tone_loss_tokens(V.strip_marks(clean))) >= 4

def test_english_run_detection():
    assert V.english_run_hits("The answer is that you should note the following")
    assert not V.english_run_hits("Xe ô tô hạng B chở người đến 8 chỗ")
