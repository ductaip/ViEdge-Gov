#!/usr/bin/env python3
"""
Kiểm tra phần cứng + thư viện, và nói THẲNG mức nén nào chạy được trên máy này.

VÌ SAO SCRIPT NÀY QUAN TRỌNG VỚI ĐỀ TÀI, KHÔNG CHỈ VỚI CODE:

FP8 W8A8 chỉ được hỗ trợ NATIVE trên compute capability >= 8.9 (Ada, Hopper).
Trên Ampere (SM 8.0/8.6) và Turing (SM 7.5), vLLM VẪN CHẠY mô hình FP8 — nhưng
tự động rơi về **W8A16 weight-only qua kernel Marlin**. Nó không báo lỗi.

Hệ quả cho đề tài: W8A8 lượng tử hoá CẢ activation, W8A16 thì KHÔNG. Đó là hai
sơ đồ nén khác nhau, cho ra chất lượng khác nhau. Nếu chạy "FP8" trên RTX 3050
rồi ghi vào Bảng 3 là "FP8", ta báo cáo một con số của sơ đồ khác dưới tên FP8 —
**sai về khoa học, và không ai phát hiện được vì không có thông báo lỗi nào.**

Đây đúng là loại lỗi mà chính đề tài đang nghiên cứu: suy giảm âm thầm.
"""
from __future__ import annotations
import importlib.util, os, shutil, sys
from pathlib import Path
from _common import log

# (tên, SM tối thiểu cho tính toán NATIVE, ghi chú khi không đạt)
PRECISION_REQ = [
    ("bf16",        80, "Ampere trở lên. Dưới SM80 (T4/P100) không có BF16 native -> dùng fp16 thay thế và GHI RÕ trong báo cáo"),
    ("fp8 (W8A8)",  89, "CHỈ Ada/Hopper. Dưới ngưỡng, vLLM âm thầm rơi về W8A16 Marlin -> ĐANG ĐO THỨ KHÁC"),
    ("int8 (W8A8)", 75, "Turing trở lên"),
    ("int4 (W4A16)",75, "Turing trở lên"),
    ("gguf (CPU)",   0, "không cần GPU"),
]

# Ước lượng VRAM cần: hệ số nhân trên số tham số (tỉ) + phần dôi cho KV/activation
BYTES_PER_PARAM = {"bf16": 2.0, "fp8": 1.0, "int8": 1.0, "int4": 0.55, "gguf_q4": 0.55}
OVERHEAD_GB = 1.2


def gpu_info():
    try:
        import torch
    except ImportError:
        return None
    if not torch.cuda.is_available():
        return {"name": None, "torch": torch.__version__}
    i = torch.cuda.current_device()
    major, minor = torch.cuda.get_device_capability(i)
    props = torch.cuda.get_device_properties(i)
    return {
        "name": props.name,
        "sm": major * 10 + minor,
        "vram_gb": round(props.total_memory / 1024**3, 2),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
    }


