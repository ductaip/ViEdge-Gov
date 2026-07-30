#!/usr/bin/env python3
"""Lấy mẫu phân tầng VMLU + xuất báo cáo phủ mẫu và sai số (cho phụ lục)."""
import json
from _common import ROOT, load_yaml, log, save_json, append_runlog
from viedge.data import vmlu

def main() -> int:
    cfg = load_yaml("configs/experiments.yaml")
    spec = cfg["eval_sets"]["vmlu_sampled"]
    src = ROOT / "data" / "raw" / "vmlu_full.jsonl"
    if not src.exists():
        log("chưa có data/raw/vmlu_full.jsonl — chạy scripts/01 trước"); return 1
    rows = vmlu.load_jsonl(src)
    n, seed = spec["n_sample"], cfg["seed"]
    key = spec.get("stratify_by") or vmlu.detect_subject_key(rows)
    sample = vmlu.stratified_sample(rows, n, subject_key=key, seed=seed,
                                    min_per_stratum=spec.get("min_per_stratum", 5))
    out = ROOT / "data" / "processed" / "vmlu_sampled.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in sample:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    report = {
        "seed": seed, "n_population": len(rows), "n_sample": len(sample),
        "stratify_by": key,
        "coverage": vmlu.coverage_report(sample, rows, key),
        "sampling_error": vmlu.sampling_error_note(len(sample), len(rows)),
    }
    save_json(report, "results/tables/vmlu_sampling_report.json")
    log(f"mẫu {len(sample)}/{len(rows)}; MoE ±{report['sampling_error']['margin_of_error_pct']}%")
    log("=> Copy báo cáo này vào PHỤ LỤC quyển. Hội đồng sẽ hỏi vì sao không chạy hết.")
    append_runlog({"step": "02_sample_vmlu", "n_sample": len(sample), "seed": seed})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
