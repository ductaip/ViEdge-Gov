#!/usr/bin/env python3
"""
In schema thật của file VMLU đã tải + thử render 2 mẫu qua hàm doc_to_*.

CHẠY CÁI NÀY TRƯỚC `make eval`. Nếu prompt render sai mà cứ chạy, ta đốt vài
giờ GPU để ra một bảng số vô nghĩa — và tệ hơn, không biết là nó vô nghĩa.
"""
import json, sys
from pathlib import Path
from _common import ROOT, log

sys.path.insert(0, str(ROOT / "configs" / "lm_eval_tasks"))
import utils  # noqa: E402

def main() -> int:
    for name in ("data/processed/vmlu_sampled.jsonl", "data/raw/vmlu_full.jsonl"):
        p = ROOT / name
        if p.exists():
            break
    else:
        log("chưa có file VMLU nào — chạy scripts/01 rồi scripts/02"); return 1

    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()[:200] if l.strip()]
    log(f"file: {p.relative_to(ROOT)} ({len(rows)} mẫu đầu)")
    log(f"các cột: {sorted(rows[0])}")

    for i, doc in enumerate(rows[:2]):
        print("\n" + "=" * 70)
        try:
            print(utils.doc_to_text(doc))
            print(f"--> choices : {utils.doc_to_choice(doc)}")
            print(f"--> target  : index {utils.doc_to_target(doc)} "
                  f"= {utils.doc_to_choice(doc)[utils.doc_to_target(doc)]}")
        except Exception as e:
            print(f"LỖI render mẫu {i}: {type(e).__name__}: {e}")
            print("raw:", json.dumps(doc, ensure_ascii=False)[:400])
            print("=> Sửa configs/lm_eval_tasks/utils.py cho khớp schema trên.")
            return 1

    bad = 0
    for doc in rows:
        try:
            utils.doc_to_target(doc)
        except Exception:
            bad += 1
    print("\n" + "=" * 70)
    log(f"{len(rows)-bad}/{len(rows)} mẫu đọc được đáp án")
    if bad:
        log("CÓ mẫu hỏng — xử lý trong utils.process_docs trước khi chạy eval")
        return 1
    log("schema OK, có thể chạy `make eval`")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())