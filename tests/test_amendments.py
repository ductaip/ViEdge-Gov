import pytest
from viedge.data.amendments import (parse_amending_document, AmendmentIndex,
                                    augment_context)

# Trích cấu trúc THẬT của Nghị định 238/2026/NĐ-CP (bản ký, 14 trang)
ND238 = '''Điều 2. Sửa đổi, bổ sung một số điểm, khoản của Điều 6
1. Bổ sung khoản 1a vào trước khoản 1 như sau:
"1a. Phạt cảnh cáo đối với người điều khiển xe ô tô chở trẻ em dưới 10 tuổi."

Điều 3. Sửa đổi, bổ sung điểm b khoản 8 Điều 13
"b) Điều khiển xe không gắn đủ biển số."

Điều 19. Bổ sung, thay thế, bãi bỏ một số cụm từ, điểm, khoản, điều
1. Bổ sung cụm từ ", trừ hành vi vi phạm quy định tại điểm b khoản 3a Điều 29 của Nghị định này" vào sau cụm từ "xe được kéo khi kéo nhau" tại điểm h khoản 3 Điều 6.
2. Bổ sung cụm từ "hoặc chuyển làn đường" vào sau cụm từ "làn đường liền kề" tại điểm a khoản 2 Điều 6; điểm e khoản 1 Điều 7; điểm h khoản 6 Điều 8.
17. Bãi bỏ điểm d, điểm đ khoản 17 Điều 32.

Điều 20. Hiệu lực thi hành
1. Nghị định này có hiệu lực thi hành từ ngày 15 tháng 8 năm 2026.

Điều 21. Điều khoản chuyển tiếp
Trường hợp hành vi vi phạm xảy ra trước ngày Nghị định này có hiệu lực thì áp dụng nghị định đang có hiệu lực tại thời điểm thực hiện hành vi.
'''
SRC, TGT, EFF = "Nghị định 238/2026/NĐ-CP", "Nghị định 168/2024/NĐ-CP", "2026-08-15"


@pytest.fixture
def ams():
    return parse_amending_document(ND238, SRC, TGT, EFF)


@pytest.fixture
def index(ams):
    return AmendmentIndex.from_amendments(ams)


def test_title_target_extracted(ams):
    pairs = {(a.source_dieu, a.target_dieu) for a in ams}
    assert ("2", "6") in pairs
    assert ("3", "13") in pairs


def test_enforcement_articles_ignored(ams):
    """Điều 'Hiệu lực thi hành' và 'Điều khoản chuyển tiếp' không sửa gì cả."""
    assert "20" not in {a.source_dieu for a in ams}
    assert "21" not in {a.source_dieu for a in ams}


def test_phrase_level_article_expands_to_all_targets(ams):
    t = sorted({a.target_dieu for a in ams if a.source_dieu == "19"}, key=int)
    assert t == ["6", "7", "8", "32"], t


def test_cross_reference_inside_quotes_is_not_a_target(ams):
    """Điều 29 chỉ xuất hiện trong CỤM TỪ ĐƯỢC CHÈN -> không phải điều bị sửa.

    Bỏ qua chi tiết này thì lớp phủ gắn sửa đổi vào nhầm điều, và câu trả lời
    trích dẫn sai — đúng loại lỗi E3 mà đề tài đang đo.
    """
    assert "29" not in {a.target_dieu for a in ams}


def test_khoan_diem_captured_from_title(ams):
    a = next(a for a in ams if a.source_dieu == "3")
    assert a.khoan == ["8"] and a.diem == ["b"]


def test_effective_date_switch(index):
    uid = f"{TGT}::dieu-6"
    assert index.for_unit(uid, as_of="2026-08-01") == []
    assert len(index.for_unit(uid, as_of="2026-08-20")) == 2
    assert len(index.for_unit(uid, as_of=None)) == 2


def test_augment_context_labels_amendments(index):
    uid = f"{TGT}::dieu-6"
    units = {uid: "Điều 6. Xử phạt người điều khiển xe ô tô"}
    after = augment_context([uid], units, index, as_of="2026-08-20")
    before = augment_context([uid], units, index, as_of="2026-08-01")
    assert "[SỬA ĐỔI" in after and "1a" in after
    assert "[SỬA ĐỔI" not in before
    assert before.strip() == units[uid]


def test_index_stats(index):
    st = index.stats()
    # Điều 2 -> 6 ; Điều 3 -> 13 ; Điều 19 -> 6,7,8,32  => 5 điều bị tác động
    assert st["n_affected_dieu"] == 5, st
    assert set(st["affected_dieu"]) == {"6", "7", "8", "13", "32"}
    assert st["n_amendments"] == 6


def test_unit_id_format(ams):
    a = ams[0]
    assert a.target_unit_id == f"{TGT}::dieu-{a.target_dieu}"
