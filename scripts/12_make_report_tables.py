#!/usr/bin/env python3
"""
Gom mọi kết quả thành bảng Markdown dán trực tiếp vào quyển báo cáo.

Chạy script này TRƯỚC KHI viết mỗi chương. Đừng chép số bằng tay từ terminal —
đó là nguồn sai số thường gặp nhất và hội đồng phát hiện được khi số trong
bảng không khớp số trong phần thảo luận.
"""
import json
from pathlib import Path
from _common import ROOT, log

T = ROOT / "results" / "tables"

def read(name: str):
    p = T / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def md_table(rows: list[dict], cols: list[str], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "—")) for c in cols) + " |")
    return "\n".join(out)

def main() -> int:
    parts: list[str] = ["# Bảng số cho quyển báo cáo ViEdge-Gov\n",
                        "> Tự sinh bởi scripts/12. KHÔNG sửa tay — sửa dữ liệu nguồn rồi chạy lại.\n"]

    st = read("corpus_stats.json")
    if st:
        parts += ["\n## Bảng 1. Mô tả kho văn bản\n",
                  md_table([st], list(st), list(st)), ""]

    sp = read("vmlu_sampling_report.json")
    if sp:
        parts += ["\n## Bảng 2. Lấy mẫu VMLU\n",
                  f"- Tổng thể: {sp['n_population']} câu; mẫu: {sp['n_sample']} câu; seed {sp['seed']}",
                  f"- Phủ môn: {sp['coverage']['n_subjects_sample']}/{sp['coverage']['n_subjects_population']}, "
                  f"lệch tỉ lệ tối đa {sp['coverage']['max_share_deviation']}",
                  f"- Sai số lấy mẫu (95%): ±{sp['sampling_error']['margin_of_error_pct']}%", ""]

    dg = read("degradation_rq1.json")
    if dg:
        parts += ["\n## Bảng 3 (RQ1). Suy giảm chất lượng theo mức nén\n",
                  md_table(dg, ["model", "precision", "acc,none", "delta_abs", "delta_rel_pct"],
                           ["Mô hình", "Mức nén", "Accuracy", "Δ tuyệt đối", "Δ tương đối (%)"]),
                  "\n*Mốc tham chiếu: bf16. Δ âm = suy giảm.*", ""]

    ag = read("agreement_per_label.json")
    if ag:
        parts += ["\n## Bảng 4 (RQ2). Đồng thuận gán nhãn theo mã lỗi\n",
                  md_table(ag, ["code", "label", "n", "prevalence", "percent_agreement", "ac1", "cohen_kappa", "interpret"],
                           ["Mã", "Loại lỗi", "n", "Prev.", "Đồng thuận thô", "AC1", "Kappa", "Diễn giải"]),
                  "\n*AC1 (Gwet) là chỉ số chính vì prevalence lệch mạnh làm kappa sụp giả tạo.*", ""]

    cal = read("detector_calibration.json")
    if cal:
        parts += ["\n## Bảng 5. Hiệu chuẩn detector tự động so với nhãn người\n",
                  md_table(cal, ["code", "precision", "recall", "tp", "fp", "fn"],
                           ["Mã", "Precision", "Recall", "TP", "FP", "FN"]), ""]

    rr = read("retrieval_rq3.json")
    if rr:
        parts += ["\n## Bảng 6 (RQ3). Truy hồi trên ViGovQA-GT\n",
                  md_table(rr, ["variant", "n", "precision", "recall", "f2", "avg_k"],
                           ["Cấu hình", "n", "P", "R", "F2", "k̄"]),
                  "\n*F2 thiên về recall: thiếu một điều luật làm câu trả lời sai, thừa chỉ tốn ngữ cảnh.*", ""]

    bench = sorted((ROOT / "results" / "bench").glob("*.json"))
    if bench:
        rows = [json.loads(p.read_text(encoding="utf-8")) for p in bench]
        parts += ["\n## Bảng 7 (RQ4). Hiệu năng trên máy CPU mục tiêu\n",
                  md_table(rows, ["tag", "ttft_ms_median", "ttft_ms_p95", "tpot_ms_median",
                                  "tokens_per_s_median", "peak_rss_mb", "model_disk_mb"],
                           ["Cấu hình", "TTFT p50 (ms)", "TTFT p95 (ms)", "TPOT (ms)",
                            "tok/s", "RAM đỉnh (MB)", "Đĩa (MB)"])]
        h = rows[0].get("host", {})
        parts += [f"\n*Máy đo: {h.get('system','?')}, {h.get('processor') or h.get('machine','?')}, "
                  f"{h.get('n_cpu_logical','?')} core logic, {h.get('ram_total_gb','?')} GB RAM.*", ""]

    missing = [n for n in ("corpus_stats.json", "vmlu_sampling_report.json", "degradation_rq1.json",
                           "agreement_per_label.json", "retrieval_rq3.json") if not (T / n).exists()]
    if missing:
        parts += ["\n## ⚠️ Còn thiếu\n"] + [f"- `{m}`" for m in missing]

    out = T / "REPORT_TABLES.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    log(f"đã sinh {out.relative_to(ROOT)}")
    if missing:
        log(f"còn thiếu {len(missing)} bảng: {missing}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
