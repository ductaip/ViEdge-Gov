#!/usr/bin/env python3
"""
Tải VMLU và BÁO CÁO split nào thực sự có đáp án.

⚠️ ĐIỀU PHẢI BIẾT VỀ VMLU: bộ này công bố 10.880 câu, nhưng **đáp án của split
test KHÔNG công khai** — nó dành cho leaderboard. Chỉ dev/validation (và train
nếu có) mới chấm được tại chỗ. Các công trình trước cũng đánh giá trên validation
vì lý do này.

Hệ quả: cỡ mẫu chấm được nhỏ hơn 10.880 rất nhiều. Script này đếm cụ thể từng
split và nói thẳng, thay vì để phát hiện muộn lúc accuracy ra 0%.

Repo mặc định thử theo thứ tự; repo đầu tiên tải được sẽ dùng.
"""
import json
from _common import ROOT, log, save_json, append_runlog, rel

# Thứ tự thử. Repo đầu tiên tải được sẽ dùng.
# TRƯỚC KHI ĐỔI THỨ TỰ: chạy scripts/01b_verify_vmlu_source.py để kiểm chéo đáp án.
# Mirror công bố đủ 10.880 dòng chỉ dùng được NẾU đáp án khớp bản chính thức
# trên phần giao nhau — VMLU chính thức giữ kín đáp án split test.
CANDIDATES = [
    "danganhdat/vmlu-v1-5",     # mirror VMLU (ZaloAI x JAIST)
    "tridm/VMLU",               # mirror khác, 10.880 dòng — PHẢI kiểm chéo trước  # repo cũ ghi trong docs, KHÔNG còn tồn tại
]
ANSWER_KEYS = ("answer", "answer_key", "label", "gold")


def has_answer(row: dict) -> bool:
    for k in ANSWER_KEYS:
        v = row.get(k)
        if v is not None and str(v).strip() not in ("", "None", "nan"):
            return True
    return False


def main() -> int:
    out = ROOT / "data" / "raw" / "vmlu_full.jsonl"
    if out.exists():
        log(f"đã có {rel(out)}, bỏ qua (xoá file nếu muốn tải lại)"); return 0
    try:
        from datasets import load_dataset
    except ImportError:
        log("Chưa có `datasets`. Chạy: pip install datasets"); return 1

    ds = None
    used = None
    for repo in CANDIDATES:
        try:
            log(f"thử {repo} ...")
            ds = load_dataset(repo)
            used = repo
            break
        except Exception as e:
            log(f"  không dùng được: {type(e).__name__}: {str(e)[:80]}")
    if ds is None:
        log("KHÔNG tải được VMLU từ repo nào trong danh sách.")
        log("Tìm mirror khác trên HF (từ khoá: vmlu) rồi thêm vào CANDIDATES,")
        log("hoặc tải thủ công từ github.com/ZaloAI-Jaist/VMLU.")
        return 1

    log(f"dùng repo: {used}")
    report = {"repo": used, "splits": {}}
    rows_with_answer, rows_all = [], []
    for split in ds.keys():
        rows = list(ds[split])
        n_ans = sum(1 for r in rows if has_answer(r))
        report["splits"][split] = {"n": len(rows), "n_with_answer": n_ans}
        log(f"  {split:<12} {len(rows):>6} câu | có đáp án: {n_ans:>6}"
            f" {'✅' if n_ans == len(rows) else '⚠️ THIẾU ĐÁP ÁN' if n_ans == 0 else '⚠️ MỘT PHẦN'}")
        for r in rows:
            r = dict(r, _split=split)
            rows_all.append(r)
            if has_answer(r):
                rows_with_answer.append(r)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows_with_answer:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report["n_total"] = len(rows_all)
    report["n_usable"] = len(rows_with_answer)
    report["columns"] = sorted(rows_all[0].keys()) if rows_all else []
    save_json(report, "results/tables/vmlu_source_report.json")

    log(f"lưu {len(rows_with_answer)}/{len(rows_all)} câu CHẤM ĐƯỢC -> {rel(out)}")
    log(f"các cột: {report['columns']}")
    if len(rows_with_answer) < len(rows_all):
        log("")
        log(f"⚠️ {len(rows_all) - len(rows_with_answer)} câu KHÔNG có đáp án công khai (split test).")
        log("   Đây là thiết kế của VMLU: test set dành cho leaderboard.")
        log(f"   Cỡ mẫu thật cho đề tài = {len(rows_with_answer)} câu.")
        log("   Vì cỡ mẫu nhỏ, Bảng 3 PHẢI dùng kiểm định BẮT CẶP (McNemar), không")
        log("   dùng sai số lấy mẫu độc lập — xem docs/DECISIONS.md ADR-013.")
    append_runlog({"step": "01_download_vmlu", "repo": used,
                   "n_total": len(rows_all), "n_usable": len(rows_with_answer)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
