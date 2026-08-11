"""
Nạp biến môi trường từ file .env — KHÔNG hardcode bí mật vào mã nguồn.

VÌ SAO QUAN TRỌNG VỚI ĐỀ TÀI NÀY, KHÔNG CHỈ VỚI BẢO MẬT:
Repo sẽ được đẩy lên git và có thể nộp kèm hồ sơ. Token nằm trong mã nguồn thì
nằm luôn trong LỊCH SỬ GIT — xoá ở commit sau cũng không gỡ được, phải rewrite
history. Ngoài ra `docs/SUBMISSION_CHECKLIST.md` yêu cầu ẩn danh hồ sơ; token
gắn với tài khoản cá nhân là một đường lộ danh tính.
"""

from __future__ import annotations

import os
from pathlib import Path

SECRET_KEYS = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN")


def load_dotenv(path: str | Path | None = None, override: bool = False) -> dict[str, str]:
    """Đọc .env ở gốc repo. Biến môi trường sẵn có được ưu tiên (override=False)."""
    root = Path(__file__).resolve().parents[2]
    p = Path(path) if path else root / ".env"
    loaded: dict[str, str] = {}
    if not p.exists():
        return loaded
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if not v:
            continue
        if override or k not in os.environ:
            os.environ[k] = v
        loaded[k] = v
    return loaded


def hf_token() -> str | None:
    """Token HF từ môi trường hoặc .env. Trả None nếu không có."""
    load_dotenv()
    for k in SECRET_KEYS:
        v = os.environ.get(k)
        if v and v.strip():
            # Đồng bộ mọi tên biến để thư viện nào cũng thấy
            for kk in SECRET_KEYS:
                os.environ.setdefault(kk, v)
            return v
    return None


def mask(secret: str | None) -> str:
    """Che token khi in ra log. In nguyên token vào log = lộ token."""
    if not secret:
        return "(chưa có)"
    return f"{secret[:6]}…{secret[-4:]} (dài {len(secret)})"


def child_env() -> dict:
    """Bản sao os.environ đã có token, để truyền cho tiến trình con.

    `lm_eval` và các script export chạy qua subprocess. Nếu không truyền env
    tường minh, chúng có thể không thấy token vừa nạp từ .env trong tiến trình
    cha — và sẽ tải chậm hoặc lỗi 401 với repo gated.
    """
    import os as _os
    env = dict(_os.environ)
    tok = hf_token()
    if tok:
        for k in SECRET_KEYS:
            env[k] = tok
    return env
