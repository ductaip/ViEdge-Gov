#!/usr/bin/env python3
"""
Phân loại mọi PDF trong data/raw/pdf/ trước khi convert.

Chạy CÁI NÀY ĐẦU TIÊN. Nó cho biết file nào dùng được, file nào là bản scan
phải thay bằng nguồn HTML — tránh mất buổi convert rồi mới phát hiện.

    python scripts/00b_triage_pdfs.py
"""
import re
from pathlib import Path
from _common import ROOT, log
import importlib.util
spec = importlib.util.spec_from_file_location("p2t", Path(__file__).parent / "00_pdf_to_text.py")
p2t = importlib.util.module_from_spec(spec); spec.loader.exec_module(p2t)
from viedge.data.desegment import glue_ratio


def main() -> int:
    pdfs = sorted((ROOT / "data" / "raw" / "pdf").glob("*.pdf"))
    if not pdfs:
        log("không có PDF nào trong data/raw/pdf/"); return 1

    rows = []
    for pdf in pdfs:
        txt = None
        for fn in p2t.EXTRACTORS.values():
            t = fn(pdf)
            if t and (txt is None or len(t) > len(txt)):
                txt = t
        txt = txt or ""
        pages = p2t.n_pages(pdf)
        scanned, per_page = p2t.is_scanned(txt, pages)
        gr = glue_ratio(txt) if not scanned else float("nan")
        n_dieu = len(re.findall(r"Điều\s+\d+", txt))
        if scanned:
            verdict, action = "🔴 SCAN", "thay bằng bản HTML toàn văn"
        elif gr >= 0.25:
            verdict, action = "🟡 DÍNH CHỮ", "convert kèm --learn-from"
        else:
            verdict, action = "🟢 SẠCH", "convert thẳng"
        rows.append((pdf.name, pages, per_page, gr, n_dieu, verdict, action))

    print(f"\n{'FILE':<28}{'TRANG':>6}{'KT/TRANG':>10}{'GLUE':>8}{'ĐIỀU':>7}  {'KẾT LUẬN':<12} VIỆC CẦN LÀM")
    print("-" * 108)
    for name, pages, pp, gr, nd, v, a in rows:
        g = "  —  " if gr != gr else f"{gr:>6.3f}"
        print(f"{name:<28}{pages:>6}{pp:>10.0f}{g:>8}{nd:>7}  {v:<12} {a}")
    print()
    n_scan = sum(1 for r in rows if "SCAN" in r[5])
    if n_scan:
        log(f"{n_scan}/{len(rows)} file là bản scan.")
        log("File .signed trên công báo = ảnh chụp văn bản đã ký, KHÔNG có lớp text.")
        log("Đừng OCR văn bản pháp luật — lỗi OCR ở số hiệu và mức phạt sẽ chui vào")
        log("ViGovQA-GT và detector E3, hỏng đúng thứ đề tài đang đo.")
        log("Lấy bản toàn văn HTML trên xaydungchinhsach.chinhphu.vn thay thế.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
