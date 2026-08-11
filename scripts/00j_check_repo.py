#!/usr/bin/env python3
"""
Kiểm toàn vẹn repo TRƯỚC khi gửi job lên Modal (hoặc trước khi chạy dài ở local).

VÌ SAO CẦN:
Repo này được xây bằng cách chép từng file. Thiếu một file thì lỗi chỉ lộ ra khi
script chạy tới dòng `import` — mà trên Modal thì đó là SAU KHI đã build image,
cấp GPU và tính tiền. Ví dụ thật: thiếu `src/viedge/eval/significance.py`, job
eval chạy tới `05_run_eval.py` dòng 7 rồi mới đổ.

Script này import mọi module lõi và kiểm mọi file bắt buộc — mất 2 giây, chặn
được cả lớp lỗi đó.

    python scripts/00j_check_repo.py
    make check
"""
from __future__ import annotations
import importlib
import sys
from _common import ROOT, log

# Module phải import được. Thiếu bất kỳ cái nào là pipeline đứt ở giữa.
MODULES = [
    "viedge.vitext",
    "viedge.env",
    "viedge.provenance",
    "viedge.data.vmlu",
    "viedge.data.corpus",
    "viedge.data.vigovqa",
    "viedge.data.amendments",
    "viedge.data.desegment",
    "viedge.quant.export",
    "viedge.eval.runner",
    "viedge.eval.significance",         # McNemar + kiểm sàn (ADR-013, 018)
    "viedge.eval.reference_agreement",  # flip rate trên tập không đáp án (ADR-016)
    "viedge.taxonomy.detectors",
    "viedge.taxonomy.agreement",
    "viedge.rag.citations",
    "viedge.rag.retrieval",
    "viedge.rag.pipeline",
    "viedge.bench.latency",
]

# Hàm/thuộc tính cụ thể — bắt được trường hợp file CÓ nhưng là BẢN CŨ.
SYMBOLS = {
    "viedge.data.vmlu": ["subject_of", "random_baseline", "choice_count_stats"],
    "viedge.eval.significance": ["mcnemar", "at_floor", "floor_accuracy", "headroom_report"],
    "viedge.eval.reference_agreement": ["flip_rate", "validate_proxy", "expected_harmful_share"],
    "viedge.eval.runner": ["paired_significance", "load_per_sample"],
    "viedge.data.corpus": ["build_retrieval_units", "article_of"],
    "viedge.data.amendments": ["parse_amending_document", "AmendmentIndex", "augment_context"],
    "viedge.provenance": ["collect", "check_consistency", "machine_key"],
    "viedge.env": ["hf_token", "child_env", "mask"],
    "viedge.rag.pipeline": ["Assistant", "SYSTEM_PROMPT"],
}

FILES = [
    "configs/experiments.yaml",
    "configs/retrieval.yaml",
    "configs/lm_eval_tasks/vmlu_sampled.yaml",
    "configs/lm_eval_tasks/utils.py",
    "scripts/_common.py",
    "scripts/_compress.py",
    "scripts/_hf_snapshot.py",
    "scripts/_to_gguf.sh",
    "scripts/04_export_quant.py",
    "scripts/05_run_eval.py",
    "modal_app.py",
]

# File dữ liệu — thiếu thì job chạy được nhưng ra kết quả rỗng.
DATA = [
    ("data/raw/vmlu/dev.jsonl", "VMLU dev — chạy `make sample`"),
    ("data/raw/vmlu/valid.jsonl", "VMLU valid"),
    ("data/processed/calib_vi.jsonl", "bộ calib tiếng Việt — `python scripts/02c_build_calib.py`"),
]


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    bad_mod, bad_sym, bad_file, warn_data = [], [], [], []

    for name in MODULES:
        try:
            mod = importlib.import_module(name)
        except Exception as e:
            bad_mod.append((name, f"{type(e).__name__}: {str(e)[:60]}"))
            continue
        for sym in SYMBOLS.get(name, []):
            if not hasattr(mod, sym):
                bad_sym.append((name, sym))

    for f in FILES:
        if not (ROOT / f).exists():
            bad_file.append(f)

    for f, hint in DATA:
        if not (ROOT / f).exists():
            warn_data.append((f, hint))

    if bad_mod:
        log(f"❌ {len(bad_mod)} module KHÔNG import được:")
        for n, e in bad_mod:
            path = "src/" + n.replace(".", "/") + ".py"
            log(f"   {n}\n      {e}\n      -> thiếu hoặc lỗi: {path}")
    if bad_sym:
        log(f"❌ {len(bad_sym)} module là BẢN CŨ (import được nhưng thiếu hàm):")
        for n, s in bad_sym:
            log(f"   {n}.{s}()  -> chép lại src/{n.replace('.', '/')}.py")
    if bad_file:
        log(f"❌ {len(bad_file)} file bắt buộc không có:")
        for f in bad_file:
            log(f"   {f}")
    if warn_data:
        log(f"⚠️  {len(warn_data)} file dữ liệu chưa có (job sẽ chạy nhưng ra rỗng):")
        for f, hint in warn_data:
            log(f"   {f}  — {hint}")

    if bad_mod or bad_sym or bad_file:
        log("")
        log("DỪNG LẠI — sửa trước khi gửi job lên Modal.")
        log("Trên Modal, lỗi này chỉ lộ ra SAU KHI đã build image và tính tiền GPU.")
        return 1

    log(f"✅ {len(MODULES)} module + {len(FILES)} file bắt buộc: đầy đủ và đúng phiên bản")
    if warn_data:
        log("   (còn thiếu dữ liệu — xem cảnh báo ở trên)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
