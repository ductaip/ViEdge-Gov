#!/usr/bin/env python3
"""
Kiểm mọi model trong configs/experiments.yaml: có tồn tại không, nặng bao nhiêu,
BF16 có vừa VRAM không.

VÌ SAO CẦN: `make export` tải model rồi mới biết repo 404/gated — đã dính một
lần, mất vài phút mạng và làm rối log. Kiểm trước tốn 5 giây.

Với cấu hình hiện tại (đúng 2 model đã chốt) script này chủ yếu dùng để kiểm
nhanh trước khi export, hoặc để thử ứng viên mới bằng --extra.

Dùng:
    python scripts/00f_check_models.py
    python scripts/00f_check_models.py --extra <repo_id_muon_thu>
"""
from __future__ import annotations
import argparse
from _common import ROOT, load_yaml, log

OVERHEAD_GB = 1.2
BYTES = {"bf16": 2.0, "int8": 1.0, "int4": 0.55}


def vram_now() -> float:
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / 1024**3
    except Exception:
        pass
    return 0.0


def probe(repo_id: str) -> dict:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return {"status": "⚠️ THIẾU LIB", "note": "pip install huggingface_hub"}
    from huggingface_hub.utils import (RepositoryNotFoundError, GatedRepoError,
                                       HfHubHTTPError)

    api = HfApi()
    try:
        info = api.model_info(repo_id, files_metadata=True)
    except GatedRepoError:
        return {"status": "🔒 GATED", "note": "cần chấp nhận điều khoản trên trang model"}
    except RepositoryNotFoundError:
        return {"status": "❌ KHÔNG CÓ", "note": "sai tên, đã đổi tên, hoặc private"}
    except HfHubHTTPError as e:
        return {"status": "⚠️ LỖI", "note": f"{type(e).__name__}"}
    except Exception as e:  # mạng, token hỏng...
        return {"status": "⚠️ LỖI", "note": f"{type(e).__name__}: {str(e)[:40]}"}

    weight_bytes = sum(
        (f.size or 0) for f in (info.siblings or [])
        if f.rfilename.endswith((".safetensors", ".bin"))
        and "consolidated" not in f.rfilename
    )
    gb = weight_bytes / 1024**3
    # suy ra số tham số từ dung lượng trọng số (giả định checkpoint bf16/fp16)
    params_b = gb / 2.0 if gb else 0.0
    return {
        "status": "✅ OK",
        "size_gb": round(gb, 2),
        "params_b": round(params_b, 2),
        "note": "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", nargs="*", default=[])
    args = ap.parse_args()

    cfg = load_yaml("configs/experiments.yaml")
    entries = [(m["tag"], m["hf_id"], m.get("priority", "P0")) for m in cfg["models"]]
    entries += [(e.split("/")[-1].lower(), e, "extra") for e in args.extra]

    vram = vram_now()
    log(f"VRAM phát hiện: {vram:.1f} GB" if vram else "không thấy GPU — bỏ qua cột vừa/không vừa")

    print(f"\n{'TAG':<18}{'HF REPO':<32}{'ƯU TIÊN':<9}{'TRẠNG THÁI':<14}{'GB':>6}{'~B':>6}  VỪA VRAM?")
    print("-" * 108)
    usable_p0 = []
    for tag, repo, pri in entries:
        r = probe(repo)
        fit = ""
        if r["status"] == "✅ OK" and vram:
            need_bf16 = r["params_b"] * BYTES["bf16"] + OVERHEAD_GB
            need_int4 = r["params_b"] * BYTES["int4"] + OVERHEAD_GB
            fit = ("bf16 ✅" if need_bf16 <= vram else
                   f"bf16 ❌ ({need_bf16:.1f}GB) · int4 {'✅' if need_int4 <= vram else '❌'}")
            if need_bf16 <= vram and pri == "P0":
                usable_p0.append(tag)
        print(f"{tag:<18}{repo:<32}{pri:<9}{r['status']:<14}"
              f"{r.get('size_gb', '—'):>6}{r.get('params_b', '—'):>6}  {fit or r['note']}")

    print()
    if len(usable_p0) < 2:
        log(f"CHỈ CÓ {len(usable_p0)} model P0 chạy được BF16 trên máy này: {usable_p0}")
        log("P0 cần >= 2 model để đường cong suy giảm có ý nghĩa so sánh.")
        log("Tìm model thay thế: HF -> Models -> lọc theo 'text-generation', sắp xếp")
        log("theo Trending, kích thước <= 2B. Kiểm bằng: --extra <repo_id>")
        log("Tiêu chí chọn: (1) có tiếng Việt trong dữ liệu huấn luyện, (2) <= 2B để")
        log("BF16 vừa 6GB, (3) không gated, (4) có safetensors.")
    else:
        log(f"{len(usable_p0)} model P0 sẵn sàng: {usable_p0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
