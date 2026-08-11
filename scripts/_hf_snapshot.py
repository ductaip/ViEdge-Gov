#!/usr/bin/env python3
"""Tải mô hình gốc (mốc tham chiếu BF16). Dùng: python _hf_snapshot.py <hf_id> <out_dir>"""
import sys
from pathlib import Path

def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__); return 2
    hf_id, out = sys.argv[1], Path(sys.argv[2])
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("pip install huggingface_hub"); return 1
    out.mkdir(parents=True, exist_ok=True)
    kw = {}
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        from viedge.env import hf_token
        if (t := hf_token()):
            kw["token"] = t
    except Exception:
        pass
    p = snapshot_download(repo_id=hf_id, local_dir=str(out),
                          ignore_patterns=["*.pt", "*.msgpack", "*.h5", "*consolidated*"],
                          **kw)
    print(f"[bf16] {hf_id} -> {p}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
