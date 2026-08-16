#!/usr/bin/env python3
"""
Sub-sample hàng đợi gán nhãn theo tầng (tag × cờ chính).

Vấn đề: queue toàn phần dễ lên 400-600 mẫu → gán tay hết trong 5 ngày không nổi.
Cách xử: lấy k mẫu mỗi tầng (tag, cờ chính) để mỗi ô có đủ mẫu, KHÔNG để
nghiêng về precision nào hoặc mã lỗi nào chỉ vì tần suất cờ khác nhau.

Đầu vào : results/taxonomy/queue_*.jsonl   (output của scripts/06_run_error_probe.py)
Đầu ra  : results/taxonomy/queue_sampled.jsonl  (dùng CHUNG cho A và B)
"""
from __future__ import annotations
import json, argparse, random
from collections import defaultdict
from pathlib import Path
from _common import ROOT, log, save_json, append_runlog

QUEUE_DIR = ROOT / "results" / "taxonomy"
OUT = QUEUE_DIR / "queue_sampled.jsonl"


def primary_flag(flags: dict) -> str:
    """Cờ chính = mã Ex được bật đầu tiên theo thứ tự E1..E6.
    Không có cờ nào → 'none'. Dùng để phân tầng, không phải để làm nhãn."""
    for k in ("E1", "E2", "E3", "E4", "E5", "E6"):
        if flags.get(k):
            return k
    return "none"


def load_all_queues() -> list[dict]:
    files = sorted(QUEUE_DIR.glob("queue_*.jsonl"))
    # Loại chính file output
    files = [f for f in files if f.name != "queue_sampled.jsonl"]
    if not files:
        raise SystemExit(
            f"không có queue_*.jsonl trong {QUEUE_DIR.relative_to(ROOT)}\n"
            f"   chạy make probe (hoặc scripts/06_run_error_probe.py) trước"
        )
    items = []
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                items.append(json.loads(line))
    log(f"nạp {len(items)} mẫu từ {len(files)} file queue")
    return items


def stratify(items: list[dict], k_per_stratum: int, seed: int) -> list[dict]:
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for it in items:
        key = (it.get("tag", ""), primary_flag(it.get("auto_flags", {})))
        buckets[key].append(it)

    rng = random.Random(seed)
    picked = []
    for key, group in sorted(buckets.items()):
        rng.shuffle(group)
        picked.extend(group[:k_per_stratum])
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--k", type=int, default=8,
        help="số mẫu mỗi tầng (tag × cờ chính). "
             "Mặc định 8 ≈ 200 mẫu tổng (4 prec × 2 model × 7 cờ × 8).",
    )
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument(
        "--max-total", type=int, default=250,
        help="chặn trần: nếu vượt thì downsample ngẫu nhiên xuống mức này",
    )
    args = ap.parse_args()

    items = load_all_queues()
    picked = stratify(items, args.k, args.seed)

    if len(picked) > args.max_total:
        rng = random.Random(args.seed)
        rng.shuffle(picked)
        picked = picked[: args.max_total]
        log(f"cắt xuống {args.max_total} mẫu để giữ trong ngân sách gán nhãn")

    # Thống kê phân bố
    dist: dict[tuple, int] = defaultdict(int)
    for it in picked:
        dist[(it.get("tag", ""), primary_flag(it.get("auto_flags", {})))] += 1

    log(f"=== phân bố sub-sample ({len(picked)} mẫu) ===")
    for key in sorted(dist):
        log(f"  {key[0]:<36} {key[1]:<6} n={dist[key]}")

    with OUT.open("w", encoding="utf-8") as f:
        for it in picked:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    log(f"đã ghi {OUT.relative_to(ROOT)}")

    save_json(
        {
            "total": len(picked),
            "per_stratum": {f"{k[0]}|{k[1]}": v for k, v in dist.items()},
            "k_per_stratum": args.k,
            "seed": args.seed,
        },
        "results/tables/queue_sampled_stats.json",
    )
    append_runlog({"step": "07a_sample", "n": len(picked), "k": args.k})

    log("")
    log("BƯỚC TIẾP: A và B chạy ĐỘC LẬP, KHÔNG xem nhãn của nhau:")
    log(f"  PYTHONPATH=src python3 scripts/07_annotate_cli.py --who A --queue {OUT.relative_to(ROOT)} --hide-auto")
    log(f"  PYTHONPATH=src python3 scripts/07_annotate_cli.py --who B --queue {OUT.relative_to(ROOT)} --hide-auto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
