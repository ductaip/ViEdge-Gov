#!/usr/bin/env python3
"""Xuất mô hình theo từng mức nén. DRY=1 để chỉ in lệnh (dùng để review trước khi đốt GPU)."""
from pathlib import Path
from _common import ROOT, load_yaml, dry_run, log, append_runlog
from viedge.quant.export import ExportSpec, run

def main() -> int:
    cfg = load_yaml("configs/experiments.yaml")
    models = [m for m in cfg["models"] if m.get("priority", "P0") == "P0"]
    if not models:
        models = cfg["models"][:2]
    precisions = cfg["precisions"]
    log(f"{len(models)} model x {len(precisions)} precision = {len(models)*len(precisions)} lượt xuất")
    rc = 0
    for m in models:
        for p in precisions:
            out = ROOT / "models" / f"{m['tag']}@{p}"
            if out.exists() and any(out.iterdir()):
                log(f"bỏ qua (đã có): {out.name}"); continue
            spec = ExportSpec(model_id=m["hf_id"], precision=p, out_dir=out,
                              calib_dataset=cfg["calibration"]["dataset"],
                              calib_samples=cfg["calibration"]["n_samples"],
                              max_seq_len=cfg["calibration"]["max_seq_len"])
            code = run(spec, dry_run=dry_run())
            append_runlog({"step": "04_export", "tag": f"{m['tag']}@{p}",
                           "rc": code, "dry": dry_run()})
            rc = rc or code
    return rc

if __name__ == "__main__":
    raise SystemExit(main())
