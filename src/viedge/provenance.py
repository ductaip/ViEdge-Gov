"""
Ghi nhận MÁY NÀO chạy bậc nén nào.

VÌ SAO ĐÂY LÀ VẤN ĐỀ KHOA HỌC, KHÔNG PHẢI TIỆN ÍCH:

Khi dùng Modal cho FP8 (cần SM 8.9) còn INT4 chạy ở nhà trên RTX 3050 (SM 8.6),
hai bậc trong CÙNG một đường cong suy giảm được đo trên HAI MÁY KHÁC NHAU. Về
lý thuyết chất lượng không phụ thuộc phần cứng, nhưng thực tế thì:

  * kernel khác nhau theo kiến trúc (Marlin trên Ampere vs cutlass trên Ada)
  * thứ tự cộng dồn float khác nhau -> chênh lệch nhỏ ở loglikelihood
  * phiên bản thư viện trên image Modal khác trên máy local

Chênh lệch đó nhỏ, nhưng suy giảm ta đang đo cũng nhỏ. Nếu Δ(INT8) là 2 điểm mà
sai khác do máy là 0,5 điểm, thì 25% "phát hiện" là nhiễu phần cứng.

QUY TẮC: mọi bậc của CÙNG một model nên chạy trên CÙNG một máy. Nếu buộc phải
tách, ghi rõ trong Bảng 3 và trong phần Thực nghiệm — đừng để hội đồng tự phát hiện.

Module này ghi dấu vết máy vào mỗi thư mục kết quả; `scripts/05` đối chiếu và
cảnh báo nếu một model có các bậc chạy trên máy khác nhau.
"""

from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path


def collect() -> dict:
    """Dấu vết máy hiện tại — đủ để tái lập và để phát hiện trộn máy."""
    info = {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": platform.node(),
        "system": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "runner": "modal" if os.environ.get("MODAL_TASK_ID") else "local",
    }
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda"] = torch.version.cuda
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            major, minor = torch.cuda.get_device_capability(0)
            info["gpu"] = p.name
            info["sm"] = f"{major}.{minor}"
            info["vram_gb"] = round(p.total_memory / 1024**3, 2)
        else:
            info["gpu"] = None
    except Exception:
        pass
    for lib in ("transformers", "llmcompressor", "lm_eval"):
        try:
            mod = __import__(lib)
            info[lib] = getattr(mod, "__version__", "?")
        except Exception:
            pass
    return info


def write(dest_dir: str | Path, extra: dict | None = None) -> Path:
    """Ghi hardware.json vào thư mục kết quả của một biến thể."""
    d = Path(dest_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / "hardware.json"
    p.write_text(json.dumps({**collect(), **(extra or {})}, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    return p


def read(dest_dir: str | Path) -> dict | None:
    p = Path(dest_dir) / "hardware.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def machine_key(info: dict | None) -> str:
    """Khoá gộp: hai lần chạy cùng khoá này thì coi như cùng máy."""
    if not info:
        return "unknown"
    return f"{info.get('runner', '?')}/{info.get('gpu') or 'cpu'}/sm{info.get('sm', '?')}"


def check_consistency(base_dir: str | Path) -> list[dict]:
    """Với mỗi model, các bậc nén có chạy cùng máy không?

    Trả danh sách model bị TRỘN MÁY, kèm chi tiết để in cảnh báo.
    """
    base = Path(base_dir)
    if not base.exists():
        return []
    by_model: dict[str, dict[str, str]] = {}
    for d in sorted(base.glob("*@*")):
        if not d.is_dir():
            continue
        model, _, prec = d.name.partition("@")
        by_model.setdefault(model, {})[prec] = machine_key(read(d))
    out = []
    for model, precs in by_model.items():
        keys = set(precs.values())
        if len(keys) > 1:
            out.append({"model": model, "machines": sorted(keys), "by_precision": precs})
    return out
