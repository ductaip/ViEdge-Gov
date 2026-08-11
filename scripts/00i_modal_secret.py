#!/usr/bin/env python3
"""
Tạo/cập nhật Modal secret `huggingface` từ file .env — token KHÔNG đi qua terminal.

VÌ SAO KHÔNG DÙNG THẲNG `modal secret create huggingface HF_TOKEN=hf_...`:
Lệnh đó ghi token nguyên văn vào ~/.bash_history (hoặc .zsh_history). Ai đọc được
lịch sử shell là đọc được token. Cũng dễ lọt vào ảnh chụp màn hình khi chia sẻ
màn hình hoặc dán log lên chat.

Script này đọc token từ .env (đã gitignore), xác thực với HF trước, rồi gọi API
của Modal để tạo secret. Token không xuất hiện ở đâu ngoài .env và Modal.

    python scripts/00i_modal_secret.py
    python scripts/00i_modal_secret.py --check     # chỉ kiểm, không tạo
"""
from __future__ import annotations
import argparse, subprocess, sys
from _common import ROOT, log, rel

SECRET_NAME = "huggingface"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--name", default=SECRET_NAME)
    args = ap.parse_args()

    from viedge.env import hf_token, mask

    tok = hf_token()
    if not tok:
        log("KHÔNG tìm thấy token trong .env hoặc môi trường.")
        log(f"  1. cp .env.example .env      (tại {rel(ROOT)})")
        log("  2. mở .env, điền HF_TOKEN=hf_...")
        log("  3. chạy lại lệnh này")
        return 1
    log(f"token đọc được: {mask(tok)}")

    # Xác thực TRƯỚC khi đẩy lên Modal. Secret sai thì job trên Modal sẽ đổ giữa
    # chừng với lỗi 401 khó hiểu — sau khi đã tính tiền GPU.
    try:
        from huggingface_hub import HfApi
        who = HfApi().whoami(token=tok)
        log(f"token hợp lệ — tài khoản: {who.get('name') or who.get('fullname')}")
    except ImportError:
        log("(chưa có huggingface_hub, bỏ qua bước xác thực)")
    except Exception as e:
        log(f"Token KHÔNG hợp lệ: {type(e).__name__}: {str(e)[:80]}")
        log("  Tạo token mới (quyền Read) tại https://huggingface.co/settings/tokens")
        return 1

    try:
        import modal  # noqa: F401
    except ImportError:
        log("Chưa cài Modal. Chạy: pip install modal"); return 1

    if args.check:
        try:
            out = subprocess.run(["modal", "secret", "list"], capture_output=True,
                                 text=True, timeout=60)
            has = args.name in (out.stdout or "")
            log(f"secret '{args.name}' trên Modal: {'✅ đã có' if has else '❌ chưa có'}")
            return 0 if has else 1
        except Exception as e:
            log(f"không kiểm được: {type(e).__name__}"); return 1

    # `modal secret create` nhận giá trị qua tham số dòng lệnh, nên ta gọi bằng
    # subprocess với danh sách args (KHÔNG qua shell) — chuỗi không đi qua shell
    # thì không vào history.
    cmd = ["modal", "secret", "create", args.name, f"HF_TOKEN={tok}", "--force"]
    log(f"tạo secret '{args.name}' trên Modal ...")
    rc = subprocess.call(cmd)
    if rc != 0:
        log("Thất bại. Kiểm đã `modal setup` chưa.")
        return rc
    log(f"✅ secret '{args.name}' sẵn sàng. modal_app.py sẽ tự nạp HF_TOKEN vào mọi job.")
    log("   Kiểm lại: python scripts/00i_modal_secret.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
