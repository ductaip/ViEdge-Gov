#!/usr/bin/env python3
"""
Chạy TOÀN BỘ pipeline trên dữ liệu fixture, không cần GPU và không cần model.

Mục đích: sau khi clone/giải nén, chạy `make smoke` để biết repo lành mạnh
trước khi đốt giờ GPU. Nếu smoke đỏ thì đừng chạy gì khác.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from viedge import vitext as V
from viedge.data import corpus as CO, vigovqa as Q, vmlu
from viedge.rag import citations as C, retrieval as R
from viedge.rag.pipeline import Assistant
from viedge.taxonomy import detectors as D, agreement as A

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "data" / "fixtures"
ok = lambda m: print(f"  \033[32mOK\033[0m  {m}")

def main() -> int:
    print("\n=== ViEdge-Gov smoke ===\n")

    print("[1/7] Bóc văn bản pháp luật")
    arts = CO.parse_document((FIX / "sample_law.txt").read_text(encoding="utf-8"),
                             "Nghị định 168/2024/NĐ-CP")
    assert len(arts) >= 2, "parser không tách được điều"
    print("      ", CO.corpus_stats([a.to_dict() for a in arts])); ok(f"{len(arts)} điều")

    print("[2/7] Từ vựng tham chiếu + phát hiện mất dấu")
    lex = V.VietLexicon.from_texts([a.text for a in arts])
    bad = V.strip_marks(arts[0].text)
    n = len(lex.tone_loss_tokens(bad))
    assert n > 0 and lex.tone_loss_tokens(arts[0].text) == []
    ok(f"lexicon={len(lex)} dạng, bắt {n} token mất dấu, 0 dương tính giả")

    print("[3/7] Index trích dẫn + phát hiện bịa (E3)")
    idx = C.CitationIndex.from_articles([a.to_dict() for a in arts])
    unk = idx.unknown(C.extract("Theo Điều 4242 Nghị định 999/1999/NĐ-CP thì..."))
    assert len(unk) >= 2; ok(f"bắt {len(unk)} trích dẫn không tồn tại")

    print("[4/7] Detector taxonomy E1-E6")
    cases = {
        "E1": "Ngưá»i Ä'iá»u khiá»n phÆ°Æ¡ng tiá»n",
        "E2": bad,
        "E3": "Căn cứ Điều 4242 Nghị định 999/1999/NĐ-CP.",
        "E5": "The answer is that you should note the following which is based on this.",
        "E6": "Phạt tiền từ 800.000 đồng. " * 30,
    }
    ref = V.diacritic_ratio(arts[0].text)
    for code, text in cases.items():
        fl = D.flags(D.compute_signals(text, lexicon=lex, index=idx), reference_diacritic_ratio=ref)
        assert fl[code], f"{code} không bật trên ca thử"
    clean = D.flags(D.compute_signals(arts[0].text, lexicon=lex, index=idx), reference_diacritic_ratio=ref)
    assert not any(clean[c] for c in ("E1","E2","E3","E5")), f"dương tính giả trên văn bản sạch: {clean}"
    ok("5/5 mã lỗi bật đúng, văn bản sạch không bị gắn cờ")

    print("[5/7] Truy hồi lai + top-k động")
    units = {a.unit_id: a.retrieval_text() for a in arts}
    ret = R.HybridRetriever(bm25=R.BM25().fit(units))
    hits = ret.retrieve("khong mang giay phep lai xe bi phat bao nhieu")
    assert hits, "truy hồi không dấu thất bại"
    ok(f"trả {len(hits)} đơn vị (truy vấn KHÔNG dấu): {[h[0].split('::')[1] for h in hits]}")

    print("[6/7] Trợ lý + cửa chặn trích dẫn")
    asst_ok = Assistant(retriever=ret, index=idx, unit_text=units,
        generator=lambda s,u: f"Theo Điều {arts[0].dieu}, khoản 1, Nghị định 168/2024/NĐ-CP thì có.")
    asst_bad = Assistant(retriever=ret, index=idx, unit_text=units,
        generator=lambda s,u: "Theo Điều 4242 Nghị định 999/1999/NĐ-CP thì không.")
    a1 = asst_ok.answer("Không mang giấy phép lái xe bị phạt bao nhiêu?")
    a2 = asst_bad.answer("Không mang giấy phép lái xe bị phạt bao nhiêu?")
    assert not a1.blocked and a2.blocked
    ok(f"hợp lệ->thông, bịa->chặn ({a2.block_reason})")

    print("[7/7] Lấy mẫu VMLU + đồng thuận + schema ViGovQA")
    pop = [{"id": f"q{i}", "subject": f"mon{i%58}"} for i in range(10880)]
    s = vmlu.stratified_sample(pop, 2000)
    assert len(s) == 2000 and not vmlu.coverage_report(s, pop)["missing_subjects"]
    moe = vmlu.sampling_error_note(2000, 10880)["margin_of_error_pct"]
    r = A.evaluate(["1"]*90+["0"]*10, ["1"]*85+["0"]*15, n_boot=200)
    items = Q.load(FIX / "vigovqa_seed.jsonl")
    errs = {it["id"]: Q.validate(it) for it in items}
    bad_items = {k: v for k, v in errs.items() if v}
    assert not bad_items, bad_items
    ok(f"mẫu 2000/10880 (MoE ±{moe}%), AC1={r.ac1:.3f} > kappa={r.cohen_kappa:.3f}, {len(items)} mẫu seed hợp lệ")

    print("\n\033[32mSMOKE PASSED\033[0m — repo lành mạnh, có thể bắt đầu chạy thật.\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
