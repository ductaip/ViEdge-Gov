"""
Chạy ViEdge-Gov trên GPU của Modal.

NGUYÊN TẮC THIẾT KẾ QUAN TRỌNG NHẤT: **KHÔNG viết lại logic**.
File này chỉ đóng gói môi trường rồi gọi ĐÚNG những script trong scripts/ mà bạn
vẫn chạy ở local. Nếu Modal có bản logic riêng, hai bản sẽ phân kỳ và có ngày
Bảng 3 chạy trên Modal khác Bảng 3 chạy ở nhà — mà không ai biết bản nào đúng.

BA THỨ MODAL GIẢI QUYẾT:
  1. Máy local không bị chiếm GPU suốt job dài
  2. L4 là compute capability 8.9 -> chạy được **FP8 W8A8 NATIVE**, bậc mà RTX 3050
     (SM 8.6) không chạy được (ADR-011). Thêm một bậc THẬT vào thang nén.
  3. VRAM 24GB -> không phải bóp batch_size/max_seq_len như trên 6GB

MỘT THỨ MODAL KHÔNG GIẢI QUYẾT:
  Bảng 7 (RQ4 — độ trễ trên máy cấp xã) BẮT BUỘC đo trên CPU thật của bạn.
  Đo trên L4 rồi báo cáo "chạy được ở xã" thì luận điểm ứng dụng mất căn cứ.
  Demo rút cáp mạng ở chung kết cũng vậy: máy local, không phải Modal.

CẢNH BÁO VỀ TRỘN MÁY (đọc kỹ, đây là bẫy khoa học):
  Nếu FP8 chạy trên Modal còn INT4 chạy ở nhà, hai bậc trong CÙNG đường cong được
  đo trên hai máy khác nhau — kernel khác, thứ tự cộng float khác, phiên bản thư
  viện khác. Chênh lệch nhỏ, nhưng suy giảm ta đo cũng nhỏ.
  => Chạy TOÀN THANG của một model trên MỘT máy. `scripts/05` tự cảnh báo nếu
     phát hiện trộn (viedge.provenance.check_consistency). Xem ADR-020.

CHUẨN BỊ MỘT LẦN:
    pip install modal
    modal setup
    modal secret create huggingface HF_TOKEN=hf_...
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import modal

APP_NAME = "viedge-gov"
REPO = "/root/viedge"

# Giá tham khảo (USD/giờ) chỉ để CHẶN việc lỡ tay đốt hết credit.
# Kiểm lại tại modal.com/pricing — giá thay đổi, con số ở đây có thể lỗi thời.
GPU_PRICE_HINT = {
    "T4": 0.59,        # SM 7.5 — KHÔNG BF16 native, KHÔNG FP8
    "L4": 0.80,        # SM 8.9 — BF16 + FP8 ✅   <- mặc định
    "A10G": 1.10,      # SM 8.6 — BF16, KHÔNG FP8
    "A100-40GB": 2.78,
    "H100": 4.56,      # SM 9.0
}
# VÌ SAO CHỌN L4 LÀM MẶC ĐỊNH:
#   * SM 8.9 -> chạy FP8 W8A8 NATIVE. Đây là lý do chính: RTX 3050 (SM 8.6) không
#     chạy được bậc này, nên Modal bổ sung đúng mảnh còn thiếu của thang nén.
#   * 24GB VRAM -> không phải bóp batch_size/max_seq_len như trên 6GB.
#   * Là GPU RẺ NHẤT trong danh sách có FP8. A100/H100 cũng có FP8 nhưng đắt gấp
#     3-6 lần, mà model 1-1.5B không dùng hết năng lực của chúng -> trả tiền cho
#     phần không dùng.
#   * KHÔNG chọn T4: SM 7.5, không có BF16 native lẫn FP8 — tệ hơn cả máy local.
#   * KHÔNG chọn A10G: SM 8.6, giống hệt máy local, không thêm được bậc nào.
DEFAULT_GPU = "L4"

# Image: nvidia/cuda bản DEVEL, KHÔNG dùng slim.
# Bài học: bản slim thiếu nvcc, mọi thứ cần biên dịch JIT (flashinfer, một số
# kernel quantization) sẽ đổ GIỮA CHỪNG job — sau khi đã tính tiền.
image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git", "build-essential", "cmake", "curl")
    .pip_install(
        "torch",
        "transformers>=4.55",
        "accelerate",
        "datasets",
        "huggingface_hub",
        "hf_transfer",
        "llmcompressor",
        "lm-eval==0.4.12",
        "sentencepiece>=0.2",
        "protobuf>=4.25",
        "pyyaml",
        "numpy",
        "tqdm",
    )
    .env({"TOKENIZERS_PARALLELISM": "false", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
    # Mã nguồn + dữ liệu nhỏ. Model/kết quả nằm trên Volume, KHÔNG nhét vào image.
    #
    # ⚠️ MỌI ĐIỂM MOUNT VOLUME PHẢI RỖNG TRONG IMAGE.
    # Modal từ chối mount lên thư mục đã có nội dung:
    #     cannot mount volume on non-empty path: "/root/viedge/results"
    # Repo local có results/{tables,bench,eval,taxonomy}/.gitkeep — chỉ cần một
    # file .gitkeep lọt vào image là hỏng. Vì vậy phải loại TOÀN BỘ `results`
    # và `models`, không chỉ loại các thư mục con.
    # Ghi CẢ tên thư mục lẫn mẫu `/**` để chắc chắn thư mục rỗng cũng không được tạo.
    .add_local_dir(
        Path(__file__).parent,
        remote_path=REPO,
        ignore=[
            # điểm mount Volume — bắt buộc rỗng
            "models", "models/**",
            "results", "results/**",
            # rác không cần đưa lên
            ".git", ".git/**", "**/__pycache__", "**/__pycache__/**", "**/*.pyc",
            ".pytest_cache", ".pytest_cache/**",
            ".venv", ".venv/**", "venv", "venv/**",
            # nguồn nặng, bản .txt đã bóc rồi nên không cần bản gốc
            "data/raw/pdf", "data/raw/pdf/**",
            "data/raw/doc", "data/raw/doc/**",
            "**/*.gguf", "**/*.safetensors", "**/*.bin",
            # bí mật: KHÔNG bao giờ đưa lên. Token đi qua Modal Secret.
            ".env",
        ],
    )
)

app = modal.App(APP_NAME, image=image)

# Volume: model đã tải/đã nén và kết quả sống qua nhiều lần chạy.
# Không có nó thì mỗi lần chạy tải lại vài GB và nén lại từ đầu — vừa chậm vừa
# tốn tiền cho công việc đã làm rồi.
models_vol = modal.Volume.from_name("viedge-models", create_if_missing=True)
hf_cache_vol = modal.Volume.from_name("viedge-hf-cache", create_if_missing=True)
results_vol = modal.Volume.from_name("viedge-results", create_if_missing=True)

VOLUMES = {
    f"{REPO}/models": models_vol,
    f"{REPO}/results": results_vol,
    "/root/.cache/huggingface": hf_cache_vol,
}

# Secret chứa HF_TOKEN. Tạo bằng: make modal-secret  (đọc từ .env, không qua shell history)
# Modal tiêm nó thành BIẾN MÔI TRƯỜNG trong container; `_run()` nhân bản sang cả
# ba tên biến mà các thư viện HF đọc, nên transformers/datasets/hub đều thấy.
SECRETS = [modal.Secret.from_name("huggingface")]
COMMON = dict(volumes=VOLUMES, secrets=SECRETS)


def _require_token(env: dict) -> None:
    """Dừng SỚM nếu thiếu token, thay vì đổ giữa chừng job đã tính tiền GPU."""
    if not env.get("HF_TOKEN"):
        raise RuntimeError(
            "Thiếu HF_TOKEN trong container Modal.\n"
            "  Tạo secret: make modal-secret   (đọc token từ .env)\n"
            "  Kiểm lại  : python scripts/00i_modal_secret.py --check\n"
            "  Tên secret phải đúng 'huggingface' — modal_app.py gọi theo tên này."
        )


def _run(script: str, args: list[str] | None = None, env_extra: dict | None = None) -> int:
    """Gọi một script trong scripts/ y hệt như chạy ở local."""
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO}/src"
    _require_token(env)
    tok = env["HF_TOKEN"]
    for k in ("HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN"):
        env[k] = tok
    env.update(env_extra or {})
    cmd = [sys.executable, f"{REPO}/scripts/{script}", *(args or [])]
    print(f"[modal] {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=REPO, env=env)


def _commit():
    models_vol.commit()
    results_vol.commit()


@app.function(gpu=DEFAULT_GPU, timeout=60 * 60, **COMMON)
def doctor() -> int:
    """Xác nhận máy Modal: phải thấy SM >= 8.9 thì FP8 mới chạy native."""
    return _run("00e_doctor.py")


@app.function(gpu=DEFAULT_GPU, timeout=60 * 60 * 4, **COMMON)
def export(precisions: str = "", dry: bool = False) -> int:
    """Xuất model theo các bậc nén. Kết quả nằm trên Volume, dùng lại lần sau.

    precisions: chuỗi ngăn cách dấu phẩy để ghi đè config, vd. "bf16,fp8,int8,int4_awq".
    """
    extra = {}
    if dry:
        extra["DRY"] = "1"
    if precisions:
        extra["VIEDGE_PRECISIONS"] = precisions
    rc = _run("04_export_quant.py", env_extra=extra)
    _commit()
    return rc


@app.function(gpu=DEFAULT_GPU, timeout=60 * 60 * 6, **COMMON)
def evaluate() -> int:
    """lm-eval + McNemar + kiểm sàn -> Bảng 3."""
    rc = _run("05_run_eval.py")
    _commit()
    return rc


@app.function(gpu=DEFAULT_GPU, timeout=60 * 60 * 2, **COMMON)
def screen(n: int = 200, extra: str = "") -> int:
    """Sàng trần tiếng Việt của model ứng viên."""
    args = ["--n", str(n)]
    if extra:
        args += ["--extra", *extra.split(",")]
    rc = _run("00g_screen_models.py", args)
    _commit()
    return rc


@app.function(gpu=DEFAULT_GPU, timeout=60 * 60 * 3, **COMMON)
def probe() -> int:
    """Sinh tự do trên mọi bậc nén -> đầu vào cho taxonomy lỗi (RQ2)."""
    rc = _run("06a_generate.py")            # Bước 1: sinh output
    if rc != 0:
        return rc
    rc = _run("06_run_error_probe.py")      # Bước 2: chạy detector
    _commit()
    return rc


def _check_mount_points() -> None:
    """Cảnh báo TRƯỚC khi build image nếu điểm mount Volume sẽ không rỗng.

    Modal từ chối mount Volume lên thư mục đã có nội dung. Lỗi hiện ra sau khi
    build image xong (mất vài phút) và thông báo chỉ nói tên thư mục, không nói
    file nào gây ra. Kiểm ở đây thì biết ngay và biết chính xác phải bỏ gì.
    """
    local = Path(__file__).parent
    for name in ("models", "results"):
        d = local / name
        if not d.exists():
            continue
        # Mọi thứ dưới đây phải nằm trong `ignore` của add_local_dir
        files = [p for p in d.rglob("*") if p.is_file()]
        if files:
            print(f"[modal] lưu ý: {name}/ có {len(files)} file ở local "
                  f"(vd. {files[0].relative_to(local)}) — đã loại khỏi image; "
                  f"chúng sống trên Volume '{'viedge-' + name}'.")


@app.local_entrypoint()
def main(step: str = "doctor", n: int = 200, precisions: str = "",
         extra: str = "", dry: bool = False, gpu_hours: float = 0.0):
    """Điểm vào từ máy local.

        modal run modal_app.py --step doctor
        modal run modal_app.py --step export --dry
        modal run modal_app.py --step export --precisions bf16,fp8,int8,int4_awq
        modal run modal_app.py --step evaluate

    Lấy kết quả về máy (chạy ở terminal local, KHÔNG qua modal run):
        modal volume get viedge-results / ./results --force
    """
    _check_mount_points()

    # Kiểm toàn vẹn repo TRƯỚC khi build image và cấp GPU. Thiếu một module thì
    # job đổ ở dòng `import` — sau khi đã tính tiền. Kiểm ở local mất 2 giây.
    import subprocess as _sp
    _local = Path(__file__).parent
    _rc = _sp.call([sys.executable, str(_local / "scripts" / "00j_check_repo.py")],
                   cwd=str(_local))
    if _rc != 0:
        raise SystemExit("[modal] repo chưa đầy đủ — xem lỗi ở trên. Không gửi job.")

    if gpu_hours:
        est = gpu_hours * GPU_PRICE_HINT[DEFAULT_GPU]
        print(f"[ước tính] {gpu_hours:.1f} giờ {DEFAULT_GPU} ≈ ${est:.2f}")
        print("           Kiểm credit còn lại tại modal.com TRƯỚC khi chạy.")

    fns = {"doctor": doctor, "export": export, "evaluate": evaluate,
           "screen": screen, "probe": probe}
    fn = fns.get(step)
    if fn is None:
        raise SystemExit(f"step không hợp lệ: {step}. Chọn: {', '.join(fns)}")

    if step == "export":
        rc = fn.remote(precisions=precisions, dry=dry)
    elif step == "screen":
        rc = fn.remote(n=n, extra=extra)
    else:
        rc = fn.remote()

    print(f"[modal] {step} kết thúc, mã thoát {rc}")
    if step in ("evaluate", "probe", "screen") and rc == 0:
        print("[modal] Lấy kết quả về máy:")
        print("        modal volume get viedge-results / ./results --force")
