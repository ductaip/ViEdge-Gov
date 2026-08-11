#!/usr/bin/env python3
"""
Dọn văn bản COPY TỪ TRÌNH DUYỆT (tab "Toàn văn" của vbpl.vn) -> .txt sạch.

VÌ SAO CẦN: tab Toàn văn luôn có cho mọi văn bản, kể cả khi file đính kèm là
bản scan. Nhưng copy từ trình duyệt kéo theo rác: menu điều hướng, breadcrumb,
nút "Tải về / Bản in", khối "Thuộc tính", chú thích chân trang. Nếu để nguyên,
BM25 index cả rác và truy hồi trả về nhiễu.

Dùng:
  1. Mở văn bản trên vbpl.vn -> tab "Toàn văn"
  2. Bôi đen TỪ dòng "CHÍNH PHỦ" (hoặc "QUỐC HỘI") ĐẾN hết phần "Nơi nhận"
  3. Dán vào một file, vd. data/raw/paste/nd168_raw.txt
  4. python scripts/00d_clean_pasted.py data/raw/paste/nd168_raw.txt \
         --out data/raw/nd_168_2024.txt

Script KHÔNG tự đoán chỗ bắt đầu/kết thúc — bạn tự bôi đen. Tự động cắt ở đây
là chỗ dễ mất điều đầu hoặc điều cuối mà không ai phát hiện.
"""
from __future__ import annotations
import argparse, re
from pathlib import Path
from _common import ROOT, log, append_runlog, rel
from viedge.data.desegment import glue_ratio

# Rác giao diện của vbpl.vn và các cổng văn bản nói chung.
NAV_LINES = [
    re.compile(r"(?i)^\s*(Toàn văn|Thuộc tính|Lịch sử|VB liên quan|Lược đồ|Bản PDF|Tải về|Bản in|Xem nhanh)\s*$"),
    re.compile(r"(?i)^\s*CSDL\s*(quốc gia|Bộ|Trung ương).*$"),
    re.compile(r"(?i)^\s*(Văn bản pháp luật|CƠ SỞ DỮ LIỆU QUỐC GIA VỀ VĂN BẢN PHÁP LUẬT)\s*»?\s*$"),
    re.compile(r"(?i)^\s*(Hiệu lực|Ngày có hiệu lực|Ngày ban hành|Người ký|Cơ quan ban hành|Loại văn bản|Số hiệu)\s*:.*$"),
    re.compile(r"(?i)^\s*(Mở|Đóng) tất cả các khối.*$"),
    re.compile(r"(?i)^\s*(Quốc hội|Chính phủ|Thủ tướng Chính phủ|Các Bộ, cơ quan ngang Bộ|Các cơ quan khác)\s*$"),
    re.compile(r"(?i)^\s*(Hiến pháp|Bộ luật|Pháp lệnh|Lệnh|Nghị quyết liên tịch|Thông tư liên tịch|Chỉ thị)\s*$"),
    re.compile(r"^\s*\d{4}\s*đến\s*\d{4}\s*$"),
    re.compile(r"(?i)^\s*(Năm ban hành|Loại văn bản)\s*$"),
    re.compile(r"(?i)^\s*This div, which you should delete.*$"),
    re.compile(r"(?i)^\s*(In trang|Chia sẻ|Gửi email|Lưu|Đánh giá).*$"),
]

# Khối cuối văn bản — giữ lại thì vô hại, nhưng cắt cho gọn index.
TAIL_MARKERS = [
    re.compile(r"(?im)^\s*Nơi nhận\s*:"),
]


def clean(raw: str) -> tuple[str, dict]:
    raw = raw.lstrip("\ufeff").replace("\ufeff", "").replace("\xa0", " ")
    lines = raw.splitlines()
    kept, dropped = [], 0
    for ln in lines:
        if any(p.match(ln) for p in NAV_LINES):
            dropped += 1
            continue
        kept.append(ln.rstrip())
    text = "\n".join(kept)

    # Gỡ mọi thứ sau "Nơi nhận:" (danh sách gửi công văn, không phải nội dung)
    cut = None
    for pat in TAIL_MARKERS:
        m = pat.search(text)
        if m:
            cut = m.start() if cut is None else min(cut, m.start())
    tail_cut = 0
    if cut is not None:
        tail_cut = len(text) - cut
        text = text[:cut]

    # "Đi ều 5." -> "Điều 5."; số trang đứng riêng; dòng trắng thừa
    text = re.sub(r"\bĐi\s+ều\b", "Điều", text)
    text = re.sub(r"\bkho\s+ản\b", "khoản", text)
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), {"nav_lines_dropped": dropped, "tail_chars_cut": tail_cut}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    src = Path(a.src) if Path(a.src).is_absolute() else ROOT / a.src
    if not src.exists():
        log(f"không thấy {src}"); return 1

    raw = src.read_text(encoding="utf-8", errors="replace")
    text, stats = clean(raw)

    out = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    n_dieu = len(re.findall(r"(?m)^\s*Điều\s+\d+", text))
    nums = [int(x) for x in re.findall(r"(?m)^\s*Điều\s+(\d+)", text)]
    gr = glue_ratio(text)
    log(f"bỏ {stats['nav_lines_dropped']} dòng rác giao diện, cắt {stats['tail_chars_cut']} ký tự phần 'Nơi nhận'")
    log(f"đã ghi {rel(out)} ({len(text)} ký tự, {n_dieu} 'Điều N', glue={gr:.3f})")
    if nums:
        log(f"   Điều {min(nums)} → {max(nums)}")
        missing = [n for n in range(min(nums), max(nums) + 1) if n not in set(nums)]
        if missing:
            log(f"   🔴 THIẾU điều: {missing[:20]}")
            log("      Nhiều khả năng bôi đen sót — copy lại cho đủ.")
    if n_dieu == 0:
        log("🔴 Không thấy 'Điều N' nào — kiểm lại đã copy đúng phần Toàn văn chưa.")
        return 1
    if gr >= 0.25:
        log("🟡 Dính chữ bất thường với nguồn copy — kiểm bằng mắt.")
    log("BƯỚC BẮT BUỘC TIẾP THEO: mở file, đọc 10 điều bằng mắt.")
    append_runlog({"step": "00d_clean_pasted", "src": src.name, "n_dieu": n_dieu,
                   "glue": round(gr, 4), **stats})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
