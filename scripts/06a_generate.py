#!/usr/bin/env python3
"""
Sinh tự do trên MỌI biến thể đã xuất trong models/{tag}/ -> đầu vào cho RQ2.

Khác scripts/05: 05 đo trắc nghiệm (nhiệt độ 0). Ở đây sinh MỞ với nhiệt độ >0
để KÍCH lỗi tiếng Việt — chính là hiện tượng ta muốn đo trong RQ2.

Đầu ra: results/taxonomy/generations/{tag}.jsonl
  Mỗi dòng: {"id": "...", "prompt": "...", "output": "..."}

Backend: vLLM (GPU, offline batching). GGUF chạy riêng bằng llama-cpp — script
này sẽ BỎ QUA gguf_* và cảnh báo.
"""
from __future__ import annotations
import json, argparse
from pathlib import Path
from _common import ROOT, log, append_runlog, dry_run

PROBES = ROOT / "data" / "processed" / "probes_vi.jsonl"
OUT_DIR = ROOT / "results" / "taxonomy" / "generations"

SAMPLING = dict(temperature=0.7, top_p=0.9, seed=20260825, max_tokens=512)


def load_probes() -> list[dict]:
    if not PROBES.exists():
        raise SystemExit(f"thiếu {PROBES.relative_to(ROOT)} — soạn bộ probe >=150 câu trước")
    rows = [json.loads(l) for l in PROBES.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        if "id" not in r or "prompt" not in r:
            raise SystemExit(f"probe hỏng schema: {r}")
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit("probe có id trùng — sửa trước khi sinh")
    return rows


def discover_variants(models_dir: Path) -> list[Path]:
    if not models_dir.exists():
        raise SystemExit(f"chưa có {models_dir.relative_to(ROOT)} — chạy scripts/04 trước")
    return sorted(p for p in models_dir.glob("*@*") if p.is_dir())


def generate_vllm(model_path: Path, prompts: list[str]) -> list[str]:
    """Sinh bằng vLLM. Nạp 1 model 1 lần rồi chạy hết batch."""
    from vllm import LLM, SamplingParams

    tag = model_path.name
    dtype = "auto"
    quantization = None
    if "@int4_awq" in tag:
        quantization = "awq_marlin"
    elif "@int8" in tag:
        quantization = "compressed-tensors"
    elif "@fp8" in tag:
        quantization = "fp8"

    log(f"  nạp model {tag} (dtype={dtype}, quant={quantization})")
    llm = LLM(
        model=str(model_path),
        dtype=dtype,
        quantization=quantization,
        max_model_len=4096,
        gpu_memory_utilization=0.85,
        seed=SAMPLING["seed"],
    )
    sp = SamplingParams(
        temperature=SAMPLING["temperature"],
        top_p=SAMPLING["top_p"],
        max_tokens=SAMPLING["max_tokens"],
        seed=SAMPLING["seed"],
    )
    outs = llm.generate(prompts, sp)
    return [o.outputs[0].text for o in outs]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models-dir", default=str(ROOT / "models"))
    ap.add_argument("--only", default="", help="chỉ chạy tag cụ thể (vd. qwen2.5-1.5b-it@bf16)")
    ap.add_argument("--skip-existing", action="store_true", help="bỏ qua tag đã có file output")
    args = ap.parse_args()

    probes = load_probes()
    log(f"nạp {len(probes)} probe từ {PROBES.relative_to(ROOT)}")

    variants = discover_variants(Path(args.models_dir))
    if args.only:
        variants = [v for v in variants if v.name == args.only]
    if not variants:
        raise SystemExit("không có biến thể nào để chạy")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompts = [p["prompt"] for p in probes]
    ids = [p["id"] for p in probes]

    skipped_gguf = []
    for v in variants:
        tag = v.name
        outfile = OUT_DIR / f"{tag}.jsonl"

        if "gguf" in tag.lower():
            skipped_gguf.append(tag)
            continue

        if args.skip_existing and outfile.exists():
            log(f"BỎ QUA {tag}: {outfile.name} đã có (--skip-existing)")
            continue

        if dry_run():
            log(f"[dry] sẽ sinh {len(prompts)} outputs cho {tag} -> {outfile.name}")
            continue

        log(f"=== {tag} — sinh {len(prompts)} outputs ===")
        try:
            texts = generate_vllm(v, prompts)
        except Exception as e:
            log(f"LỖI khi sinh {tag}: {e}")
            append_runlog({"step": "06a_generate", "tag": tag, "error": str(e)})
            continue

        with outfile.open("w", encoding="utf-8") as f:
            for probe, text in zip(probes, texts):
                f.write(json.dumps(
                    {"id": probe["id"], "prompt": probe["prompt"], "output": text},
                    ensure_ascii=False,
                ) + "\n")

        log(f"đã ghi {outfile.relative_to(ROOT)} ({len(texts)} dòng)")
        append_runlog({
            "step": "06a_generate", "tag": tag, "n": len(texts),
            "sampling": SAMPLING,
        })

    if skipped_gguf:
        log(f"⚠️  BỎ QUA {len(skipped_gguf)} biến thể GGUF: {skipped_gguf}")
        log("   GGUF phải chạy bằng llama-cpp-python (viết script riêng)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
