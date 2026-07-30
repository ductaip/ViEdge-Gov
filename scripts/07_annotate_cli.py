#!/usr/bin/env python3
"""
CLI gán nhãn taxonomy. Chạy: python scripts/07_annotate_cli.py --who A --queue <file>

QUY TẮC BẤT DI BẤT DỊCH: hai người gán ĐỘC LẬP, không xem nhãn của nhau,
không thảo luận trước khi cả hai xong. Nếu vi phạm, AC1 vô nghĩa và hội đồng
có quyền loại phần phân tích này.
"""
import argparse, json
from pathlib import Path
from _common import ROOT, log
from viedge.taxonomy.detectors import E_LABELS

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--who", required=True, choices=["A", "B"])
    ap.add_argument("--queue", required=True)
    ap.add_argument("--hide-auto", action="store_true",
                    help="Ẩn cờ tự động để tránh mồi neo (KHUYẾN NGHỊ BẬT)")
    args = ap.parse_args()

    qpath = Path(args.queue)
    if not qpath.is_absolute():
        qpath = ROOT / qpath
    items = [json.loads(l) for l in qpath.read_text(encoding="utf-8").splitlines() if l.strip()]
    out = ROOT / "results" / "taxonomy" / f"labels_{qpath.stem}_{args.who}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
        log(f"tiếp tục: đã gán {len(done)} mẫu")

    codes = list(E_LABELS)
    print("\nMã lỗi: " + " | ".join(f"{i+1}={c} ({E_LABELS[c]})" for i, c in enumerate(codes)))
    print("Nhập số của các lỗi có mặt, cách nhau bằng dấu cách. Enter = không lỗi. q = thoát.\n")

    with out.open("a", encoding="utf-8") as f:
        for it in items:
            if it["id"] in done:
                continue
            print("=" * 72)
            print(f"[{it['id']}] {it.get('tag','')}")
            print(f"PROMPT: {it.get('prompt','')[:200]}")
            print("-" * 72)
            print(it.get("output", "")[:1500])
            print("-" * 72)
            if not args.hide_auto:
                print("cờ tự động:", sorted(k for k, v in it.get("auto_flags", {}).items() if v))
            raw = input("lỗi? > ").strip()
            if raw.lower() == "q":
                break
            picked = set()
            for tok in raw.split():
                if tok.isdigit() and 1 <= int(tok) <= len(codes):
                    picked.add(codes[int(tok) - 1])
            note = input("ghi chú (Enter bỏ qua) > ").strip()
            f.write(json.dumps({"id": it["id"], "tag": it.get("tag", ""), "annotator": args.who,
                                "labels": {c: (c in picked) for c in codes}, "note": note},
                               ensure_ascii=False) + "\n")
            f.flush()
    log(f"đã lưu -> {out.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
