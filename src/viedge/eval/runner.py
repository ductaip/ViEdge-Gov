"""
Điều phối đánh giá. Bọc quanh lm-eval, KHÔNG viết lại harness.

CẤU HÌNH ĐÃ CHẠY THÔNG (từ chiến dịch Viettel — dùng lại nguyên xi):
  * lm-eval==0.4.12   (0.4.9 lỗi AutoModelForVision2Seq)
  * KHÔNG ghim transformers==4.53.2 nếu cùng env với vllm (xung đột)
  * backend local-completions + tokenizer trỏ path local
  * Modal image: nvidia/cuda devel (cần nvcc cho flashinfer JIT)

Hai loại đánh giá trong đề tài:
  A. MCQ (VMLU)  -> lm-eval, loglikelihood, nhanh, rẻ
  B. Sinh tự do  -> tự chạy, để lấy văn bản cho taxonomy lỗi E1-E6
Loại B mới là chỗ tính mới nằm; loại A chỉ là đường cong nền.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalJob:
    model_tag: str          # vd. "qwen3.5-2b@int4_awq"
    model_path: str
    tasks: list[str] = field(default_factory=lambda: ["vmlu_sampled"])
    batch_size: str = "auto"
    limit: int | None = None
    out_dir: Path = Path("results/eval")
    extra_args: list[str] = field(default_factory=list)

    def command(self) -> list[str]:
        cmd = [
            "lm_eval",
            "--model", "hf",
            "--model_args", f"pretrained={self.model_path},trust_remote_code=True",
            "--tasks", ",".join(self.tasks),
            "--batch_size", self.batch_size,
            "--output_path", str(self.out_dir / self.model_tag),
            "--log_samples",
        ]
        if self.limit:
            cmd += ["--limit", str(self.limit)]
        return cmd + self.extra_args


def run(job: EvalJob, dry_run: bool = False) -> int:
    cmd = job.command()
    print("[eval]", " ".join(shlex.quote(c) for c in cmd), flush=True)
    if dry_run:
        return 0
    job.out_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.call(cmd)


def collect_results(out_dir: str | Path) -> list[dict]:
    """Quét mọi file kết quả lm-eval thành bảng phẳng để dựng bảng báo cáo."""
    rows: list[dict] = []
    for f in sorted(Path(out_dir).rglob("results*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        tag = f.parent.name
        for task, metrics in (data.get("results") or {}).items():
            row = {"model_tag": tag, "task": task}
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    row[k] = v
            rows.append(row)
    return rows


def degradation_table(rows: list[dict], metric: str = "acc,none", ref_precision: str = "bf16") -> list[dict]:
    """Bảng trung tâm của RQ1: mức tụt tuyệt đối và tương đối so với BF16.

    model_tag theo quy ước "<model>@<precision>".
    """
    by_model: dict[str, dict[str, float]] = {}
    for r in rows:
        if metric not in r:
            continue
        tag = str(r["model_tag"])
        model, _, prec = tag.partition("@")
        by_model.setdefault(model, {})[prec or "unknown"] = float(r[metric])
    out: list[dict] = []
    for model, precs in sorted(by_model.items()):
        ref = precs.get(ref_precision)
        for prec, val in sorted(precs.items()):
            row = {"model": model, "precision": prec, metric: round(val, 4)}
            if ref is not None:
                row["delta_abs"] = round(val - ref, 4)
                row["delta_rel_pct"] = round(100 * (val - ref) / ref, 2) if ref else None
            out.append(row)
    return out
