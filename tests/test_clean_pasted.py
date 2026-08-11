"""Test bộ dọn text copy từ trình duyệt."""
import importlib.util, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "cp", Path(__file__).resolve().parents[1] / "scripts" / "00d_clean_pasted.py")
cp = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(cp)

RAW = """CSDL quốc gia về VBPL »
Toàn văn
Thuộc tính
Tải về
Hiệu lực: Còn hiệu lực
Ngày có hiệu lực: 01/01/2025

Điều 1. Phạm vi điều chỉnh
1. Nghị định này quy định về xử phạt vi phạm hành chính.

2

Đi ều 2. Đối tượng áp dụng
1. Cá nhân, tổ chức có hành vi vi phạm.

Nơi nhận:
- Ban Bí thư Trung ương Đảng;
"""


def test_nav_junk_removed():
    out, st = cp.clean(RAW)
    for junk in ("CSDL quốc gia", "Thuộc tính", "Hiệu lực:", "Ngày có hiệu lực"):
        assert junk not in out, junk
    assert st["nav_lines_dropped"] >= 5


def test_content_preserved():
    out, _ = cp.clean(RAW)
    assert "Phạm vi điều chỉnh" in out
    assert "xử phạt vi phạm hành chính" in out


def test_split_word_repaired():
    """PDF/HTML hay chèn khoảng trắng giữa 'Đi ều' — không sửa thì mất điều đó."""
    out, _ = cp.clean(RAW)
    assert "Điều 2. Đối tượng áp dụng" in out
    assert "Đi ều" not in out


def test_tail_cut_at_noi_nhan():
    out, st = cp.clean(RAW)
    assert "Ban Bí thư" not in out
    assert st["tail_chars_cut"] > 0


def test_bare_page_number_removed():
    out, _ = cp.clean(RAW)
    assert "\n2\n" not in out


def test_bom_stripped():
    out, _ = cp.clean("\ufeffĐiều 1. Tiêu đề\n1. Nội dung.")
    assert out.startswith("Điều 1")
