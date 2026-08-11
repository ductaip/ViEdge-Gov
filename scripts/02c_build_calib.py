#!/usr/bin/env python3
"""
Dựng bộ calibration TIẾNG VIỆT cho quantization.

VÌ SAO ĐÂY LÀ VIỆC CHẶN ĐƯỜNG: không có calib thì không chạy được W8A8/W4A16,
không có mô hình nén thì không có Bảng 3 (RQ1), không có RQ1 thì không có đề tài.
Và calib KHÔNG cần corpus đầy đủ — chỉ cần văn bản tiếng Việt.

QUY TẮC (ADR-007): calib phải là tiếng Việt. Dùng C4/WikiText tiếng Anh sẽ chọn
scale theo phân bố activation tiếng Anh, tức là tự tay tạo ra chính hiện tượng
suy giảm mà đề tài đang đo -> hỏng tính hợp lệ nội tại của thí nghiệm.

TRỘN HAI NGUỒN, có chủ ý:
  - văn bản pháp luật (miền đích) — để scale phù hợp với thứ mô hình sẽ gặp
  - văn xuôi tiếng Việt thường — để calib không lệch hoàn toàn về văn phong
    pháp lý; nếu chỉ có văn bản luật, mô hình nén xong có thể tệ đi rõ rệt
    trên câu hỏi đời thường, và ta sẽ đo nhầm hiệu ứng đó thành "suy giảm do nén"

Dùng:
    python scripts/02c_build_calib.py                     # từ data/raw/*.txt
    python scripts/02c_build_calib.py --add-wiki 200      # thêm wiki tiếng Việt
"""
from __future__ import annotations
import argparse, json, random, re
from pathlib import Path
from _common import ROOT, load_yaml, log, save_json, append_runlog, rel
from viedge import vitext
from viedge.data.desegment import glue_ratio

MIN_CHARS, MAX_CHARS = 200, 4000


def chunks_from_text(text: str, doc_id: str) -> list[dict]:
    """Cắt theo điều nếu có; nếu không thì theo đoạn. Mỗi mẩu là một mẫu calib."""
    parts = re.split(r"(?m)^(?=\s*Điều\s+\d+)", text)
    if len(parts) < 3:
        parts = re.split(r"\n\s*\n", text)
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) < MIN_CHARS:
            continue
        # cắt mẩu quá dài, giữ ranh giới câu
        while len(p) > MAX_CHARS:
            cut = p.rfind(". ", MIN_CHARS, MAX_CHARS)
            cut = cut + 1 if cut > 0 else MAX_CHARS
            out.append({"text": p[:cut].strip(), "source": doc_id})
            p = p[cut:].strip()
        if len(p) >= MIN_CHARS:
            out.append({"text": p, "source": doc_id})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=256, help="số mẫu calib")
    ap.add_argument("--legal-ratio", type=float, default=0.7,
                    help="tỉ lệ mẫu từ văn bản pháp luật (còn lại là văn xuôi thường)")
    ap.add_argument("--add-wiki", type=int, default=0,
                    help="tải N đoạn wikipedia tiếng Việt làm nguồn văn xuôi thường")
    ap.add_argument("--seed", type=int, default=20260825)
    args = ap.parse_args()

    legal: list[dict] = []
    for f in sorted((ROOT / "data" / "raw").glob("*.txt")):
        t = f.read_text(encoding="utf-8", errors="replace")
        gr = glue_ratio(t)
        if gr >= 0.25:
            log(f"BỎ QUA {f.name}: dính chữ (glue={gr:.3f}) — calib bằng text hỏng"); continue
        c = chunks_from_text(t, f.stem)
        legal.extend(c)
        log(f"{f.name}: {len(c)} mẩu (glue={gr:.3f})")

    if not legal:
        log("Không có văn bản nào trong data/raw/*.txt"); return 1

    general: list[dict] = []
    if args.add_wiki:
        try:
            from datasets import load_dataset
            log(f"tải {args.add_wiki} đoạn wikipedia tiếng Việt ...")
            ds = load_dataset("wikimedia/wikipedia", "20231101.vi", split=f"train[:{args.add_wiki*2}]")
            for r in ds:
                general.extend(chunks_from_text(r["text"][:6000], "wiki_vi"))
                if len(general) >= args.add_wiki:
                    break
            general = general[: args.add_wiki]
            log(f"wiki: {len(general)} mẩu")
        except Exception as e:
            log(f"không tải được wiki ({type(e).__name__}) — tiếp tục chỉ với văn bản pháp luật")

    rng = random.Random(args.seed)
    rng.shuffle(legal); rng.shuffle(general)

    n_legal = args.n if not general else min(len(legal), int(args.n * args.legal_ratio))
    n_gen = min(len(general), args.n - n_legal)
    samples = legal[:n_legal] + general[:n_gen]
    rng.shuffle(samples)

    if len(samples) < args.n:
        log(f"CHỈ CÓ {len(samples)}/{args.n} mẫu — vẫn chạy được nhưng calib yếu hơn.")
        log("   Thêm văn bản vào data/raw/ hoặc dùng --add-wiki.")

    out = ROOT / "data" / "processed" / "calib_vi.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps({"text": s["text"]}, ensure_ascii=False) + "\n")

    from collections import Counter
    src = Counter(s["source"] for s in samples)
    lens = sorted(len(s["text"]) for s in samples)
    ratios = [vitext.diacritic_ratio(s["text"]) for s in samples]
    stats = {
        "n_samples": len(samples), "seed": args.seed,
        "by_source": dict(src),
        "chars_median": lens[len(lens) // 2], "chars_max": lens[-1],
        "diacritic_ratio_mean": round(sum(ratios) / len(ratios), 4),
        "language": "vi",
        "note": "ADR-007: calib PHẢI tiếng Việt, không dùng C4/WikiText tiếng Anh",
    }
    save_json(stats, "results/tables/calib_stats.json")
    log(f"đã ghi {rel(out)}: {len(samples)} mẫu, median {stats['chars_median']} ký tự")
    log(f"   nguồn: {dict(src)}")
    log(f"   tỉ lệ dấu trung bình {stats['diacritic_ratio_mean']} (văn bản VN sạch thường 0.18-0.35)")
    if stats["diacritic_ratio_mean"] < 0.15:
        log("   CẢNH BÁO: tỉ lệ dấu thấp bất thường — kiểm text nguồn có mất dấu không")
    append_runlog({"step": "02c_build_calib", **{k: v for k, v in stats.items() if k != "note"}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
