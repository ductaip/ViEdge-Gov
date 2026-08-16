#!/usr/bin/env python3
"""
Chấm VMLU trên GGUF bằng llama-cpp-python — đọc logits trực tiếp (KHÔNG qua
llama-server, KHÔNG qua kỹ thuật echo+logprobs của lm-eval).

LỊCH SỬ 2 LẦN THỬ TRƯỚC, ĐỀU KHÔNG DÙNG ĐƯỢC:

1. `lm_eval --model gguf` + llama-server: `GGUFLM` viết cho schema logprobs CŨ
   của OpenAI Completions API (đọc lại logprob của MỌI token trong prompt khi
   echo=True). `llama-server` bản mới (build từ llama.cpp hiện tại) CHỈ trả
   logprob của token vừa sinh, không echo lại token prompt — đã kiểm bằng tay,
   0/1 token cho mọi trường hợp. Kỹ thuật GGUFLM dựa vào không còn dữ liệu.

2. `llama_cpp.Llama.create_completion(echo=True, logprobs=K)` — tầng Python
   (không qua HTTP) THÌ ĐÚNG, đã kiểm bằng tay ra số hợp lý. Nhưng cách gọi lại
   toàn bộ context+lựa_chọn cho MỖI lựa chọn (4 lượt/câu) quá chậm trên CPU —
   30 câu chạy > 20 phút không xong.

CÁCH DÙNG Ở ĐÂY (giống hệt phương pháp scripts/00g_screen_models.py chấm HF,
để hai backend so sánh công bằng): VMLU luôn có lựa chọn là MỘT CHỮ CÁI
(" A".." E", xem configs/lm_eval_tasks/utils.py::doc_to_choice). Một chữ cái
gần như luôn là MỘT token. Nên chỉ cần:
  1. Xử lý CONTEXT một lần (llm.eval)
  2. Đọc logits ở vị trí CUỐI (llm.eval_logits[-1])
  3. So logit của token-đầu-tiên từng lựa chọn, chọn lớn nhất
Không cần gọi lại model cho từng lựa chọn -> nhanh hơn cách echo nhiều lần.

Có fallback CHẬM (đúng kỹ thuật của lần thử 2 — echo+cộng logprob) cho câu
hiếm gặp mà lựa chọn không phải một token, để không bỏ sót câu nào.

RAM đã kiểm ổn định qua nhiều lượt gọi (llm.reset() dọn sạch trước mỗi câu,
không rò rỉ) — xem log kiểm tra trong lịch sử phát triển script này.

Output ghi ĐÚNG định dạng mà viedge.eval.runner.collect_results/load_per_sample
đọc (results_*.json + samples_*.jsonl), để `make eval` gộp bậc GGUF vào Bảng 3
tự động — không cần code riêng ở tầng báo cáo.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _common import ROOT, dry_run, log, append_runlog

sys.path.insert(0, str(ROOT / "configs" / "lm_eval_tasks"))


def load_docs(n: int | None = None) -> list[dict]:
    p = ROOT / "data" / "processed" / "vmlu_sampled.jsonl"
    if not p.exists():
        log("chưa có data/processed/vmlu_sampled.jsonl — chạy `make sample` trước")
        return []
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows[:n] if n else rows


def choice_token_ids(llm, choices: list[str]) -> list[int] | None:
    """id token ĐẦU TIÊN của từng lựa chọn. None nếu có lựa chọn > 1 token
    hoặc hai lựa chọn trùng token đầu (không phân biệt được bằng cách nhanh)."""
    ids = []
    for ch in choices:
        toks = llm.tokenize(ch.encode("utf-8"), add_bos=False)
        if len(toks) != 1:
            return None
        ids.append(toks[0])
    return ids if len(set(ids)) == len(ids) else None


def score_fast(llm, ctx: str, choices: list[str]) -> int | None:
    """Một lượt eval context, đọc logits. None nếu không dùng được cách nhanh."""
    cids = choice_token_ids(llm, choices)
    if cids is None:
        return None
    llm.reset()
    tokens = llm.tokenize(ctx.encode("utf-8"), add_bos=True)
    llm.eval(tokens)
    logits = llm.eval_logits[-1]
    scores = [logits[c] for c in cids]
    return max(range(len(scores)), key=lambda i: scores[i])


def score_slow(llm, ctx: str, choices: list[str]) -> int:
    """Fallback: echo + cộng logprob continuation (đúng kỹ thuật lần thử 2).
    Dùng khi lựa chọn không phải một token — hiếm với VMLU."""
    scores = []
    for ch in choices:
        full = ctx + ch
        out = llm.create_completion(full, max_tokens=1, logprobs=1,
                                    echo=True, temperature=0.0)
        lp = out["choices"][0]["logprobs"]
        offsets, tok_lps = lp["text_offset"], lp["token_logprobs"]
        start = next((i for i, o in enumerate(offsets) if o >= len(ctx)), len(offsets))
        cont = [v for v in tok_lps[start:] if v is not None]
        scores.append(sum(cont) if cont else float("-inf"))
    return max(range(len(scores)), key=lambda i: scores[i])


def run_model(tag: str, gguf_path: Path, n_ctx: int, threads: int | None,
              docs: list[dict], out_dir: Path, dry: bool) -> int:
    log(f"=== {tag} ({gguf_path.name}, {gguf_path.stat().st_size / 1e9:.2f} GB) ===")
    if dry:
        log(f"[dry] sẽ chấm {len(docs)} câu bằng {gguf_path}")
        return 0

    import utils  # configs/lm_eval_tasks/utils.py — cùng prompt với backend HF
    from llama_cpp import Llama

    t0 = time.time()
    llm = Llama(model_path=str(gguf_path), n_ctx=n_ctx, verbose=False,
               logits_all=True, n_threads=threads)
    log(f"nạp model: {time.time() - t0:.1f}s")

    n_correct = 0
    n_slow = 0
    samples = []
    t_start = time.time()
    for i, doc in enumerate(docs):
        ctx = utils.doc_to_text(doc)
        choices = utils.doc_to_choice(doc)
        gold = utils.doc_to_target(doc)

        pred = score_fast(llm, ctx, choices)
        if pred is None:
            pred = score_slow(llm, ctx, choices)
            n_slow += 1

        ok = pred == gold
        n_correct += int(ok)
        samples.append({"doc_id": doc.get("id", i), "acc": ok,
                        "pred": pred, "gold": gold})
        if (i + 1) % 50 == 0 or i + 1 == len(docs):
            elapsed = time.time() - t_start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(docs) - i - 1) / rate if rate > 0 else float("inf")
            log(f"  {i + 1}/{len(docs)}  acc={n_correct / (i + 1):.4f}  "
                f"{rate:.2f} câu/s  ETA {eta / 60:.1f} phút  (slow-path: {n_slow})")

    acc = n_correct / len(docs) if docs else 0.0
    log(f"XONG {tag}: accuracy = {acc:.4f} ({n_correct}/{len(docs)}), "
        f"slow-path dùng cho {n_slow} câu")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    results_doc = {
        "results": {"vmlu_sampled": {"acc,none": acc, "acc_stderr,none": None}},
        "config": {"model": "gguf", "model_args": f"path={gguf_path}", "n_ctx": n_ctx},
    }
    (out_dir / f"results_{ts}.json").write_text(
        json.dumps(results_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / f"samples_vmlu_sampled_{ts}.jsonl").open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    from viedge.provenance import write as write_prov
    write_prov(out_dir, {"stage": "eval", "tag": tag, "backend": "llama-cpp-python",
                        "n_ctx": n_ctx, "n_docs": len(docs), "n_slow_path": n_slow})
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qtype", default="q4_k_m")
    ap.add_argument("--n-ctx", type=int, default=2048)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None, help="chấm ít câu hơn để test nhanh")
    ap.add_argument("--tags", nargs="*", default=None,
                    help="chỉ chạy các tag này, vd. --tags qwen2.5-1.5b-it")
    args = ap.parse_args()

    docs = load_docs(args.limit)
    if not docs:
        return 1
    log(f"chấm {len(docs)} câu VMLU")

    models_dir = ROOT / "models"
    variants = sorted(p for p in models_dir.glob(f"*@gguf_{args.qtype}") if p.is_dir())
    if args.tags:
        variants = [v for v in variants if v.name.split("@")[0] in args.tags]
    if not variants:
        log(f"không có thư mục nào dạng *@gguf_{args.qtype} trong models/"); return 1

    rc_all = 0
    for v in variants:
        tag = v.name
        cand = v / f"model-{args.qtype.lower()}.gguf"
        if not cand.exists():
            hits = sorted(v.glob(f"*{args.qtype.lower()}*.gguf"))
            cand = hits[0] if hits else None
        if cand is None:
            log(f"BỎ QUA {tag}: chưa có model-{args.qtype}.gguf — quantize trước bằng llama-quantize")
            rc_all = 1
            continue
        rc = run_model(tag, cand, args.n_ctx, args.threads, docs,
                       ROOT / "results" / "eval" / tag, dry_run())
        append_runlog({"step": "05b_eval_gguf", "tag": tag, "rc": rc,
                       "n_docs": len(docs), "dry": dry_run()})
        rc_all = rc_all or rc

    if rc_all == 0 and not dry_run():
        log("")
        log("Xong. Chạy `make eval` lại để gộp bậc GGUF vào Bảng 3 — "
            "collect_results() quét mọi thư mục results/eval/*.")
    return rc_all


if __name__ == "__main__":
    raise SystemExit(main())