def have(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def main() -> int:
    print("\n" + "=" * 74)
    print("ViEdge-Gov · KIỂM TRA MÔI TRƯỜNG")
    print("=" * 74)

    g = gpu_info()
    if g is None:
        log("chưa cài torch — không kết luận được về GPU"); sm, vram = 0, 0
    elif g["name"] is None:
        log(f"torch {g['torch']} nhưng KHÔNG thấy GPU (CUDA không khả dụng)"); sm, vram = 0, 0
    else:
        sm, vram = g["sm"], g["vram_gb"]
        arch = ("Blackwell" if sm >= 100 else "Hopper" if sm >= 90 else "Ada" if sm >= 89
                else "Ampere" if sm >= 80 else "Turing" if sm >= 75 else "cũ hơn Turing")
        print(f"\nGPU   : {g['name']}")
        print(f"        compute capability SM {sm//10}.{sm%10} ({arch}) · VRAM {vram} GB")
        print(f"        torch {g['torch']} · CUDA {g['cuda']}")

    print(f"\n{'MỨC NÉN':<16}{'CẦN SM':>8}  {'KẾT LUẬN':<14} GHI CHÚ")
    print("-" * 74)
    blocked = []
    for name, need, note in PRECISION_REQ:
        if need == 0:
            verdict = "✅ CHẠY ĐƯỢC"
        elif sm >= need:
            verdict = "✅ CHẠY ĐƯỢC"
        else:
            verdict = "❌ KHÔNG"
            blocked.append(name)
        print(f"{name:<16}{need if need else '—':>8}  {verdict:<14} {note[:44]}")

    if blocked:
        print()
        for name, need, note in PRECISION_REQ:
            if name in blocked:
                log(f"{name}: {note}")

    # VRAM
    if vram:
        print(f"\n{'MÔ HÌNH':<14}{'bf16':>9}{'int8':>9}{'int4':>9}   (GB ước tính, đã cộng {OVERHEAD_GB} GB dôi)")
        print("-" * 74)
        for label, params_b in (("1.2B", 1.2), ("2B", 2.0), ("4B", 4.0), ("7B", 7.0)):
            row = []
            for p in ("bf16", "int8", "int4"):
                need = params_b * BYTES_PER_PARAM[p] + OVERHEAD_GB
                row.append(f"{need:>6.1f}{'✅' if need <= vram else '❌'}")
            print(f"{label:<14}{row[0]:>9}{row[1]:>9}{row[2]:>9}")
        print(f"\n  VRAM khả dụng: {vram} GB. Cột ❌ = phải giảm batch/seq-len, hoặc đổi máy.")

    print("\nTHƯ VIỆN & CÔNG CỤ")
    print("-" * 74)
    checks = [
        ("torch", have("torch"), "pip install torch"),
        ("transformers", have("transformers"), "pip install transformers"),
        ("llmcompressor", have("llmcompressor"), "pip install llmcompressor"),
        ("lm_eval", shutil.which("lm_eval") is not None or have("lm_eval"), "pip install lm-eval==0.4.12"),
        ("datasets", have("datasets"), "pip install datasets"),
        ("huggingface_hub", have("huggingface_hub"), "pip install huggingface_hub"),
        ("sentence_transformers", have("sentence_transformers"), "pip install sentence-transformers"),
        ("llama_cpp (python)", have("llama_cpp"), "pip install llama-cpp-python"),
        ("cmake", shutil.which("cmake") is not None, "sudo apt-get install -y cmake  (cần cho GGUF)"),
        ("sentencepiece", have("sentencepiece"), "pip install sentencepiece  (cần cho GGUF vocab)"),
        ("protobuf", have("google.protobuf"), "pip install protobuf  (cần cho GGUF vocab)"),
        ("antiword", shutil.which("antiword") is not None, "sudo apt-get install -y antiword"),
        ("pdftotext", shutil.which("pdftotext") is not None, "sudo apt-get install -y poppler-utils"),
    ]
    missing = []
    for name, ok, fix in checks:
        print(f"  {'✅' if ok else '❌'} {name:<24}{'' if ok else fix}")
        if not ok:
            missing.append((name, fix))

    # Token HF — đọc từ .env hoặc môi trường, và CHE khi in
    try:
        from viedge.env import hf_token, mask
        tok = hf_token()
        shown = mask(tok)
    except Exception:
        tok = os.environ.get("HF_TOKEN")
        shown = "(có)" if tok else "(chưa có)"
    print(f"  {'✅' if tok else '⚠️ '} HF_TOKEN{'':<16}{shown if tok else 'tạo .env từ .env.example rồi điền HF_TOKEN'}")

    # Quyền ghi cache HF — đã gặp lỗi thật: thư mục cache do root sở hữu sau
    # một lần chạy bằng sudo, khiến mọi lần tải sau đó báo Permission denied
    # nhưng VẪN tải lại từ đầu -> tưởng mạng chậm, thực ra là hỏng cache.
    cache = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    if cache.exists():
        ok_w = os.access(cache, os.W_OK)
        print(f"  {'✅' if ok_w else '❌'} cache HF ghi được    {cache}"
              f"{'' if ok_w else '  -> sudo chown -R $USER:$USER ' + str(cache)}")
        try:
            import shutil as _sh
            free = _sh.disk_usage(cache).free / 1024**3
            print(f"  {'✅' if free > 20 else '⚠️ '} dung lượng trống    {free:.1f} GB"
                  f"{'' if free > 20 else '  -> mỗi model 1.5B tốn ~3.5GB, cả ma trận ~25GB'}")
        except Exception:
            pass
    else:
        print(f"  ⚠️  cache HF chưa tạo   {cache} (sẽ tạo khi tải model đầu tiên)")

    print("\n" + "=" * 74)
    if missing:
        log(f"THIẾU {len(missing)} thứ. Cài trước khi chạy make export/eval:")
        seen = set()
        pips = [f for _, f in missing if f.startswith("pip") and not (f in seen or seen.add(f))]
        apts = [f for _, f in missing if f.startswith("sudo") and not (f in seen or seen.add(f))]
        for f in pips + apts:
            print(f"    {f}")
    if blocked:
        log("PHẢI ĐIỀU CHỈNH MA TRẬN THÍ NGHIỆM — xem docs/DECISIONS.md ADR-011.")
    if not missing and not blocked:
        log("Môi trường đủ điều kiện chạy toàn bộ ma trận.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
