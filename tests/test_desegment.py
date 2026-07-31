import pytest
from viedge.data.desegment import (desegment, glue_ratio, is_syllable,
                                   SyllableModel, SEED_SYLLABLES)

# Đoạn dính chữ THẬT, trích từ bản PDF chính thức QCVN 41:2024 (datafiles.chinhphu.vn)
GLUED = "Quychuẩnnày quyđịnh vềbáohiệuđườngbộbaogồm:đèntínhiệugiaothông"
EXPECTED_WORDS = ["Quy", "chuẩn", "này", "quy", "định", "về", "báo", "hiệu",
                  "đường", "bộ", "bao", "gồm", "đèn", "tín", "hiệu", "giao", "thông"]
CLEAN = "Người điều khiển phương tiện phải tuân thủ quy định về tốc độ theo Điều 6."


@pytest.mark.parametrize("s", ["nghiêng", "phương", "quy", "đường", "biển", "tín", "hiệu"])
def test_valid_syllables(s):
    assert is_syllable(s)


@pytest.mark.parametrize("s", ["quychuẩn", "đườngbộ", "xzqw", "giaothông"])
def test_invalid_syllables(s):
    assert not is_syllable(s)


def test_glue_ratio_discriminates():
    assert glue_ratio(GLUED) > 0.5
    assert glue_ratio(CLEAN) < 0.15


def test_desegment_real_pdf_sample():
    out = desegment(GLUED)
    assert glue_ratio(out) < 0.15
    words = out.replace(":", " ").split()
    assert words == EXPECTED_WORDS, words


def test_clean_text_untouched():
    """Quan trọng: văn bản sạch KHÔNG được đụng vào."""
    assert desegment(CLEAN) == CLEAN


def test_header_case_preserved():
    out = desegment("CỘNGHOÀXÃHỘICHỦNGHĨAVIỆTNAM")
    assert out == "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM", out


def test_model_learns_from_clean_text():
    m = SyllableModel.from_texts(["kiểm định phương tiện cơ giới"])
    assert "kiểm" in m.known and len(m.known) > len(SEED_SYLLABLES) - 1


def test_unknown_syllable_still_segmented():
    """Âm tiết lạ (tên riêng) vẫn phải tách được nhờ hợp cấu trúc."""
    out = desegment("xelamchạytrênđường")
    assert len(out.split()) >= 4