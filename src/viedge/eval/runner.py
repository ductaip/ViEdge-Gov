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
    model_tag: str          # vd. "qwen2.5-1.5b-it@int4_awq"
    model_path: str
    tasks: list[str] = field(default_factory=lambda: ["vmlu_sampled"])
    batch_size: str = "auto"
    limit: int | None = None
    out_dir: Path = Path("results/eval")
    extra_args: list[str] = field(default_factory=list)
    model_args_override: str | None = None

    def command(self) -> list[str]:
        margs = self.model_args_override or f"pretrained={self.model_path},trust_remote_code=True"
        cmd = [
            "lm_eval",
            "--model", "hf",
            "--model_args", margs,
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
    # Truyền token tường minh: lm_eval là tiến trình con, không tự đọc .env.
    try:
        from viedge.env import child_env
        env = child_env()
    except Exception:
        env = None
    return subprocess.call(cmd, env=env)


def _tag_from_path(out_dir: Path, f: Path) -> str:
    """Lấy model_tag từ đường dẫn file kết quả.

    ⚠️ KHÔNG dùng f.parent.name. lm-eval tạo THÊM một cấp thư mục đặt tên theo
    ĐƯỜNG DẪN MODEL đã làm sạch:

        results/eval/gemma3-1b-it@bf16/__root__viedge__models__gemma3-1b-it@bf16/results_*.json
                     ^^^^^^^^^^^^^^^^ tag thật    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ tên lm-eval đặt

    Lấy nhầm cấp trong cho ra tag "__root__viedge__models__gemma3-1b-it", và vì
    tag được tách ở dấu "@" nên model/precision đều sai. Tệ hơn: `load_per_sample`
    tra theo tag đó sẽ không thấy file nào -> im lặng bỏ qua kiểm định McNemar,
    tức là MẤT chỉ số chính của Bảng 3 mà chỉ có một dòng log nhỏ báo.

    Lấy cấp NGAY DƯỚI out_dir mới đúng.
    """
    try:
        rel = f.relative_to(out_dir)
    except ValueError:
        return f.parent.name
    return rel.parts[0] if rel.parts else f.parent.name


def collect_results(out_dir: str | Path) -> list[dict]:
    """Quét mọi file kết quả lm-eval thành bảng phẳng để dựng bảng báo cáo."""
    base = Path(out_dir)
    rows: list[dict] = []
    for f in sorted(base.rglob("results*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        tag = _tag_from_path(base, f)
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


def load_per_sample(out_dir: str | Path, model_tag: str) -> list[bool] | None:
    """Đọc đúng/sai TỪNG CÂU từ file --log_samples của lm-eval.

    Cần cho kiểm định bắt cặp: chỉ có accuracy tổng thì không tính McNemar được.
    Vì vậy scripts/05 LUÔN chạy với --log_samples, đừng bỏ cờ đó để tiết kiệm đĩa.
    """
    base = Path(out_dir) / model_tag
    # rglob vì lm-eval lồng thêm một cấp thư mục đặt theo đường dẫn model.
    files = sorted(base.rglob("samples_*.jsonl"))
    if not files:
        return None
    out: list[bool] = []
    for line in files[0].read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        acc = r.get("acc", r.get("exact_match"))
        if acc is None and "filtered_resps" in r:
            continue
        out.append(bool(acc))
    return out or None


def paired_significance(
    out_dir: str | Path,
    model: str,
    ref_precision: str = "bf16",
    precisions: list[str] | None = None,
) -> list[dict]:
    """Bảng McNemar cho từng bậc nén so với mốc tham chiếu.

    Đây là chỉ số CHÍNH của Bảng 3, không phải MoE độc lập — xem ADR-013.
    """
    from viedge.eval.significance import mcnemar, paired_bootstrap_ci

    ref = load_per_sample(out_dir, f"{model}@{ref_precision}")
    if ref is None:
        return []
    rows = []
    base = Path(out_dir)
    tags = precisions or sorted(
        d.name.split("@", 1)[1] for d in base.glob(f"{model}@*") if d.is_dir()
    )
    for prec in tags:
        if prec == ref_precision:
            continue
        cur = load_per_sample(out_dir, f"{model}@{prec}")
        if cur is None or len(cur) != len(ref):
            rows.append({"model": model, "precision": prec,
                         "note": "thiếu dữ liệu từng câu hoặc lệch số câu — không kiểm định được"})
            continue
        r = mcnemar(ref, cur)
        lo, hi = paired_bootstrap_ci(ref, cur, n_boot=5000)
        rows.append({
            "model": model, "precision": prec, "n": r.n,
            "acc_ref": round(r.acc_a, 4), "acc": round(r.acc_b, 4),
            "delta": round(r.delta, 4),
            "ci95_low": round(lo, 4), "ci95_high": round(hi, 4),
            "flip_down": r.b, "flip_up": r.c,
            "p_value": round(r.p_value, 6), "method": r.method,
            "significant": r.significant,
        })
    return rows
