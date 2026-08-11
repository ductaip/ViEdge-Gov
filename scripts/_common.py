"""Tiện ích dùng chung cho mọi script: đường dẫn, config, log."""
from __future__ import annotations
import json, os, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

def load_yaml(path: str) -> dict:
    import yaml
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))

def dry_run() -> bool:
    return os.environ.get("DRY", "0") not in ("0", "", "false", "False")

def rel(path) -> str:
    """Đường dẫn để HIỂN THỊ: tương đối nếu trong repo, tuyệt đối nếu ngoài.

    Path.relative_to() ném ValueError khi đích nằm ngoài repo (vd. ghi ra /tmp).
    Ném lỗi chỉ vì một dòng log là hỏng cả lần chạy — nhất là khi công việc
    thật đã xong xuôi.
    """
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def save_json(obj, rel_path: str) -> Path:
    p = ROOT / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[saved] {rel(p)}")
    return p

def log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def append_runlog(entry: dict) -> None:
    """Mọi lần chạy thật PHẢI ghi vào đây. Cuối tuần copy sang WEEKLOG.md.
    Không có runlog = cuối tháng không dựng lại được bảng nào."""
    p = ROOT / "logs" / "runlog.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), **entry}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[runlog] {entry.get('step','?')} :: {entry.get('note','')}")
