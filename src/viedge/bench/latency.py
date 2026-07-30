"""
Đo hiệu năng trên MÁY MỤC TIÊU (CPU), không phải trên GPU.

Toàn bộ luận điểm ứng dụng của đề tài là "chạy được trên máy cấp xã".
Nếu chỉ báo cáo số đo trên T4 thì luận điểm đó không có căn cứ. Bảng số
phải đo trên đúng cấu hình sẽ triển khai, và cấu hình đó phải được ghi
vào báo cáo (CPU model, số core, RAM, OS).
"""

from __future__ import annotations

import json
import platform
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class HostInfo:
    machine: str = ""
    processor: str = ""
    system: str = ""
    python: str = ""
    n_cpu_logical: int = 0
    ram_total_gb: float = 0.0

    @classmethod
    def collect(cls) -> "HostInfo":
        import os
        ram = 0.0
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        ram = round(int(line.split()[1]) / 1024 / 1024, 2)
                        break
        except OSError:
            pass
        return cls(
            machine=platform.machine(),
            processor=platform.processor() or platform.uname().processor,
            system=f"{platform.system()} {platform.release()}",
            python=platform.python_version(),
            n_cpu_logical=os.cpu_count() or 0,
            ram_total_gb=ram,
        )


@dataclass
class RunMetrics:
    ttft_ms: float
    total_ms: float
    n_output_tokens: int

    @property
    def tokens_per_s(self) -> float:
        gen_ms = max(self.total_ms - self.ttft_ms, 1e-6)
        return (self.n_output_tokens - 1) / (gen_ms / 1000) if self.n_output_tokens > 1 else 0.0

    @property
    def tpot_ms(self) -> float:
        if self.n_output_tokens <= 1:
            return 0.0
        return (self.total_ms - self.ttft_ms) / (self.n_output_tokens - 1)


@dataclass
class BenchResult:
    tag: str
    host: HostInfo
    runs: list[RunMetrics] = field(default_factory=list)
    peak_rss_mb: float = 0.0
    model_disk_mb: float = 0.0

    def summary(self) -> dict:
        if not self.runs:
            return {"tag": self.tag, "n_runs": 0}
        ttft = [r.ttft_ms for r in self.runs]
        tps = [r.tokens_per_s for r in self.runs]
        tpot = [r.tpot_ms for r in self.runs]
        def pct(xs, q):
            xs = sorted(xs)
            return round(xs[min(len(xs) - 1, int(q * len(xs)))], 2)
        return {
            "tag": self.tag,
            "n_runs": len(self.runs),
            "ttft_ms_median": round(statistics.median(ttft), 2),
            "ttft_ms_p95": pct(ttft, 0.95),
            "tpot_ms_median": round(statistics.median(tpot), 2),
            "tokens_per_s_median": round(statistics.median(tps), 2),
            "peak_rss_mb": round(self.peak_rss_mb, 1),
            "model_disk_mb": round(self.model_disk_mb, 1),
            "host": asdict(self.host),
        }


def peak_rss_mb() -> float:
    import resource
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux báo KB, macOS báo byte.
    return ru / 1024 if platform.system() == "Linux" else ru / 1024 / 1024


def dir_size_mb(path: str | Path) -> float:
    p = Path(path)
    if not p.exists():
        return 0.0
    if p.is_file():
        return p.stat().st_size / 1024 / 1024
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1024 / 1024


def measure(
    generate_stream: Callable[[str], "object"],
    prompts: list[str],
    tag: str,
    warmup: int = 1,
) -> BenchResult:
    """generate_stream(prompt) -> iterator các token/chunk văn bản.

    TTFT = thời gian đến chunk đầu tiên. Phải warmup trước, nếu không lần
    chạy đầu gánh cả chi phí nạp mô hình và số TTFT sẽ vô nghĩa.
    """
    res = BenchResult(tag=tag, host=HostInfo.collect())
    for p in prompts[:warmup]:
        for _ in generate_stream(p):
            pass
    for prompt in prompts:
        t0 = time.perf_counter()
        first_at = None
        n = 0
        for _chunk in generate_stream(prompt):
            if first_at is None:
                first_at = time.perf_counter()
            n += 1
        t1 = time.perf_counter()
        if first_at is None:
            continue
        res.runs.append(
            RunMetrics(
                ttft_ms=(first_at - t0) * 1000,
                total_ms=(t1 - t0) * 1000,
                n_output_tokens=n,
            )
        )
    res.peak_rss_mb = peak_rss_mb()
    return res


def save(result: BenchResult, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result.summary(), ensure_ascii=False, indent=2), encoding="utf-8")
