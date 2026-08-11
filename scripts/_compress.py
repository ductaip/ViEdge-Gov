#!/usr/bin/env python3
"""
Nén W8A8 / W4A16 / FP8 bằng llm-compressor.

CALIBRATION BẰNG TIẾNG VIỆT — đọc docs/DECISIONS.md ADR-007 trước khi đổi.
Dùng C4 tiếng Anh sẽ tự tạo ra chính hiện tượng suy giảm mà đề tài đang đo.

⚠️ BẮT BUỘC TRUYỀN `processor=tokenizer` VÀO `oneshot`.
Nếu không, llm-compressor tự gọi `AutoProcessor.from_pretrained(model)`. Với các
model thuộc HỌ ĐA PHƯƠNG THỨC (Gemma-3, Qwen-VL, Llama-Vision...), AutoProcessor
tìm `preprocessor_config.json` để dựng image processor — mà bản TEXT-ONLY như
`google/gemma-3-1b-it` không có file đó, nên đổ:

    OSError: Can't load image processor for 'google/gemma-3-1b-it'

Lỗi trông như "thiếu file trên Hub" nhưng thực chất là llm-compressor đoán sai
loại processor. Truyền thẳng tokenizer là hết — chính thông báo lỗi cũng gợi ý vậy.
"""
import argparse, json, sys
from pathlib import Path


def load_calib(path: str, n: int) -> list[str]:
    p = Path(path)
    if not p.exists():
        print(f"[LỖI] không có bộ calib {path}")
        print('      Tạo file jsonl, mỗi dòng {"text": "<văn bản tiếng Việt>"}')
        print("      Hoặc chạy: python scripts/02c_build_calib.py --add-wiki 150")
        sys.exit(1)
    texts = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            texts.append(json.loads(line)["text"])
        if len(texts) >= n:
            break
    if len(texts) < n:
        print(f"[cảnh báo] chỉ có {len(texts)}/{n} mẫu calib")
        print("           calib ít -> scale kém đại diện. Bổ sung bằng:")
        print("           python scripts/02c_build_calib.py --add-wiki 150")
    return texts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--scheme", required=True, choices=["FP8_DYNAMIC", "W8A8", "W4A16"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--calib", default="data/processed/calib_vi.jsonl")
    ap.add_argument("--num-calib", type=int, default=256)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    a = ap.parse_args()

    try:
        from llmcompressor import oneshot
        from llmcompressor.modifiers.quantization import QuantizationModifier
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        print(f"thiếu thư viện: {e}\n  pip install llmcompressor transformers")
        return 1

    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        a.model, dtype="auto", device_map="auto", trust_remote_code=True)

    recipe = QuantizationModifier(targets="Linear", scheme=a.scheme, ignore=["lm_head"])

    # FP8_DYNAMIC không cần calibration; W8A8/W4A16 thì cần.
    if a.scheme == "FP8_DYNAMIC":
        oneshot(model=model, recipe=recipe, output_dir=a.out, processor=tok)
    else:
        from datasets import Dataset
        texts = load_calib(a.calib, a.num_calib)
        if not texts:
            print("[LỖI] bộ calib rỗng"); return 1
        ds = Dataset.from_dict({"text": texts}).map(
            lambda b: tok(b["text"], truncation=True, max_length=a.max_seq_len),
            batched=True, remove_columns=["text"])
        oneshot(
            model=model,
            dataset=ds,
            recipe=recipe,
            output_dir=a.out,
            max_seq_length=a.max_seq_len,
            num_calibration_samples=len(texts),
            processor=tok,          # ⚠️ BẮT BUỘC — xem docstring
        )

    tok.save_pretrained(a.out)
    print(f"[{a.scheme}] -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
