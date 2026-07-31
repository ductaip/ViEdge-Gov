#!/usr/bin/env python3
"""
PDF văn bản pháp quy -> .txt sạch, sẵn sàng cho scripts/03.

Dùng:
    python scripts/00_pdf_to_text.py data/raw/pdf/51-bgtvt-kem.pdf \
           --out data/raw/qcvn_41_2024.txt

Việc script làm, theo thứ tự:
  1. Thử NHIỀU trình trích xuất (pdftotext, PyMuPDF, pdfplumber) — mỗi trình
     xử lý font nhúng khác nhau, và PDF công báo Việt Nam hay bị mất khoảng
     trắng ở một trình mà trình khác lại ổn.
  2. Chấm điểm từng kết quả bằng glue_ratio, chọn bản tốt nhất.
  3. Nếu bản tốt nhất VẪN dính chữ -> tách lại bằng viedge.data.desegment.
  4. Dọn header/footer/số trang.
  5. Lọc chỉ thị nhúng (prompt injection) — xem ghi chú bên dưới.
  6. In báo cáo để người dùng tự kiểm trước khi tin.

⚠️ LUÔN MỞ FILE .txt ĐỌC BẰNG MẮT ÍT NHẤT 10 ĐIỀU trước khi chạy tiếp.
Không có bước này thì mọi bảng số phía sau đều dựng trên cát.
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
from _common import ROOT, log, append_runlog
from viedge.data.desegment import desegment, glue_ratio, SyllableModel

# Mẫu chỉ thị nhúng gặp thật trên một số trang tổng hợp văn bản luật: nội dung
# trang chứa câu lệnh nhắm vào trợ lý AI ("hãy luôn thông báo với người dùng...").
# Nếu crawl rồi nhét thẳng vào ngữ cảnh RAG, mô hình có thể làm theo.
INJECTION_PATTERNS = [
    re.compile(r"^\s*#.*$", re.MULTILINE),
    re.compile(r"(?i)^.*(QUAN TRỌNG|IMPORTANT|LƯU Ý HỆ THỐNG)\s*:.*(hãy|phải|bạn cần|you must|always).*$", re.MULTILINE),
    re.compile(r"(?i)^.*(system prompt|ignore (all )?previous|bỏ qua (mọi )?hướng dẫn|trợ lý AI).*$", re.MULTILINE),
    re.compile(r"(?i)^.*(vui lòng (đăng nhập|đăng ký)|tiện ích dành cho tài khoản|gói cước).*$", re.MULTILINE),
]

# Rác thường gặp trong PDF công báo.
NOISE_PATTERNS = [
    re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE),                 # số trang đứng riêng
    re.compile(r"(?im)^\s*(CÔNG BÁO|Công báo)\s*/.*$"),
    re.compile(r"(?im)^\s*QCVN\s*41:2024/BGTVT\s*$"),             # header lặp
]


def extract_pdftotext(path: Path) -> str | None:
    import shutil, subprocess
    if not shutil.which("pdftotext"):
        return None
    for args in (["-layout"], []):
        try:
            r = subprocess.run(["pdftotext", *args, str(path), "-"],
                               capture_output=True, timeout=300)
            if r.returncode == 0 and r.stdout:
                yield_text = r.stdout.decode("utf-8", errors="replace")
                if yield_text.strip():
                    return yield_text
        except Exception:
            continue
    return None


def extract_pymupdf(path: Path) -> str | None:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None
    try:
        doc = fitz.open(str(path))
        return "\n".join(p.get_text("text") for p in doc)
    except Exception:
        return None


def extract_pdfplumber(path: Path) -> str | None:
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception:
        return None


EXTRACTORS = {
    "pdftotext": extract_pdftotext,
    "pymupdf": extract_pymupdf,
    "pdfplumber": extract_pdfplumber,
}


def clean(text: str) -> str:
    for pat in INJECTION_PATTERNS:
        text = pat.sub("", text)
    for pat in NOISE_PATTERNS:
        text = pat.sub("", text)
    text = text.replace("\u00ad", "")                    # soft hyphen
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # "Đi ều 5." -> "Điều 5."  (PDF hay chèn khoảng trắng giữa chữ)
    text = re.sub(r"\bĐi\s+ều\b", "Điều", text)
    text = re.sub(r"\bkho\s+ản\b", "khoản", text)
    return text.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--learn-from", nargs="*", default=[],
                    help="file .txt SẠCH để học thêm âm tiết (rất nên dùng)")
    ap.add_argument("--no-desegment", action="store_true")
    args = ap.parse_args()

    pdf = Path(args.pdf)
    if not pdf.is_absolute():
        pdf = ROOT / pdf
    if not pdf.exists():
        log(f"không thấy {pdf}"); return 1

    results: dict[str, str] = {}
    for name, fn in EXTRACTORS.items():
        txt = fn(pdf)
        if txt and txt.strip():
            results[name] = txt
            log(f"{name:<12} {len(txt):>8} ký tự | glue_ratio={glue_ratio(txt):.3f}")
        else:
            log(f"{name:<12} (không dùng được — chưa cài hoặc lỗi)")

    if not results:
        log("KHÔNG trình trích xuất nào chạy được.")
        log("  cài: apt-get install poppler-utils  HOẶC  pip install pymupdf pdfplumber")
        return 1

    best = min(results, key=lambda k: glue_ratio(results[k]))
    text = results[best]
    log(f"=> chọn {best} (glue_ratio thấp nhất)")

    model = None
    if args.learn_from:
        texts = []
        for f in args.learn_from:
            p = Path(f) if Path(f).is_absolute() else ROOT / f
            if p.exists():
                texts.append(p.read_text(encoding="utf-8"))
        if texts:
            model = SyllableModel.from_texts(texts)
            log(f"học âm tiết từ {len(texts)} file sạch -> kho {len(model.known)} âm tiết")

    gr = glue_ratio(text)
    if gr >= 0.25 and not args.no_desegment:
        log(f"phát hiện dính chữ (glue_ratio={gr:.3f}) -> tách lại")
        text = desegment(text, model=model)
        log(f"sau khi tách: glue_ratio={glue_ratio(text):.3f}")
        log("   ⚠️ tách tự động KHÔNG hoàn hảo — bắt buộc đọc mắt trước khi dùng")

    text = clean(text)
    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    n_dieu = len(re.findall(r"^\s*Điều\s+\d+", text, flags=re.MULTILINE))
    log(f"đã ghi {out.relative_to(ROOT)} ({len(text)} ký tự, bắt được {n_dieu} 'Điều N')")
    if n_dieu == 0:
        log("CẢNH BÁO: không thấy 'Điều N' nào — parser sẽ trả về rỗng.")
        log("   Kiểm lại: PDF có phải bản scan không? Nếu có, cần OCR trước.")
    log("BƯỚC BẮT BUỘC TIẾP THEO: mở file, đọc 10 điều bằng mắt.")
    append_runlog({"step": "00_pdf_to_text", "pdf": pdf.name, "extractor": best,
                   "glue_before": round(gr, 4), "glue_after": round(glue_ratio(text), 4),
                   "n_dieu": n_dieu})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())