# Chạy trên GPU Modal

## Vì sao dùng Modal — và vì sao KHÔNG dùng cho mọi thứ

### Modal dùng cho việc gì

| Việc | Chạy ở đâu | Vì sao |
|---|---|---|
| `make modal-export` — nén model | **Modal L4** | job dài, và FP8 cần SM 8.9 |
| `make modal-eval` — lm-eval, Bảng 3 | **Modal L4** | job dài, 24GB không phải bóp batch |
| `make modal-probe` — sinh tự do cho RQ2 | **Modal L4** | job dài, sinh nhiều lượt |
| `make modal-screen` — sàng model mới | Modal *hoặc* local | nhanh, chạy đâu cũng được |
| **`make bench` — Bảng 7 (RQ4)** | **BẮT BUỘC local CPU** | đây LÀ luận điểm ứng dụng |
| **Demo rút cáp mạng** | **BẮT BUỘC local** | chung kết diễn trên máy thật |
| `make corpus/verify/amend/index` | local | không cần GPU |
| Gán nhãn taxonomy | local (việc người) | — |

| Modal giải quyết | Modal KHÔNG giải quyết |
|---|---|
| Máy local không bị chiếm GPU suốt job dài | **Bảng 7 (RQ4)** — độ trễ trên máy cấp xã, bắt buộc đo CPU thật của bạn |
| **L4 là SM 8.9 → chạy được FP8 W8A8 native** | **Demo rút cáp mạng** ở chung kết — máy local |
| VRAM 24GB, không phải bóp batch/seq | Gán nhãn taxonomy (việc người) |

Điểm số 2 là lý do đáng giá nhất. RTX 3050 là SM 8.6, dưới ngưỡng 8.9 mà FP8 W8A8
cần, nên ADR-011 phải loại FP8 khỏi thang chính. Trên L4, bậc đó **quay lại** —
thang nén từ 4 bậc thành 5, và FP8 chính là điểm giữa thú vị nhất giữa 8-bit và
4-bit.

---

## Chuẩn bị (một lần)

```bash
pip install modal
modal setup            # đăng nhập Modal
make modal-secret      # đọc HF_TOKEN từ .env -> tạo secret trên Modal
```

`make modal-secret` đọc token từ `.env` (đã gitignore), **xác thực với HF trước**,
rồi mới đẩy lên Modal.

Vì sao không gõ thẳng `modal secret create huggingface HF_TOKEN=hf_...`: lệnh đó
ghi token nguyên văn vào `~/.bash_history`. Ai đọc được lịch sử shell là đọc được
token, và nó cũng dễ lọt vào ảnh chụp màn hình.

Xác thực trước cũng tránh một kiểu hỏng tốn tiền: secret sai thì job trên Modal
chạy được vài phút rồi mới đổ với lỗi 401 khó hiểu — sau khi đã tính tiền GPU.

⚠️ Tên secret phải đúng `huggingface` — `modal_app.py` gọi theo tên này.

Kiểm lại bất cứ lúc nào:

```bash
python scripts/00i_modal_secret.py --check
```

## Token chảy qua hệ thống thế nào

```
.env (máy bạn, gitignore)
  └─ make modal-secret ──> Modal Secret "huggingface"
                             └─ Modal tiêm thành biến môi trường HF_TOKEN
                                  └─ _run() nhân bản sang HUGGING_FACE_HUB_TOKEN
                                     và HUGGINGFACEHUB_API_TOKEN
                                       └─ transformers / datasets / hub đều thấy
```

Token **không** nằm trong mã nguồn, **không** trong git, **không** trong image.
`modal_app.py` cũng dừng ngay từ đầu nếu container không thấy token, thay vì để
job chạy rồi mới đổ.

Kiểm máy Modal trước khi tốn tiền:

```bash
make modal-doctor
```

Phải thấy `SM 8.9 (Ada)` và dòng `fp8 (W8A8) ✅ CHẠY ĐƯỢC`. Nếu thấy SM 8.6 thì
Modal cấp A10G chứ không phải L4 — sửa `DEFAULT_GPU` trong `modal_app.py`.

## Vì sao chọn L4

| GPU | SM | BF16 native | FP8 native | Nhận xét |
|---|---|---|---|---|
| T4 | 7.5 | ❌ | ❌ | **tệ hơn máy local** — không thêm được gì |
| A10G | 8.6 | ✅ | ❌ | giống hệt RTX 3050, không thêm bậc nào |
| **L4** | **8.9** | ✅ | **✅** | **rẻ nhất trong nhóm có FP8** ← mặc định |
| A100 / H100 | 8.0 / 9.0 | ✅ | chỉ H100 | đắt gấp 3–6 lần; model 1–1.5B không dùng hết |

