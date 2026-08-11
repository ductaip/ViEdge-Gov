#!/usr/bin/env python3
"""Chạy lm-eval trên mọi biến thể đã xuất, rồi dựng bảng suy giảm (RQ1)."""
from pathlib import Path
from _common import ROOT, dry_run, load_yaml, log, save_json, append_runlog
from viedge.eval.runner import (EvalJob, run, collect_results, degradation_table,
                                paired_significance)
from viedge.eval.significance import at_floor

def main() -> int:
    cfg = load_yaml("configs/experiments.yaml")
    ev = cfg.get("evaluation", {}) or {}
    batch = str(ev.get("batch_size", "4"))
    max_len = ev.get("max_length")
    models_dir = ROOT / "models"
    variants = sorted(p for p in models_dir.glob("*@*") if p.is_dir()) if models_dir.exists() else []
    if not variants:
        log("chưa có model nào trong models/ — chạy scripts/04 trước"); return 1
    for v in variants:
        margs = f"pretrained={v},trust_remote_code=True"
        if max_len:
            margs += f",max_length={max_len}"
        job = EvalJob(model_tag=v.name, model_path=str(v), tasks=["vmlu_sampled"],
                      batch_size=batch, out_dir=ROOT / "results" / "eval",
                      extra_args=["--include_path", str(ROOT / "configs" / "lm_eval_tasks")])
        job.model_args_override = margs
        code = run(job, dry_run=dry_run())
        if code == 0 and not dry_run():
            from viedge.provenance import write as write_prov
            write_prov(ROOT / "results" / "eval" / v.name, {"stage": "eval", "tag": v.name})
        append_runlog({"step": "05_eval", "tag": v.name, "rc": code, "dry": dry_run()})
    # CẢNH BÁO TRỘN MÁY — phải xử lý TRƯỚC khi tin vào bảng (ADR-020)
    from viedge.provenance import check_consistency
    mixed = check_consistency(ROOT / "results" / "eval")
    if mixed:
        log("")
        log("⚠️  CÁC BẬC CỦA CÙNG MỘT MODEL CHẠY TRÊN MÁY KHÁC NHAU:")
        for m in mixed:
            log(f"   {m['model']}: {', '.join(m['machines'])}")
            for prec, mk in sorted(m["by_precision"].items()):
                log(f"      {prec:<14} {mk}")
        log("   Chênh lệch do phần cứng (kernel, thứ tự cộng float, phiên bản thư")
        log("   viện) có thể lẫn vào Δ đang đo. Hoặc chạy lại toàn thang trên MỘT máy,")
        log("   hoặc ghi rõ trong Bảng 3 và phần Thực nghiệm. Xem ADR-020.")

    rows = collect_results(ROOT / "results" / "eval")
    if rows:
        save_json(rows, "results/tables/eval_raw.json")
        table = degradation_table(rows)
        save_json(table, "results/tables/degradation_rq1.json")
        log("=== BẢNG RQ1: suy giảm so với BF16 ===")
        for r in table:
            log(f"  {r['model']:<18} {r['precision']:<12} "
                f"{r.get('acc,none','-')}  Δ={r.get('delta_abs','-')} ({r.get('delta_rel_pct','-')}%)")

        # Kiểm SÀN: biến thể nào đã tụt về mức đoán mò thì DỪNG diễn giải (ADR-018)
        baseline = (cfg.get("eval_sets", {}).get("vmlu_sampled", {})
                    .get("random_baseline", 0.25))
        n_eval = 0
        sp = ROOT / "data" / "processed" / "vmlu_sampled.jsonl"
        if sp.exists():
            n_eval = sum(1 for l in sp.read_text(encoding="utf-8").splitlines() if l.strip())
        if n_eval:
            floors = []
            for r in table:
                acc = r.get("acc,none")
                if acc is None:
                    continue
                f = at_floor(float(acc), n_eval, float(baseline))
                floors.append({"model": r["model"], "precision": r["precision"],
                               "acc": acc, "baseline": baseline, "z": round(f.z, 3),
                               "p_value": round(f.p_value, 6),
                               "at_floor": f.at_floor, "note": f.note})
            save_json(floors, "results/tables/floor_check.json")
            hit = [f for f in floors if f["at_floor"]]
            if hit:
                log("")
                log(f"🔴 {len(hit)} biến thể ĐÃ CHẠM SÀN (không phân biệt được với đoán mò "
                    f"{baseline:.4f}, n={n_eval}):")
                for f in hit:
                    log(f"   {f['model']}@{f['precision']}  acc={f['acc']}  p={f['p_value']}")
                log("   -> Ghi nhận là MẤT NĂNG LỰC. KHÔNG diễn giải mức tụt tiếp theo,")
                log("      và KHÔNG vẽ đường cong xuống dưới điểm này.")

        # Kiểm định BẮT CẶP — chỉ số chính của Bảng 3 (ADR-013)
        models = sorted({str(r["model_tag"]).split("@")[0] for r in rows})
        sig = []
        for m in models:
            sig.extend(paired_significance(ROOT / "results" / "eval", m))
        if sig:
            save_json(sig, "results/tables/significance_rq1.json")
            log("")
            log("=== KIỂM ĐỊNH BẮT CẶP (McNemar) — chỉ số CHÍNH của Bảng 3 ===")
            for r in sig:
                if "note" in r:
                    log(f"  {r['model']:<18} {r['precision']:<12} {r['note']}"); continue
                log(f"  {r['model']:<18} {r['precision']:<12} "
                    f"Δ={r['delta']:+.1%} CI[{r['ci95_low']:+.1%},{r['ci95_high']:+.1%}] "
                    f"↓{r['flip_down']} ↑{r['flip_up']} p={r['p_value']:.4g} "
                    f"{'✅ có ý nghĩa' if r['significant'] else '— không có ý nghĩa'}")
        else:
            log("chưa có dữ liệu từng câu -> không kiểm định bắt cặp được.")
            log("   Kiểm lm-eval có chạy với --log_samples không.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
