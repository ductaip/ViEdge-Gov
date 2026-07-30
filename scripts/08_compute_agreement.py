#!/usr/bin/env python3
"""
Tính AC1/kappa từng mã lỗi + hiệu chuẩn detector so với nhãn người.

Xuất hai bảng cho quyển:
  - agreement_per_label.json : độ tin cậy của quy trình gán nhãn
  - detector_calibration.json: precision/recall của detector tự động
Bảng thứ hai là phần kiểm định công cụ — thiếu nó thì mọi số tự động bị hỏi.
"""
import json
from collections import defaultdict
from pathlib import Path
from _common import ROOT, log, save_json
from viedge.taxonomy import agreement as A
from viedge.taxonomy.detectors import E_LABELS

def load_labels(who: str) -> dict[str, dict[str, bool]]:
    out: dict[str, dict[str, bool]] = {}
    for f in (ROOT / "results" / "taxonomy").glob(f"labels_*_{who}.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[f"{r.get('tag','')}|{r['id']}"] = r["labels"]
    return out

def main() -> int:
    a, b = load_labels("A"), load_labels("B")
    if not a or not b:
        log("thiếu nhãn của A hoặc B — chạy scripts/07 cho cả hai người"); return 1
    common = sorted(set(a) & set(b))
    log(f"A={len(a)}  B={len(b)}  trùng={len(common)}")
    if len(common) < 30:
        log("CẢNH BÁO: dưới 30 mẫu trùng, AC1 sẽ có CI rất rộng. Cần >=50.")

    res = A.per_label_binary(a, b, list(E_LABELS), n_boot=2000)
    table = []
    for code, r in res.items():
        prev = sum(1 for k in common if a[k].get(code) or b[k].get(code)) / len(common)
        table.append({"code": code, "label": E_LABELS[code], "n": r.n_items,
                      "prevalence": round(prev, 3),
                      "percent_agreement": round(r.percent_agreement, 3),
                      "ac1": round(r.ac1, 3), "ac1_ci": [round(x, 3) for x in (r.ac1_ci or (0, 0))],
                      "cohen_kappa": round(r.cohen_kappa, 3),
                      "interpret": A.interpret(r.ac1)})
    save_json(table, "results/tables/agreement_per_label.json")
    log("=== BẢNG ĐỒNG THUẬN THEO MÃ LỖI ===")
    for r in table:
        log(f"  {r['code']}  prev={r['prevalence']:.3f}  AC1={r['ac1']:.3f} {r['ac1_ci']}  "
            f"kappa={r['cohen_kappa']:.3f}  ({r['interpret']})")
    log("Lưu ý viết báo cáo: chỗ nào AC1 >> kappa thì giải thích bằng nghịch lý")
    log("prevalence lệch — hội đồng SẼ hỏi vì sao hai chỉ số chênh nhau.")

    # Hiệu chuẩn detector: gộp nhãn người (union A,B) làm ground truth mềm
    sig_files = list((ROOT / "results" / "taxonomy").glob("signals_*.jsonl"))
    if sig_files:
        auto: dict[str, dict[str, bool]] = {}
        for f in sig_files:
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    auto[f"{r['tag']}|{r['id']}"] = r["flags"]
        calib = []
        for code in E_LABELS:
            tp = fp = fn = 0
            for k in common:
                human = a[k].get(code) or b[k].get(code)
                machine = auto.get(k, {}).get(code, False)
                tp += int(human and machine); fp += int(machine and not human); fn += int(human and not machine)
            prec = tp / (tp + fp) if tp + fp else None
            rec = tp / (tp + fn) if tp + fn else None
            calib.append({"code": code, "tp": tp, "fp": fp, "fn": fn,
                          "precision": round(prec, 3) if prec is not None else None,
                          "recall": round(rec, 3) if rec is not None else None})
        save_json(calib, "results/tables/detector_calibration.json")
        log("=== HIỆU CHUẨN DETECTOR ===")
        for r in calib:
            log(f"  {r['code']}  P={r['precision']}  R={r['recall']}  (tp={r['tp']} fp={r['fp']} fn={r['fn']})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
