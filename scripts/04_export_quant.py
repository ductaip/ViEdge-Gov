#!/usr/bin/env python3
"""Xuất mô hình theo từng mức nén. DRY=1 để chỉ in lệnh (dùng để review trước khi đốt GPU)."""
import os
from pathlib import Path
import os

from _common import ROOT, load_yaml, dry_run, log, append_runlog
from viedge.quant.export import ExportSpec, run

def preflight(precisions: list[str]) -> list[str]:
    """Loại các mức nén KHÔNG chạy được trên máy này, trước khi tốn giờ tải model.

    Hai lý do loại, đều im lặng nếu không kiểm:
      - thiếu thư viện  -> script con báo lỗi rồi bỏ qua, cuối cùng thiếu bảng
      - GPU không đủ SM -> FP8 rơi về W8A16, ta đo nhầm sơ đồ khác (ADR-011)
    """
    import importlib.util, shutil
    out, skip = [], []
    try:
        import torch
        sm = (lambda c: c[0] * 10 + c[1])(torch.cuda.get_device_capability(0)) \
            if torch.cuda.is_available() else 0
    except Exception:
        sm = 0
    has_llmc = importlib.util.find_spec("llmcompressor") is not None
    has_cmake = shutil.which("cmake") is not None
    has_spm = importlib.util.find_spec("sentencepiece") is not None

    for p in precisions:
        if p.startswith("fp8") and sm and sm < 89:
            skip.append((p, f"GPU SM {sm//10}.{sm%10} < 8.9 — FP8 sẽ âm thầm rơi về W8A16, ĐANG ĐO THỨ KHÁC"))
        elif p in ("fp8", "int8", "int4_awq") and not has_llmc:
            skip.append((p, "thiếu llmcompressor (pip install llmcompressor)"))
        elif p.startswith("gguf") and not has_cmake:
            skip.append((p, "thiếu cmake (sudo apt-get install -y cmake)"))
        elif p.startswith("gguf") and not has_spm:
            skip.append((p, "thiếu sentencepiece (pip install sentencepiece protobuf) "
                            "— convert sẽ đổ ở bước dựng vocab sau vài phút"))
        else:
            out.append(p)
    for p, why in skip:
        log(f"BỎ QUA {p}: {why}")
    if skip:
        log("Chạy `python scripts/00e_doctor.py` để xem đầy đủ.")
    return out


def main() -> int:
    cfg = load_yaml("configs/experiments.yaml")
    # configs/experiments.yaml chỉ còn ĐÚNG HAI model, đều là P0 (ADR-018/019).
    # Vẫn lọc theo `priority` để nếu sau này thêm model phụ thì không xuất nhầm.
    models = [m for m in cfg["models"] if m.get("priority", "P0") == "P0"]
    if not models:
        log("configs/experiments.yaml không có model P0 nào"); return 1
    # VIEDGE_PRECISIONS cho phép chạy MỘT bậc riêng lẻ mà không sửa config —
    # cần khi chạy trên máy khác (Modal L4 chạy được FP8, local thì không).
    override = os.environ.get("VIEDGE_PRECISIONS", "").strip()
    wanted = [x.strip() for x in override.split(",") if x.strip()] if override else None
    if wanted:
        known = set(cfg["precisions"]) | set(cfg.get("optional_precisions") or [])
        bad = [w for w in wanted if w not in known]
        if bad:
            log(f"precision không có trong config: {bad}"); return 1
        log(f"ghi đè bậc nén theo VIEDGE_PRECISIONS: {wanted}")
    precisions = preflight(wanted or cfg["precisions"])
    if not precisions:
        log("Không mức nén nào chạy được — sửa môi trường trước."); return 1
    log(f"{len(models)} model x {len(precisions)} precision = {len(models)*len(precisions)} lượt xuất")
    rc = 0
    for m in models:
        # bf16 PHẢI xong trước: GGUF convert cần THƯ MỤC MODEL LOCAL, không nhận
        # được HF repo id. Chạy sai thứ tự -> "is not a directory".
        ordered = sorted(precisions, key=lambda x: (x != "bf16", x))
        bf16_dir = ROOT / "models" / f"{m['tag']}@bf16"
        for p in ordered:
            out = ROOT / "models" / f"{m['tag']}@{p}"
            if out.exists() and any(out.iterdir()):
                log(f"bỏ qua (đã có): {out.name}"); continue
            source = m["hf_id"]
            if p.startswith("gguf"):
                if not (bf16_dir.exists() and any(bf16_dir.iterdir())):
                    log(f"BỎ QUA {out.name}: cần {bf16_dir.name} trước (GGUF convert đọc thư mục local)")
                    continue
                source = str(bf16_dir)
            spec = ExportSpec(model_id=source, precision=p, out_dir=out,
                              calib_dataset=cfg["calibration"]["dataset"],
                              calib_samples=cfg["calibration"]["n_samples"],
                              max_seq_len=cfg["calibration"]["max_seq_len"])
            code = run(spec, dry_run=dry_run())
            if code == 0 and not dry_run():
                # Ghi dấu vết máy: bậc nào chạy ở đâu. Cần cho Bảng 3 (ADR-020).
                from viedge.provenance import write as write_prov
                write_prov(out, {"stage": "export", "precision": p, "model_tag": m["tag"]})
            append_runlog({"step": "04_export", "tag": f"{m['tag']}@{p}",
                           "rc": code, "dry": dry_run()})
            rc = rc or code
    return rc

if __name__ == "__main__":
    raise SystemExit(main())