Lý do gọn: L4 là GPU **rẻ nhất có FP8**, và FP8 chính là mảnh còn thiếu của thang
nén. 24GB VRAM là phần thưởng kèm theo — không phải bóp `batch_size`/`max_seq_len`
như trên 6GB.

---

## Quy trình

```bash
DRY=1 make modal-export                        # xem lệnh, chưa chạy thật
make modal-export PREC=bf16,fp8,int8,int4_awq  # xuất trên L4, có cả FP8
make modal-eval                                # lm-eval + McNemar -> Bảng 3
make modal-pull                                # kéo kết quả về ./results
```

`make modal-pull` chạy `modal volume get viedge-results / ./results --force`.
Không có bước này thì kết quả nằm mãi trên Volume của Modal.

---

## ⚠️ BẪY KHOA HỌC: đừng trộn máy giữa các bậc

Nếu FP8 chạy trên Modal còn INT4 chạy ở nhà, hai bậc trong **cùng một đường cong
suy giảm** được đo trên hai máy khác nhau:

- kernel khác theo kiến trúc (Marlin trên Ampere vs cutlass trên Ada)
- thứ tự cộng dồn float khác → chênh nhỏ ở loglikelihood
- phiên bản thư viện trên image Modal khác máy local

Chênh lệch đó nhỏ. Nhưng **suy giảm ta đang đo cũng nhỏ**. Nếu Δ(INT8) là 2 điểm
mà sai khác do máy là 0,5 điểm, thì 25% "phát hiện" là nhiễu phần cứng.

**Quy tắc: chạy TOÀN THANG của một model trên MỘT máy.**

`scripts/05` tự đối chiếu `hardware.json` trong từng thư mục kết quả và in cảnh
báo nếu phát hiện trộn. Đừng bỏ qua cảnh báo đó.

Hai cách làm đúng:

| Cách | Khi nào |
|---|---|
| **Chạy hết trên Modal** (5 bậc, gồm FP8) | có credit — sạch nhất |
| Chạy hết ở local (4 bậc, không FP8) + ghi rõ trong quyển | hết credit |

Cách sai: bf16/int8/int4 ở local, fp8 trên Modal, rồi xếp chung một bảng mà không
ghi chú.

---

## Chi phí

`modal_app.py` có `GPU_PRICE_HINT` để ước tính trước:

```bash
modal run modal_app.py --step doctor --gpu-hours 3
```

Ước lượng thô cho hai model × 5 bậc: khoảng 2–4 giờ L4 cho export, 2–3 giờ cho
eval. **Luôn chạy `DRY=1` trước** để xem đúng số lượt sẽ chạy.

> ⚠️ **Không tạo nhiều tài khoản để lách hạn mức credit.** Vi phạm điều khoản
> dịch vụ, và rủi ro mất luôn công cụ đang phụ thuộc giữa lúc gấp. Nếu hết credit,
> lùi về chạy local 4 bậc — mất FP8 chứ không mất đề tài.

---

## Volume

| Volume | Chứa gì |
|---|---|
| `viedge-models` | model đã tải và đã nén — dùng lại giữa các lần chạy |
| `viedge-hf-cache` | cache HuggingFace, tránh tải lại vài GB mỗi lần |
| `viedge-results` | mọi thứ trong `results/`, kéo về bằng `make modal-pull` |

Xem dung lượng: `modal volume ls viedge-models`
Xoá khi cần làm lại sạch: `modal volume rm viedge-models`

---

## Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Xử lý |
|---|---|---|
| `cannot mount volume on non-empty path: "/root/viedge/results"` | `add_local_dir` copy `results/` (kể cả file `.gitkeep`) vào image, Volume không mount đè lên thư mục đã có nội dung | `ignore` phải loại **cả tên thư mục lẫn `results/**`** — đã sửa trong `modal_app.py`. Lỗi này cũng xảy ra với `models/` |
| `Secret 'huggingface' not found` | chưa tạo secret | `make modal-secret` |
| Doctor báo SM 8.6 | Modal cấp A10G, không phải L4 | đổi `DEFAULT_GPU`, hoặc chấp nhận bỏ FP8 |
| Job đổ giữa chừng vì thiếu `nvcc` | dùng image slim | image phải là `nvidia/cuda:*-devel` — đã đặt sẵn |
| Chạy xong không thấy kết quả ở máy | chưa kéo về | `make modal-pull` |
| Tải lại model mỗi lần chạy | Volume chưa gắn hoặc chưa commit | kiểm `VOLUMES` và `_commit()` trong `modal_app.py` |
