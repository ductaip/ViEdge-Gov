#!/usr/bin/env python3
"""Bóc kho văn bản pháp luật -> điều/khoản/điểm + dựng index trích dẫn."""
from pathlib import Path
from _common import ROOT, load_yaml, log, save_json, append_runlog
from viedge.data import corpus as CO

def main() -> int:
    cfg = load_yaml("configs/retrieval.yaml")
    all_articles = []
    missing = []
    for doc in cfg["corpus"]:
        p = ROOT / doc["path"]
        if not p.exists():
            missing.append(doc["path"]); continue
        arts = CO.parse_document(p.read_text(encoding="utf-8"), doc["id"])
        log(f"{doc['id']}: {len(arts)} điều")
        all_articles.extend(arts)
    if missing:
        log(f"THIẾU {len(missing)} file: {missing}")
        log("   -> tải văn bản vào data/raw/ trước (xem docs/DATA_SOURCES.md)")
    if not all_articles:
        return 1
    out = ROOT / "data" / "processed" / "articles.jsonl"
    CO.save_articles(all_articles, out)
    stats = CO.corpus_stats([a.to_dict() for a in all_articles])
    stats["corpus_snapshot_date"] = cfg.get("corpus_snapshot_date")
    save_json(stats, "results/tables/corpus_stats.json")
    log(f"=> Bảng 1 của quyển: {stats}")
    if not stats["corpus_snapshot_date"] or "__" in str(stats["corpus_snapshot_date"]):
        log("CẢNH BÁO: chưa điền corpus_snapshot_date trong configs/retrieval.yaml")
    append_runlog({"step": "03_build_corpus", **stats})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
