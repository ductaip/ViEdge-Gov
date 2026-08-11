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
    # scripts/01 đã lọc bỏ câu không có đáp án (split test của VMLU). Nếu số câu
    # chấm được ÍT HƠN chỉ tiêu lấy mẫu thì dùng HẾT — lấy mẫu thêm là vô nghĩa.
    if len(rows) <= n:
        log(f"chỉ có {len(rows)} câu chấm được (< chỉ tiêu {n}) -> DÙNG HẾT, không lấy mẫu")
        n = len(rows)
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
    moe = report["sampling_error"]["margin_of_error_pct"]
    if len(sample) >= len(rows):
        # Hiệu chỉnh mẫu hữu hạn cho MoE = 0 khi lấy TOÀN BỘ tổng thể. Đúng về
        # toán, nhưng "±0.0%" dễ bị đọc nhầm thành "không có sai số nào".
        log(f"dùng TOÀN BỘ {len(rows)} câu chấm được -> không còn sai số LẤY MẪU")
        log("   (±0.0% ở đây KHÔNG có nghĩa là kết quả không có sai số: vẫn còn")
        log("    sai số do chính bộ đề, do mô hình, và do quy trình chấm.)")
    else:
        log(f"mẫu {len(sample)}/{len(rows)}; MoE độc lập ±{moe}%")
    log("")
    log("⚠️ MoE ở trên là sai số lấy mẫu ĐỘC LẬP — KHÔNG phải chỉ số dùng cho Bảng 3.")
    log("   Ta chấm CÙNG bộ câu hỏi qua mọi bậc nén = thiết kế BẮT CẶP, nên phải")
    log("   dùng McNemar + bootstrap bắt cặp (mạnh hơn nhiều ở cỡ mẫu này).")
    log("   MoE độc lập chỉ đưa vào phụ lục để đối chiếu. Xem ADR-013.")
    log("=> Copy báo cáo này vào PHỤ LỤC quyển.")
    append_runlog({"step": "02_sample_vmlu", "n_sample": len(sample), "seed": seed})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
