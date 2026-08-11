#!/usr/bin/env python3
"""
Đối chiếu các mirror VMLU và quyết định dùng nguồn nào — BẰNG BẰNG CHỨNG.

VẤN ĐỀ. VMLU chính thức giữ kín đáp án split test (9.833 câu) cho leaderboard.
Nhưng trên HF có mirror công bố đủ 10.880 dòng. Chỉ có ba khả năng:
  (a) mirror chép từ bản gốc CÓ đáp án ở thời điểm nào đó
  (b) mirror có cột đáp án nhưng RỖNG ở phần test
  (c) đáp án phần test do bên thứ ba tự suy/tự sinh -> KHÔNG đáng tin

Nếu là (c) mà ta dùng, mọi con số accuracy trong Bảng 3 đều dựa trên đáp án sai,
và **không so được với bất kỳ công trình nào** dùng VMLU chính thức. Hội đồng
hỏi "số của em so được với leaderboard VMLU không?" thì không trả lời được.

CÁCH PHÂN BIỆT (a) với (c) — kiểm chéo phần CÓ ĐÁP ÁN CHÍNH THỨC:
Lấy các câu xuất hiện ở CẢ hai nguồn trong phần validation (đáp án chính thức,
công khai). Nếu mirror khớp ~100% trên phần này, nó chép từ bản gốc -> phần test
nhiều khả năng cũng thật. Nếu lệch đáng kể -> đáp án là tự sinh, LOẠI.

Đây là phép kiểm rẻ (vài phút) cho một quyết định ảnh hưởng toàn bộ Bảng 3.

    python scripts/01b_verify_vmlu_source.py
    python scripts/01b_verify_vmlu_source.py --repos tridm/VMLU danganhdat/vmlu-v1-5
"""
from __future__ import annotations
import argparse, hashlib, re, unicodedata
from collections import Counter
from _common import ROOT, log, save_json

DEFAULT_REPOS = ["tridm/VMLU", "danganhdat/vmlu-v1-5"]
ANSWER_KEYS = ("answer", "answer_key", "label", "gold", "correct")
QUESTION_KEYS = ("question", "text", "query")


def norm_q(row: dict) -> str | None:
    """Khoá đối chiếu: chuẩn hoá câu hỏi rồi băm. Chịu được khác biệt khoảng trắng."""
    for k in QUESTION_KEYS:
        if row.get(k):
            q = unicodedata.normalize("NFC", str(row[k]))
            q = re.sub(r"\s+", " ", q).strip().lower()
            return hashlib.sha1(q.encode()).hexdigest()[:16] if q else None
    return None


def answer_of(row: dict) -> str | None:
    for k in ANSWER_KEYS:
        v = row.get(k)
        if v is not None and str(v).strip() not in ("", "None", "nan", "-1"):
            return str(v).strip().upper()[:1]
    return None


def load(repo: str):
    from datasets import load_dataset
    return load_dataset(repo)


def profile(repo: str) -> dict | None:
    try:
        ds = load(repo)
    except Exception as e:
        log(f"{repo}: KHÔNG tải được — {type(e).__name__}: {str(e)[:70]}")
        return None
    info = {"repo": repo, "splits": {}, "rows": {}}
    for split in ds.keys():
        rows = list(ds[split])
        n_ans = sum(1 for r in rows if answer_of(r))
        info["splits"][split] = {"n": len(rows), "n_answer": n_ans}
        info["rows"][split] = rows
        log(f"  {repo:<26} {split:<12} {len(rows):>6} câu | đáp án {n_ans:>6} "
            f"{'✅' if n_ans == len(rows) else '❌ RỖNG' if n_ans == 0 else '⚠️ MỘT PHẦN'}")
    info["columns"] = sorted(next(iter(ds.values()))[0].keys())
    return info


def answer_balance(rows: list[dict]) -> dict:
    """Phân bố đáp án A/B/C/D. Bộ đề thật thường khá đều; lệch nặng là dấu hiệu
    đáp án được suy đoán hoặc sinh máy."""
    c = Counter(a for r in rows if (a := answer_of(r)))
    tot = sum(c.values()) or 1
    return {k: round(v / tot, 3) for k, v in sorted(c.items())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*", default=DEFAULT_REPOS)
    args = ap.parse_args()

    log("Tải và lập hồ sơ từng nguồn ...")
    profs = [p for r in args.repos if (p := profile(r))]
    if not profs:
        log("Không nguồn nào tải được."); return 1

    # Gom mọi câu CÓ đáp án của từng nguồn, theo khoá băm câu hỏi
    ans_map: dict[str, dict[str, str]] = {}
    for p in profs:
        m = {}
        for split, rows in p["rows"].items():
            for r in rows:
                k, a = norm_q(r), answer_of(r)
                if k and a:
                    m[k] = a
        ans_map[p["repo"]] = m
        log(f"{p['repo']}: {len(m)} câu có đáp án (đã khử trùng theo nội dung câu hỏi)")
        log(f"   phân bố đáp án: {answer_balance([r for rs in p['rows'].values() for r in rs])}")

    report = {"profiles": [{k: v for k, v in p.items() if k != "rows"} for p in profs],
              "cross_checks": []}

    if len(profs) >= 2:
        log("\n=== KIỂM CHÉO ĐÁP ÁN TRÊN PHẦN GIAO NHAU ===")
        for i in range(len(profs)):
            for j in range(i + 1, len(profs)):
                ra, rb = profs[i]["repo"], profs[j]["repo"]
                A, B = ans_map[ra], ans_map[rb]
                common = set(A) & set(B)
                if not common:
                    log(f"{ra} ↔ {rb}: KHÔNG có câu chung — không kết luận được"); continue
                agree = sum(1 for k in common if A[k] == B[k])
                rate = agree / len(common)
                verdict = ("✅ KHỚP — mirror chép từ bản gốc, đáng tin"
                           if rate >= 0.99 else
                           "⚠️ LỆCH NHẸ — kiểm tay vài ca trước khi dùng"
                           if rate >= 0.95 else
                           "❌ LỆCH NẶNG — ít nhất một nguồn có đáp án tự sinh, KHÔNG DÙNG")
                log(f"{ra} ↔ {rb}: {len(common)} câu chung, khớp {agree} ({rate:.1%}) → {verdict}")
                report["cross_checks"].append(
                    {"a": ra, "b": rb, "n_common": len(common),
                     "n_agree": agree, "rate": round(rate, 4), "verdict": verdict})

    save_json(report, "results/tables/vmlu_source_verification.json")
    log("\n=== KHUYẾN NGHỊ ===")
    best = max(profs, key=lambda p: sum(s["n_answer"] for s in p["splits"].values()))
    n_best = sum(s["n_answer"] for s in best["splits"].values())
    log(f"Nguồn nhiều câu chấm được nhất: {best['repo']} ({n_best} câu)")
    log("Chốt theo NGUYÊN TẮC: chỉ dùng nguồn có đáp án đã kiểm chéo khớp >= 99%.")
    log("Nếu không kiểm chéo được, dùng phần validation chính thức và ghi rõ cỡ mẫu.")
    log("Bảng này đưa vào PHỤ LỤC — nó chứng minh nguồn dữ liệu đã được thẩm định.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
