#!/usr/bin/env python3
"""
Đăng nhập HuggingFace MỘT LẦN, dùng cho mọi lần tải về sau.

VÌ SAO CẦN SCRIPT RIÊNG:
Truyền `token=...` vào từng lời gọi `from_pretrained` KHÔNG dập được cảnh báo
"You are sending unauthenticated requests" — tầng HTTP của huggingface_hub đọc
BIẾN MÔI TRƯỜNG / file token trong cache, không đọc tham số của lời gọi. Ngoài
ra `lm_eval` chạy như TIẾN TRÌNH CON, nó không thấy os.environ ta đặt trong
Python cha nếu không được kế thừa đúng.

Script này ghi token vào cache chuẩn của HF (~/.cache/huggingface/token), nên:
  * mọi thư viện (transformers, datasets, hub) đều thấy
  * mọi tiến trình con (lm_eval, script export) đều thấy
  * chỉ phải làm MỘT LẦN trên mỗi máy

BẢO MẬT:
  * Token đọc từ .env (đã gitignore), KHÔNG hardcode trong mã nguồn.
  * File token của HF nằm ngoài repo -> không lọt vào git.
  * add_to_git_credential=False: KHÔNG ghi token vào git credential helper,
    tránh vô tình đẩy lên remote.
  * Mọi log đều che token.

    python scripts/00h_hf_login.py
    python scripts/00h_hf_login.py --check     # chỉ kiểm, không ghi
"""
from __future__ import annotations
import argparse
from _common import ROOT, log, rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="chỉ kiểm tra, không ghi cache")
    args = ap.parse_args()

    from viedge.env import hf_token, mask

    tok = hf_token()          # đọc .env + đồng bộ mọi tên biến môi trường
    if not tok:
        log("KHÔNG tìm thấy token.")
        log(f"  1. cp .env.example .env      (tại {rel(ROOT)})")
        log("  2. mở .env, điền HF_TOKEN=hf_...")
        log("  3. chạy lại lệnh này")
        log("")
        log("  Lấy token tại https://huggingface.co/settings/tokens")
        log("  Quyền READ là đủ cho đề tài này — KHÔNG cần Write.")
        return 1

    if not tok.startswith("hf_"):
        log(f"Token có dạng lạ ({mask(tok)}) — token HF thường bắt đầu bằng 'hf_'.")
        log("Kiểm lại đã copy đủ chưa.")

    try:
        from huggingface_hub import HfApi, login
    except ImportError:
        log("Chưa có huggingface_hub. Chạy: pip install huggingface_hub"); return 1

    # Xác thực TRƯỚC khi ghi cache — token sai mà ghi vào cache thì mọi lần tải
    # sau đều lỗi 401 với thông báo khó hiểu.
    try:
        who = HfApi().whoami(token=tok)
    except Exception as e:
        log(f"Token KHÔNG hợp lệ: {type(e).__name__}: {str(e)[:80]}")
        log("  Vào https://huggingface.co/settings/tokens, tạo token mới (quyền Read).")
        return 1

    name = who.get("name") or who.get("fullname") or "(không rõ)"
    log(f"Token hợp lệ: {mask(tok)} — tài khoản: {name}")

    if args.check:
        log("(chế độ --check: không ghi vào cache)")
        return 0

    login(token=tok, add_to_git_credential=False)
    log("Đã lưu token vào cache HuggingFace.")
    log("  Từ giờ mọi lần tải — kể cả tiến trình con như lm_eval — đều dùng token này.")
    log("  Cảnh báo 'unauthenticated requests' sẽ biến mất.")
    log("")
    log("Kiểm lại: python scripts/00h_hf_login.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
