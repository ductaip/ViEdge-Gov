#!/usr/bin/env python3
"""
Đánh giá truy hồi trên ViGovQA-GT: precision/recall/F2, có/không dense,
top-k động vs top-k cố định. Sinh bảng cho RQ3.
"""
import json, pickle, statistics
from _common import ROOT, load_yaml, log, save_json, append_runlog
from viedge.data import vigovqa as Q
from viedge.rag import retrieval as R

def mean(xs): return round(statistics.mean(xs), 4) if xs else 0.0

def main() -> int:
    cfg = load_yaml("configs/retrieval.yaml")
    qp = ROOT / "data" / "vigovqa" / "vigovqa_gt.jsonl"
    if not qp.exists():
        qp = ROOT / "data" / "fixtures" / "vigovqa_seed.jsonl"
        log(f"dùng fixture ({qp.name}) — thay bằng bộ thật khi có")
    items = Q.load(qp)
    bad = {it["id"]: Q.validate(it) for it in items}
    bad = {k: v for k, v in bad.items() if v}
    if bad:
        log(f"CÓ {len(bad)} mẫu không hợp lệ, ví dụ: {list(bad.items())[:2]}"); return 1

    # CỬA KIỂM TRA BẮT BUỘC: gold unit_id phải tồn tại trong index.
    # Lỗi hay gặp nhất của cả pipeline là lệch tên văn bản giữa
    # configs/retrieval.yaml và trường `doc` trong citations — khi đó mọi
    # điểm F2 bằng 0 mà không có thông báo lỗi nào. Đừng bỏ qua cửa này.
    upath = ROOT / "data" / "processed" / "units.json"
    if upath.exists():
        known = set(json.loads(upath.read_text(encoding="utf-8")))
        gold_all = {f"{c['doc']}::dieu-{c['dieu']}" for it in items for c in it["citations"]}
        miss = sorted(gold_all - known)
        cov = 100 * (1 - len(miss) / len(gold_all)) if gold_all else 0
        log(f"phủ gold trong index: {cov:.1f}% ({len(gold_all)-len(miss)}/{len(gold_all)})")
        if miss:
            log("LỖI: các gold unit sau KHÔNG có trong index:")
            for m in miss[:5]:
                log(f"   - {m}")
            log("   Nguyên nhân gần như chắc chắn: `id` văn bản trong")
            log("   configs/retrieval.yaml khác trường `doc` trong citations.")
            log(f"   id đang có trong index: {sorted({k.split('::')[0] for k in known})}")
            if cov == 0:
                log("   => Dừng: không có gold nào khớp, mọi điểm sẽ bằng 0.")
                return 1

    bpath = ROOT / "data" / "processed" / "bm25.pkl"
    if not bpath.exists():
        log("chưa có bm25.pkl — chạy scripts/09 trước"); return 1
    with bpath.open("rb") as f:
        bm = pickle.load(f)
    dense = None
    dpath = ROOT / "data" / "processed" / "dense.pkl"
    if dpath.exists():
        log("(dense có sẵn nhưng cần encoder lúc truy vấn — bỏ qua ở chế độ chỉ-BM25)")

    fus, dyn = cfg["retriever"]["fusion"], cfg["retriever"]["dynamic_top_k"]
    variants = {
        "bm25_top5_fixed":  dict(max_k=5, min_k=5, drop_ratio=0.0),
        "bm25_top10_fixed": dict(max_k=10, min_k=10, drop_ratio=0.0),
        "bm25_dynamic":     dict(max_k=dyn["max_k"], min_k=dyn["min_k"], drop_ratio=dyn["drop_ratio"]),
    }
    table = []
    for name, kw in variants.items():
        ret = R.HybridRetriever(bm25=bm, dense=dense, rrf_k=fus["rrf_k"],
                                bm25_weight=fus["bm25_weight"], dense_weight=fus["dense_weight"],
                                pool=fus["pool"], **kw)
        P, Rc, F, K = [], [], [], []
        for it in items:
            gold = sorted({f"{c['doc']}::dieu-{c['dieu']}" for c in it["citations"]})
            got = [d for d, _ in ret.retrieve(it["question"])]
            m = R.prf(got, gold, beta=2.0)
            P.append(m["precision"]); Rc.append(m["recall"]); F.append(m["f2"]); K.append(len(got))
        row = {"variant": name, "n": len(items), "precision": mean(P), "recall": mean(Rc),
               "f2": mean(F), "avg_k": mean(K)}
        table.append(row)
        log(f"  {name:<20} P={row['precision']:.3f} R={row['recall']:.3f} F2={row['f2']:.3f} k̄={row['avg_k']}")
    save_json(table, "results/tables/retrieval_rq3.json")
    log("=> Luận điểm cần chứng minh: top-k động cho F2 cao hơn top-k cố định")
    log("   ở mức k trung bình THẤP HƠN. Nếu không đúng, nói thẳng trong báo cáo.")
    append_runlog({"step": "10_eval_rag", "table": table})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
