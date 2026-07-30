#!/usr/bin/env python3
"""Chạy lm-eval trên mọi biến thể đã xuất, rồi dựng bảng suy giảm (RQ1)."""
from pathlib import Path
from _common import ROOT, dry_run, log, save_json, append_runlog
from viedge.eval.runner import EvalJob, run, collect_results, degradation_table

def main() -> int:
    models_dir = ROOT / "models"
    variants = sorted(p for p in models_dir.glob("*@*") if p.is_dir()) if models_dir.exists() else []
    if not variants:
        log("chưa có model nào trong models/ — chạy scripts/04 trước"); return 1
    for v in variants:
        job = EvalJob(model_tag=v.name, model_path=str(v), tasks=["vmlu_sampled"],
                      out_dir=ROOT / "results" / "eval")
        code = run(job, dry_run=dry_run())
        append_runlog({"step": "05_eval", "tag": v.name, "rc": code, "dry": dry_run()})
    rows = collect_results(ROOT / "results" / "eval")
    if rows:
        save_json(rows, "results/tables/eval_raw.json")
        table = degradation_table(rows)
        save_json(table, "results/tables/degradation_rq1.json")
        log("=== BẢNG RQ1: suy giảm so với BF16 ===")
        for r in table:
            log(f"  {r['model']:<18} {r['precision']:<12} "
                f"{r.get('acc,none','-')}  Δ={r.get('delta_abs','-')} ({r.get('delta_rel_pct','-')}%)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
