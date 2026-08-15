"""Tách đơn vị cho corpus TTHC (thủ tục hành chính) — khác Article vì không có 'Điều N'.

parse_document() luôn trả về rỗng cho loại văn bản này (đã kiểm thật trên
data/raw/tthc_giao_thong.txt: 0 điều) — lỗi im lặng, mất cả corpus TTHC nếu
scripts/03_build_corpus.py không rẽ nhánh đúng. Test này khoá lại hành vi đó.
"""
from viedge.data import corpus as CO

DOC = """Đăng ký, cấp biển số xe lần đầu thực hiện tại Công an cấp tỉnh
Mã thủ tục
1.000377
Lĩnh vực
Đăng ký, quản lý phương tiện giao thông cơ giới đường bộ
Cơ quan thực hiện
Phòng Cảnh sát giao thông

Trình tự thực hiện
Bước 1: Chủ xe kê khai trên cổng dịch vụ công.

Đăng ký, cấp biển số xe lần đầu thực hiện tại Công an cấp xã
Mã thủ tục
1.010910
Lĩnh vực
Đăng ký, quản lý phương tiện giao thông cơ giới đường bộ
Cơ quan thực hiện
Công an xã, phường, thị trấn.

Trình tự thực hiện
Bước 1: Chủ xe kê khai trên cổng dịch vụ công.
"""


def test_parse_document_returns_empty_on_tthc():
    """Chốt đúng lý do phải có parse_tthc(): parse_document không thấy gì."""
    assert CO.parse_document(DOC, "TTHC giao thông") == []


def test_parse_tthc_splits_by_ma_thu_tuc():
    procs = CO.parse_tthc(DOC, "TTHC giao thông")
    assert [p.ma for p in procs] == ["1.000377", "1.010910"]
    assert [p.ten for p in procs] == [
        "Đăng ký, cấp biển số xe lần đầu thực hiện tại Công an cấp tỉnh",
        "Đăng ký, cấp biển số xe lần đầu thực hiện tại Công an cấp xã",
    ]


def test_parse_tthc_keeps_full_body_per_procedure():
    procs = CO.parse_tthc(DOC, "TTHC giao thông")
    assert "Phòng Cảnh sát giao thông" in procs[0].text
    assert "Công an xã, phường, thị trấn" not in procs[0].text
    assert "Công an xã, phường, thị trấn" in procs[1].text


def test_unit_id_uses_ma_not_dieu():
    procs = CO.parse_tthc(DOC, "TTHC giao thông")
    assert procs[0].unit_id == "TTHC giao thông::tthc-1.000377"


def test_retrieval_text_does_not_say_dieu():
    """Article.retrieval_text() ghi cứng 'Điều N' — Procedure không được lặp lỗi
    đó, gọi một thủ tục hành chính là 'Điều' là sai thuật ngữ."""
    procs = CO.parse_tthc(DOC, "TTHC giao thông")
    rt = procs[0].retrieval_text()
    assert "Điều" not in rt
    assert "Thủ tục 1.000377" in rt


def test_to_dict_compatible_with_citation_index():
    from viedge.rag.citations import CitationIndex

    procs = CO.parse_tthc(DOC, "TTHC giao thông")
    idx = CitationIndex.from_articles([p.to_dict() for p in procs])
    assert "tthc giao thông" in idx.docs
    assert "1.000377" in idx.dieu
    assert "1.010910" in idx.dieu


def test_no_markers_returns_empty():
    assert CO.parse_tthc("văn bản không có mã thủ tục nào cả", "X") == []


def test_real_file_all_nine_procedures_no_gplx():
    """Hồi quy trên file thật: đúng 9 thủ tục, KHÔNG có GPLX (đã loại theo
    quyết định phạm vi — Thông tư 12/2025/TT-BCA đang biến động)."""
    from pathlib import Path

    p = Path(__file__).parent.parent / "data" / "raw" / "tthc_giao_thong.txt"
    if not p.exists():
        return
    procs = CO.parse_tthc(p.read_text(encoding="utf-8"), "TTHC giao thông")
    assert len(procs) == 9
    assert not any("giấy phép lái xe" in p.ten.lower() for p in procs)
