"""
Xuất mô hình ở 4 mức chính xác số học.

BÀI HỌC ĐÃ TRẢ GIÁ (từ chiến dịch Viettel — đừng lặp lại):
  * bitsandbytes NF4: chi phí dequant ăn hết phần tiết kiệm băng thông,
    TPOT ~58ms vs ~38ms của FP8 (chậm ~50%), và văn bản ngữ cảnh dài
    bắt đầu vỡ nghĩa. => KHÔNG dùng bnb làm đường 4-bit chính. Dùng AWQ
    (có calibration) cho GPU, GGUF Q4_K_M cho CPU.
  * FP8 W8A8 KHÔNG phá gate độ chính xác trên tác vụ tiếng Anh
    (GPQA delta ~0.02). Nhưng đó là TIẾNG ANH — chính khoảng trống này
    là lý do đề tài tồn tại. Phải đo lại trên tiếng Việt.
  * Image Modal phải là nvidia/cuda devel (cần nvcc cho JIT), KHÔNG
    dùng debian_slim.

Module này chỉ điều phối; công việc nặng gọi ra CLI của llm-compressor /
autoawq / llama.cpp để không nhốt logic vào một phiên bản thư viện.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

PRECISIONS = ("bf16", "fp8", "int8", "int4_awq", "gguf_q8_0", "gguf_q4_k_m")


@dataclass
class ExportSpec:
    model_id: str          # HF repo hoặc path local
    precision: str
    out_dir: Path
    use_gptq: bool = False   # W4A16: dùng GPTQ (có calib) thay vì RTN data-free
    calib_dataset: str = "data/processed/calib_vi.jsonl"
    calib_samples: int = 256
    max_seq_len: int = 4096

    def validate(self) -> None:
        if self.precision not in PRECISIONS:
            raise ValueError(f"precision không hỗ trợ: {self.precision} (chọn trong {PRECISIONS})")


def build_command(spec: ExportSpec) -> list[str]:
    """Trả về câu lệnh sẽ chạy — in ra trước khi chạy để log vào WEEKLOG."""
    spec.validate()
    out = str(spec.out_dir)
    p = spec.precision

    if p == "bf16":
        # Chỉ tải về, không nén. Đây là mốc tham chiếu của toàn bộ đề tài.
        return ["python", "scripts/_hf_snapshot.py", spec.model_id, out]

    if p in ("fp8", "int8", "int4_awq"):
        scheme = {"fp8": "FP8_DYNAMIC", "int8": "W8A8", "int4_awq": "W4A16"}[p]
        return [
            "python", "scripts/_compress.py",
            "--model", spec.model_id,
            "--scheme", scheme,
            "--out", out,
            "--calib", spec.calib_dataset,
            "--num-calib", str(spec.calib_samples),
            "--max-seq-len", str(spec.max_seq_len),
        ] + (["--use-gptq"] if (spec.use_gptq and p == "int4_awq") else [])

    # GGUF cho CPU: convert -> quantize
    qtype = "Q8_0" if p == "gguf_q8_0" else "Q4_K_M"
    return [
        "bash", "scripts/_to_gguf.sh", spec.model_id, out, qtype,
    ]


def run(spec: ExportSpec, dry_run: bool = False) -> int:
    cmd = build_command(spec)
    print("[export]", " ".join(shlex.quote(c) for c in cmd), flush=True)
    if dry_run:
        return 0
    Path(spec.out_dir).mkdir(parents=True, exist_ok=True)
    try:
        from viedge.env import child_env
        env = child_env()
    except Exception:
        env = None
    return subprocess.call(cmd, env=env)


# CALIBRATION — điểm dễ sai nhất, đọc kỹ.
#
# Bộ calibration cho quantization PHẢI là tiếng Việt, và nên gồm cả văn bản
# pháp luật. Nếu calibrate bằng C4/WikiText tiếng Anh (mặc định của phần lớn
# tutorial), scale được chọn theo phân bố activation tiếng Anh, và ta tự tay
# tạo ra chính hiện tượng suy giảm mà đề tài đang đo — làm hỏng tính hợp lệ
# nội tại của thí nghiệm.
#
# => Thí nghiệm phụ ĐÁNG GIÁ (nếu còn thời gian, P4): so cùng một mức nén với
#    calib tiếng Anh vs calib tiếng Việt. Nếu chênh lệch lớn, đó là một phát
#    hiện độc lập và là khuyến nghị kỹ thuật rất cụ thể cho cộng đồng VN.
CALIB_NOTE = __doc__
