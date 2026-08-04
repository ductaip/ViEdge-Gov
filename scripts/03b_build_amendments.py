#!/usr/bin/env python3
"""
Dựng lớp phủ sửa đổi: ánh xạ nghị định sửa đổi -> điều nó sửa trong văn bản gốc.

Chạy SAU scripts/03. Đọc `amendments:` trong configs/retrieval.yaml.
"""
from _common import ROOT, load_yaml, log, save_json, append_runlog
from viedge.data.amendments import parse_amending_document, AmendmentIndex

def main() -> int:
    cfg = load_yaml("configs/retrieval.yaml")
    specs = cfg.get("amendments") or []
    if not specs:
        log("configs/retrieval.yaml chưa khai báo mục `amendments:` — bỏ qua"); return 0

    all_ams = []
    for sp in specs:
        p = ROOT / sp["path"]
        if not p.exists():
            log(f"THIẾU {sp['path']} — bỏ qua {sp['id']}"); continue
        ams = parse_amending_document(
            p.read_text(encoding="utf-8"),
            source_doc=sp["id"], target_doc=sp["amends"],
            effective_date=str(sp.get("hieu_luc", "")),
        )
        log(f"{sp['id']}: {len(ams)} quy định sửa đổi -> {sp['amends']}")
        all_ams.extend(ams)

    if not all_ams:
        log("không bóc được sửa đổi nào"); return 1

    idx = AmendmentIndex.from_amendments(all_ams)
    idx.save(ROOT / "data" / "processed" / "amendments.jsonl")
    st = idx.stats()
    save_json(st, "results/tables/amendments_stats.json")
    log(f"=> {st['n_amendments']} sửa đổi, tác động {st['n_affected_dieu']} điều")
    log(f"   các điều bị sửa: {', '.join(st['affected_dieu'])}")
    log("Kiểm tay 3 điều bất kỳ: quy định sửa đổi có đúng trỏ vào điều đó không?")
    append_runlog({"step": "03b_amendments", **st})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
