#!/usr/bin/env python3
"""Dựng index truy hồi (BM25 + dense tuỳ chọn) và lưu ra đĩa."""
import json, pickle
from _common import ROOT, load_yaml, log, append_runlog
from viedge.data import corpus as CO
from viedge.rag import retrieval as R

def main() -> int:
    cfg = load_yaml("configs/retrieval.yaml")
    ap = ROOT / "data" / "processed" / "articles.jsonl"
    if not ap.exists():
        log("chưa có articles.jsonl — chạy scripts/03 trước"); return 1
    arts = CO.load_articles(ap)
    units = {a["unit_id"]: f"{a['doc_id']} — Điều {a['dieu']}. {a['title']}\n{a['text']}" for a in arts}
    log(f"{len(units)} đơn vị truy hồi")

    bm = R.BM25(**cfg["retriever"]["bm25"]).fit(units)
    outdir = ROOT / "data" / "processed"
    (outdir / "units.json").write_text(json.dumps(units, ensure_ascii=False), encoding="utf-8")
    with (outdir / "bm25.pkl").open("wb") as f:
        pickle.dump(bm, f)
    log("lưu bm25.pkl + units.json")

    dcfg = cfg["retriever"]["dense"]
    if dcfg.get("enabled"):
        try:
            from sentence_transformers import SentenceTransformer
            model_name = dcfg["model"]
            log(f"nạp encoder {model_name} ...")
            st = SentenceTransformer(model_name)
            enc = lambda xs: st.encode(list(xs), batch_size=dcfg.get("batch_size", 32),
                                       normalize_embeddings=False).tolist()
            dense = R.DenseIndex(enc).fit(units)
            with (outdir / "dense.pkl").open("wb") as f:
                pickle.dump({"doc_ids": dense.doc_ids, "vecs": dense.vecs, "model": model_name}, f)
            log(f"lưu dense.pkl ({len(dense.vecs)} vector, dim={len(dense.vecs[0])})")
        except Exception as e:
            log(f"bỏ qua dense: {type(e).__name__}: {e}")
            log(f"   thử fallback: {dcfg.get('fallback')}")
    append_runlog({"step": "09_build_index", "n_units": len(units)})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
