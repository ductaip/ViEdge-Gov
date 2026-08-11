#!/usr/bin/env python3
"""
.doc / .docx -> .txt sạch.

VÌ SAO ƯU TIÊN .doc HƠN PDF: Cơ sở dữ liệu quốc gia (vbpl.vn) đính kèm bản
Word gốc của văn bản, vd. "168.2024.NĐ.CP.doc". Đó là văn bản có cấu trúc thật,
không phải trang in — nên KHÔNG có chuyện dính chữ, KHÔNG có header/footer lặp,
KHÔNG có ngắt trang cắt ngang điều luật. Lấy được .doc thì bỏ hẳn nhánh PDF.

Dùng:
    python scripts/00c_doc_to_text.py data/raw/doc/168.2024.ND.CP.doc \
        --out data/raw/nd_168_2024.txt
"""
from __future__ import annotations
import argparse, re, shutil, subprocess, sys
from pathlib import Path
from _common import ROOT, log, append_runlog, rel
from viedge.data.desegment import glue_ratio

# Dùng lại bộ lọc của nhánh PDF để không phân đôi logic vệ sinh dữ liệu.
import importlib.util
_spec = importlib.util.spec_from_file_location("p2t", Path(__file__).parent / "00_pdf_to_text.py")
p2t = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(p2t)


def via_docx(path: Path) -> str | None:
    """.docx — đọc trực tiếp bằng python-docx."""
    if path.suffix.lower() != ".docx":
        return None
    try:
        import docx
    except ImportError:
        return None
    try:
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    except Exception:
        return None


def via_antiword(path: Path) -> str | None:
    """.doc cũ (OLE2) — antiword nhanh và giữ xuống dòng tốt."""
    if not shutil.which("antiword"):
        return None
    try:
        r = subprocess.run(["antiword", "-w", "0", str(path)], capture_output=True, timeout=180)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        pass
    return None


def via_libreoffice(path: Path) -> str | None:
    """Đường chắc ăn nhất: LibreOffice chuyển .doc/.docx -> .txt."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    out_dir = Path("/tmp/viedge_doc2txt")
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "txt:Text (encoded):UTF8",
             "--outdir", str(out_dir), str(path)],
            capture_output=True, timeout=300,
        )
        cand = out_dir / (path.stem + ".txt")
        if cand.exists():
            return cand.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return None


CONVERTERS = {"python-docx": via_docx, "antiword": via_antiword, "libreoffice": via_libreoffice}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src = Path(args.doc)
    if not src.is_absolute():
        src = ROOT / src
    if not src.exists():
        log(f"không thấy {src}"); return 1

    results = {}
    for name, fn in CONVERTERS.items():
        t = fn(src)
        if t and t.strip():
            results[name] = t
            log(f"{name:<14} {len(t):>8} ký tự | glue_ratio={glue_ratio(t):.3f}")
        else:
            log(f"{name:<14} (không dùng được)")

    if not results:
        log("KHÔNG chuyển đổi được. Cài một trong các cách sau:")
        log("   sudo apt-get install -y antiword libreoffice-writer")
        log("   pip install python-docx          # chỉ cho .docx")
        log("Hoặc mở file bằng Word/LibreOffice rồi 'Save As -> Plain Text (UTF-8)'.")
        return 1

    best = max(results, key=lambda k: len(results[k]))
    text = p2t.clean(results[best])
    log(f"=> chọn {best}")

    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    n_dieu = len(re.findall(r"^\s*Điều\s+\d+", text, flags=re.MULTILINE))
    gr = glue_ratio(text)
    log(f"đã ghi {rel(out)} ({len(text)} ký tự, {n_dieu} 'Điều N', glue={gr:.3f})")
    if n_dieu == 0:
        log("CẢNH BÁO: không thấy 'Điều N' nào — kiểm lại file nguồn.")
    if gr >= 0.25:
        log("CẢNH BÁO: dính chữ bất thường với nguồn .doc — kiểm bằng mắt.")
    log("BƯỚC BẮT BUỘC TIẾP THEO: mở file, đọc 10 điều bằng mắt.")
    append_runlog({"step": "00c_doc_to_text", "src": src.name, "converter": best,
                   "n_dieu": n_dieu, "glue": round(gr, 4)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
