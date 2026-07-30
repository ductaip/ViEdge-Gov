#!/usr/bin/env bash
# Chuyển HF -> GGUF rồi lượng tử hoá. Dùng: _to_gguf.sh <model_dir_or_hf_id> <out_dir> <QTYPE>
set -euo pipefail
MODEL="${1:?thiếu model}"; OUT="${2:?thiếu out}"; QTYPE="${3:-Q4_K_M}"
LCPP="${LLAMA_CPP_DIR:-$HOME/llama.cpp}"

if [ ! -d "$LCPP" ]; then
  echo "[gguf] clone llama.cpp -> $LCPP"
  git clone --depth 1 https://github.com/ggerganov/llama.cpp "$LCPP"
  cmake -S "$LCPP" -B "$LCPP/build" >/dev/null
  cmake --build "$LCPP/build" --config Release -j"$(nproc)" >/dev/null
fi

mkdir -p "$OUT"
F16="$OUT/model-f16.gguf"
if [ ! -f "$F16" ]; then
  echo "[gguf] convert -> $F16"
  python "$LCPP/convert_hf_to_gguf.py" "$MODEL" --outfile "$F16" --outtype f16
fi

TARGET="$OUT/model-$(echo "$QTYPE" | tr 'A-Z' 'a-z').gguf"
echo "[gguf] quantize $QTYPE -> $TARGET"
"$LCPP/build/bin/llama-quantize" "$F16" "$TARGET" "$QTYPE"
ls -lh "$TARGET"
echo "[gguf] xong. Đo hiệu năng: python scripts/11_bench_cpu.py --gguf $TARGET --tag <tag>"
