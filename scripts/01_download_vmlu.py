#!/usr/bin/env python3
"""Tải VMLU. Nguồn chính: HF `anhdungitvn/vmlu_v1.5`; dự phòng: repo ZaloAI-Jaist/VMLU."""
from _common import ROOT, log, append_runlog

def main() -> int:
    out = ROOT / "data" / "raw" / "vmlu_full.jsonl"
    if out.exists():
        log(f"đã có {out.name}, bỏ qua"); return 0
    try:
        from datasets import load_dataset
    except ImportError:
        log("Chưa có `datasets`. Chạy: pip install datasets"); return 1
    log("tải anhdungitvn/vmlu_v1.5 ...")
    ds = load_dataset("anhdungitvn/vmlu_v1.5")
    split = "test" if "test" in ds else list(ds.keys())[0]
    rows = list(ds[split])
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"lưu {len(rows)} câu -> {out}")
    log(f"các cột: {list(rows[0].keys()) if rows else '(rỗng)'}")
    append_runlog({"step": "01_download_vmlu", "n_rows": len(rows), "split": split})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
