#!/usr/bin/env python3
"""
Sinh tự do trên MỌI biến thể đã xuất trong models/{tag}/ -> đầu vào cho RQ2.

Khác scripts/05: 05 đo trắc nghiệm (nhiệt độ 0). Ở đây sinh MỞ với nhiệt độ >0
để KÍCH lỗi tiếng Việt — chính là hiện tượng ta muốn đo trong RQ2.

Đầu ra: results/taxonomy/generations/{tag}.jsonl
  Mỗi dòng: {"id": "...", "prompt": "...", "output": "..."}

Backend: vLLM (GPU, offline batching). GGUF chạy riêng bằng llama-cpp.
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


def _patch_gemma3_rope(model_path: Path) -> bool:
    """Gemma3 quantized bị thiếu rope_type trong config.json (vLLM 0.19 đòi).
    Patch tạm nếu cần, trả True nếu đã patch."""
    cfg_path = model_path / "config.json"
    if not cfg_path.exists():
        return False
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    rope = cfg.get("rope_scaling") or cfg.get("rope_parameters")
    if rope and isinstance(rope, dict) and "rope_type" not in rope:
        rope["rope_type"] = rope.get("type", "default")
        # Ghi vào key mà vLLM đọc
        cfg["rope_scaling"] = rope
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"  đã patch rope_type vào {cfg_path.name}")
        return True
    return False


def _patch_config_groups_list_to_dict(model_path: Path) -> bool:
    """Một số bản llmcompressor ghi quantization_config.config_groups thành
    LIST thay vì DICT — vLLM đòi dict {tên_nhóm: nhóm}. Không phụ thuộc kiến
    trúc model (Qwen, Gemma... đều có thể dính, tuỳ phiên bản llmcompressor
    lúc export), nên áp dụng cho MỌI biến thể quantized, không riêng Qwen.
    Patch tạm nếu cần, trả True nếu đã patch."""
    cfg_path = model_path / "config.json"
    if not cfg_path.exists():
        return False
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    qc = cfg.get("quantization_config", {})
    cg = qc.get("config_groups")
    if isinstance(cg, list):
        qc["config_groups"] = {f"group_{i}": g for i, g in enumerate(cg)}
        cfg["quantization_config"] = qc
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"  đã patch config_groups list->dict cho {model_path.name}")
        return True
    return False


def _patch_extra_special_tokens_list_to_dict(model_path: Path) -> bool:
    """NGUYÊN NHÂN THẬT của lỗi 'list' object has no attribute 'keys' khi sinh
    trên Qwen quantized — ĐÃ XÁC MINH BẰNG TRACEBACK, không phải config_groups:

        transformers/tokenization_utils_base.py:1210 _set_model_specific_special_tokens
        self.SPECIAL_TOKENS_ATTRIBUTES + list(special_tokens.keys())
        AttributeError: 'list' object has no attribute 'keys'

    `_compress.py` gọi tok.save_pretrained(out) sau khi AutoTokenizer.from_pretrained()
    nạp tokenizer Qwen2 (có sẵn extra_special_tokens dạng LIST 13 token thị giác:
    <|im_start|>, <|vision_start|>...). Lúc lưu, transformers khi đó chấp nhận
    list. `transformers>=4.55` trên Modal lúc NẠP LẠI đòi DICT {tên: token} và
    gọi thẳng .keys() không kiểm kiểu trước — vỡ ngay tại __init__ tokenizer,
    TRƯỚC khi kịp sinh gì. bf16 không dính vì chưa qua vòng save_pretrained này
    (tải thẳng bằng snapshot_download, không có field extra_special_tokens).

    Đặt tên khoá từ chính token (bỏ <| |>) để dict vẫn đọc được ý nghĩa,
    không dùng khoá vô nghĩa kiểu key_0, key_1."""
    cfg_path = model_path / "tokenizer_config.json"
    if not cfg_path.exists():
        return False
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    est = cfg.get("extra_special_tokens")
    if isinstance(est, list):
        cfg["extra_special_tokens"] = {
            tok.strip("<|>").replace("|", "_") or f"token_{i}": tok
            for i, tok in enumerate(est)
        }
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"  đã patch extra_special_tokens list->dict cho {model_path.name}")
        return True
    return False


def generate_vllm(model_path: Path, prompts: list[str]) -> list[tuple[str, str]]:
    """Sinh bằng vLLM. KHÔNG hardcode quantization — để vLLM tự đọc config.json."""
    from vllm import LLM, SamplingParams

    tag = model_path.name

    # Gemma3 quantized: patch rope nếu thiếu
    if "gemma" in tag.lower() and "bf16" not in tag:
        _patch_gemma3_rope(model_path)

    # Mọi model quantized: config_groups có thể bị ghi sai dạng list
    if "bf16" not in tag and "gguf" not in tag:
        _patch_config_groups_list_to_dict(model_path)
        _patch_extra_special_tokens_list_to_dict(model_path)

    log(f"  nạp model {tag} (quantization=auto từ config.json)")
    llm = LLM(
        model=str(model_path),
        dtype="auto",
        # KHÔNG truyền quantization= → vLLM tự đọc từ config.json
        # (llmcompressor ghi sẵn quantization_config vào config.json)
        max_model_len=4096,
        gpu_memory_utilization=0.85,
        seed=SAMPLING["seed"],
        trust_remote_code=True,
    )
    sp = SamplingParams(
        temperature=SAMPLING["temperature"],
        top_p=SAMPLING["top_p"],
        max_tokens=SAMPLING["max_tokens"],
        seed=SAMPLING["seed"],
    )
    outs = llm.generate(prompts, sp)
    # finish_reason "length" = bị CẮT vì hết max_tokens, không phải model tự
    # dừng. Phải ghi lại: detector E6 (suy sụp mạch lạc) dùng "không kết thúc
    # bằng dấu câu" làm tín hiệu, và sẽ hiểu nhầm MỌI câu bị cắt vì hết ngân
    # sách token là "vỡ mạch lạc" nếu không biết finish_reason. Bug này đã bắt
    # được trên dữ liệu thật: 135/150 cờ E6 ở BF16 (mốc CHƯA nén) đều do cắt
    # ngang, không phải suy giảm — xem viedge.taxonomy.detectors.
    return [(o.outputs[0].text, o.outputs[0].finish_reason) for o in outs]


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
            log(f"[dry] sẽ sinh {len(probes)} outputs cho {tag} -> {outfile.name}")
            continue

        log(f"=== {tag} — sinh {len(probes)} outputs ===")
        prompts = [p["prompt"] for p in probes]
        try:
            outputs = generate_vllm(v, prompts)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log(f"LỖI khi sinh {tag}: {e}")
            log(tb)  # BẮT BUỘC in traceback đầy đủ — str(e) không đủ để định vị dòng lỗi
            append_runlog({"step": "06a_generate", "tag": tag, "error": str(e), "traceback": tb})
            continue

        n_cut = sum(1 for _, fr in outputs if fr == "length")
        with outfile.open("w", encoding="utf-8") as f:
            for probe, (text, finish_reason) in zip(probes, outputs):
                f.write(json.dumps(
                    {"id": probe["id"], "prompt": probe["prompt"], "output": text,
                     "finish_reason": finish_reason},
                    ensure_ascii=False,
                ) + "\n")

        log(f"đã ghi {outfile.relative_to(ROOT)} ({len(outputs)} dòng, "
            f"{n_cut} bị cắt vì hết max_tokens={SAMPLING['max_tokens']})")
        if n_cut / len(outputs) > 0.3:
            log(f"   ⚠️ {100*n_cut/len(outputs):.0f}% bị cắt — cân nhắc tăng max_tokens, "
                f"nếu không detector E6 sẽ thiếu tín hiệu ở nhiều mẫu (đã lọc "
                f"finish_reason='length' khỏi E6, nhưng câu trả lời vẫn thiếu nội dung).")
        append_runlog({
            "step": "06a_generate", "tag": tag, "n": len(outputs), "n_cut": n_cut,
            "sampling": SAMPLING,
        })

    if skipped_gguf:
        log(f"⚠️  BỎ QUA {len(skipped_gguf)} biến thể GGUF: {skipped_gguf}")
        log("   GGUF phải chạy bằng llama-cpp-python (viết script riêng)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
