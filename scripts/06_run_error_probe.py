#!/usr/bin/env python3
"""
Sinh tự do + chạy detector -> tạo hàng đợi gán nhãn cho RQ2 (TÍNH MỚI của đề tài).

Đây là script quan trọng nhất về mặt điểm số. Đầu ra:
  results/taxonomy/signals_<tag>.jsonl    - tín hiệu tự động toàn bộ
  results/taxonomy/queue_<tag>.jsonl      - mẫu cần người xem
Nhớ: detector chỉ TRIAGE. Nhãn dùng trong kết luận là nhãn người.
"""
import json
from pathlib import Path
from _common import ROOT, log, append_runlog
from viedge import vitext as V
from viedge.data import corpus as CO
from viedge.rag import citations as C
from viedge.taxonomy import detectors as D

PROBE_FILE = ROOT / "data" / "processed" / "probes_vi.jsonl"

def load_probes() -> list[dict]:
    if PROBE_FILE.exists():
        return [json.loads(l) for l in PROBE_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Bộ probe tối thiểu. MỞ RỘNG lên >=150 prompt trong Tuần 2.
    return [
        {"id": "p001", "prompt": "Giải thích ý nghĩa của biển báo cấm đỗ xe theo quy chuẩn hiện hành."},
        {"id": "p002", "prompt": "Nêu trình tự thủ tục cấp đổi giấy phép lái xe hạng B."},
        {"id": "p003", "prompt": "Tóm tắt các trường hợp bị tước quyền sử dụng giấy phép lái xe."},
        {"id": "p004", "prompt": "Viết đoạn 300 từ giải thích quyền và nghĩa vụ của người điều khiển phương tiện."},
    ]

def main() -> int:
    arts = []
    ap = ROOT / "data" / "processed" / "articles.jsonl"
    if ap.exists():
        arts = CO.load_articles(ap)
    lex = V.VietLexicon.from_texts([a["text"] for a in arts]) if arts else None
    idx = C.CitationIndex.from_articles(arts) if arts else C.CitationIndex.empty()
    if lex is None:
        log("CẢNH BÁO: chưa có corpus -> detector E2 sẽ yếu. Chạy scripts/03 trước.")

    gen_dir = ROOT / "results" / "taxonomy" / "generations"
    files = sorted(gen_dir.glob("*.jsonl")) if gen_dir.exists() else []
    if not files:
        log(f"chưa có sinh tự do trong {gen_dir.relative_to(ROOT)}/")
        log("   Định dạng cần: mỗi dòng {\"id\":..., \"prompt\":..., \"output\":...}")
        log(f"   Có {len(load_probes())} probe mẫu sẵn — mở rộng lên >=150 trong Tuần 2.")
        return 1

    ref_ratio: dict[str, float] = {}
    for f in files:  # nạp tỉ lệ dấu của BF16 làm tham chiếu tương đối
        if "@bf16" in f.stem:
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    ref_ratio[r["id"]] = V.diacritic_ratio(r.get("output", ""))

    for f in files:
        tag = f.stem
        rows, queue = [], []
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            sig = D.compute_signals(rec.get("output", ""), lexicon=lex, index=idx,
                                    finish_reason=rec.get("finish_reason"))
            fl = D.flags(sig, reference_diacritic_ratio=ref_ratio.get(rec["id"]))
            row = {"id": rec["id"], "tag": tag, "flags": fl, "signals": sig.to_dict()}
            rows.append(row)
            if D.needs_human_review(sig, fl):
                queue.append({"id": rec["id"], "tag": tag, "prompt": rec.get("prompt", ""),
                              "output": rec.get("output", ""), "auto_flags": fl})
        outdir = ROOT / "results" / "taxonomy"
        (outdir / f"signals_{tag}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        (outdir / f"queue_{tag}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in queue), encoding="utf-8")
        rate = {k: round(100*sum(1 for r in rows if r["flags"][k])/len(rows), 1) for k in D.E_LABELS} if rows else {}
        log(f"{tag}: {len(rows)} mẫu, {len(queue)} cần người xem | tỉ lệ cờ %: {rate}")
        append_runlog({"step": "06_probe", "tag": tag, "n": len(rows), "queue": len(queue), "flag_rate_pct": rate})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
