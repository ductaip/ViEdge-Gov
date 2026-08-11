#!/usr/bin/env python3
"""
Kiểm tra cấu trúc kho văn bản SAU khi parse — chạy trước khi tin vào bất cứ số nào.

Vì sao cần một script riêng: parser chạy không báo lỗi KHÔNG có nghĩa là nó bóc
đúng. Ba kiểu hỏng thường gặp, đều im lặng:

  1. THIẾU ĐIỀU — văn bản bị chia làm nhiều file PDF (công báo hay cắt văn bản
     dài thành "phần 1", "phần tiếp"). Ghép sót một file thì mất cả trăm điều
     mà không có thông báo nào.
  2. TRÙNG ĐIỀU — ghép hai file chồng lấn, một điều xuất hiện hai lần với nội
     dung khác nhau. Truy hồi trả về bản nào là hên xui.
  3. ĐIỀU RỖNG / CỤT — parser bắt được tiêu đề "Điều 12." nhưng thân bị mất do
     ngắt trang, còn lại vài chục ký tự.

Script in bảng để mắt người kiểm. KHÔNG tự sửa — sửa tự động ở đây là chỗ dễ
tạo ra dữ liệu sai mà tin tưởng nhất.
"""
import re
from collections import Counter
from _common import ROOT, load_yaml, log, save_json
from viedge.data import corpus as CO
from viedge.data.desegment import glue_ratio

MIN_CHARS = 80   # dưới ngưỡng này coi là điều rỗng/cụt


def num(dieu: str) -> int:
    m = re.match(r"(\d+)", str(dieu))
    return int(m.group(1)) if m else 0


def check_doc(doc_id: str, arts: list[dict]) -> dict:
    nums = [num(a["dieu"]) for a in arts]
    counts = Counter(a["dieu"] for a in arts)
    dups = sorted([d for d, c in counts.items() if c > 1], key=num)
    lo, hi = (min(nums), max(nums)) if nums else (0, 0)
    present = set(nums)
    gaps = [n for n in range(lo, hi + 1) if n not in present] if nums else []
    thin = sorted([a["dieu"] for a in arts if len(a.get("text", "")) < MIN_CHARS], key=num)
    all_text = " ".join(a.get("text", "") for a in arts)
    return {
        "doc_id": doc_id,
        "n_dieu": len(arts),
        "range": f"{lo}–{hi}" if nums else "—",
        "n_gaps": len(gaps),
        "gaps": gaps[:20],
        "n_dups": len(dups),
        "dups": dups[:10],
        "n_thin": len(thin),
        "thin": thin[:10],
        "glue_ratio": round(glue_ratio(all_text), 3),
        "avg_chars": round(sum(len(a.get("text", "")) for a in arts) / len(arts), 1) if arts else 0,
    }


def main() -> int:
    cfg = load_yaml("configs/retrieval.yaml")
    ap = ROOT / "data" / "processed" / "articles.jsonl"
    if not ap.exists():
        log("chưa có articles.jsonl — chạy `make corpus` trước"); return 1
    arts = CO.load_articles(ap)

    by_doc: dict[str, list[dict]] = {}
    for a in arts:
        by_doc.setdefault(a["doc_id"], []).append(a)

    reports = [check_doc(d, v) for d, v in sorted(by_doc.items())]
    save_json(reports, "results/tables/corpus_verify.json")

    print(f"\n{'VĂN BẢN':<34}{'ĐIỀU':>6}{'KHOẢNG':>10}{'THIẾU':>7}{'TRÙNG':>7}{'RỖNG':>6}{'GLUE':>7}{'KT/ĐIỀU':>9}")
    print("-" * 96)
    for r in reports:
        print(f"{r['doc_id'][:33]:<34}{r['n_dieu']:>6}{r['range']:>10}"
              f"{r['n_gaps']:>7}{r['n_dups']:>7}{r['n_thin']:>6}"
              f"{r['glue_ratio']:>7.3f}{r['avg_chars']:>9.0f}")
    print()

    bad = False
    for r in reports:
        if r["n_gaps"]:
            bad = True
            log(f"🔴 {r['doc_id']}: THIẾU {r['n_gaps']} điều — {r['gaps']}")
            log("   Nguyên nhân hay gặp: văn bản bị cắt làm nhiều PDF, ghép thiếu một phần.")
        if r["n_dups"]:
            bad = True
            log(f"🔴 {r['doc_id']}: TRÙNG {r['n_dups']} điều — {r['dups']}")
            log("   Nguyên nhân hay gặp: ghép hai file chồng lấn nhau.")
        if r["n_thin"]:
            log(f"🟡 {r['doc_id']}: {r['n_thin']} điều dưới {MIN_CHARS} ký tự — {r['thin']}")
            log("   Kiểm tay: bị mất thân do ngắt trang, hay vốn dĩ điều đó ngắn?")
        if r["glue_ratio"] >= 0.25:
            bad = True
            log(f"🔴 {r['doc_id']}: DÍNH CHỮ (glue={r['glue_ratio']}) — convert lại kèm --learn-from")

    # Đối chiếu với số điều mong đợi nếu config có khai báo
    for spec in cfg.get("corpus", []):
        exp = spec.get("expect_n_dieu")
        if not exp:
            continue
        got = next((r["n_dieu"] for r in reports if r["doc_id"] == spec["id"]), 0)
        if got != exp:
            bad = True
            log(f"🔴 {spec['id']}: mong đợi {exp} điều, bóc được {got}")

    if not bad:
        log("✅ Không phát hiện lỗi cấu trúc.")
        log("   Vẫn phải MỞ FILE đọc 10 điều bằng mắt — script không thay được việc đó.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
