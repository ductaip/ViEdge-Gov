# Cài đặt & môi trường

## Khởi động nhanh (5 phút, chưa cần GPU)

```bash
pip install -r requirements.txt
make smoke        # phải XANH trước khi làm gì khác
make test         # 45 test
```

`make smoke` chạy toàn pipeline trên dữ liệu fixture: bóc văn bản → dựng từ vựng
→ index trích dẫn → 6 detector → truy hồi lai → trợ lý + cửa chặn → lấy mẫu +
đồng thuận. Đỏ ở đâu thì sửa ở đó trước khi đốt giờ GPU.

---

## Môi trường đánh giá (Kaggle T4 ×2)

**Cấu hình đã chạy thông — đừng đổi tuỳ ý:**

```bash
pip install lm-eval==0.4.12
```

| Cạm bẫy | Hậu quả | Xử lý |
|---|---|---|
| `lm-eval==0.4.9` | lỗi `AutoModelForVision2Seq` | dùng 0.4.12 |
| ghim `transformers==4.53.2` cùng env với vllm | xung đột phụ thuộc | **không ghim** |
| tách env cho eval và serve | — | nên tách, tránh vòng xung đột |

Kaggle: bật GPU T4 ×2, `PYTHONPATH=/kaggle/working/viedge-gov/src`.
Xem `notebooks/kaggle_t4_eval.ipynb`.

---

## Môi trường Modal (job ngắn, L4)

Image **phải** là `nvidia/cuda` bản devel — cần `nvcc` cho flashinfer JIT.
`debian_slim` thiếu nvcc và sẽ vỡ.

```python
image = modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.11")
```

> ⚠️ **Không tạo nhiều tài khoản để lách hạn mức credit.** Vi phạm ToS, rủi ro
> ban toàn bộ — mất luôn công cụ đang phụ thuộc cho việc khác. Đề tài này gần
> như không cần Modal: T4 ×2 đủ cho toàn bộ P0–P2.

---

## Nén mô hình

```bash
pip install llmcompressor        # FP8_DYNAMIC / W8A8 / W4A16
pip install autoawq              # đường AWQ thay thế
```

`DRY=1 make export` để in lệnh mà không chạy — **review lệnh trước khi đốt GPU**.

**Không dùng bitsandbytes NF4 làm đường 4-bit chính.** Đã đo: TPOT 58,3ms vs
~38ms của FP8 (chậm ~50%, dequant ăn hết tiết kiệm băng thông) và văn bản ngữ
cảnh dài vỡ nghĩa. Giữ **một** lượt bnb làm đối chứng (ADR-005).

---

## Đường CPU (GGUF) — dùng cho demo & Bảng 7

```bash
pip install llama-cpp-python

# convert + quantize
git clone https://github.com/ggerganov/llama.cpp && cd llama.cpp
python convert_hf_to_gguf.py <model_dir> --outfile model-f16.gguf --outtype f16
cmake -B build && cmake --build build --config Release -j
./build/bin/llama-quantize model-f16.gguf model-q4_k_m.gguf Q4_K_M
```

Đo hiệu năng **trên đúng máy sẽ demo**:

```bash
make bench                                    # chế độ giả lập, kiểm script
python scripts/11_bench_cpu.py --gguf model-q4_k_m.gguf --tag qwen2b-q4km
```

Script in cấu hình máy — **chép đúng dòng đó vào phần Thực nghiệm của quyển**.

---

## Retrieval

```bash
pip install sentence-transformers
```

Encoder trong `configs/retrieval.yaml`. Nếu encoder chính lỗi, `scripts/09` báo
và gợi ý fallback; BM25 vẫn hoạt động độc lập nên pipeline không chết.

Với kho ~400 điều, **không cần FAISS** — cosine vét cạn đủ nhanh. Đừng thêm
phức tạp không cần thiết chỉ vì nghe chuyên nghiệp.

---

## Thứ tự chạy đầy đủ

```bash
make smoke                    # 0. kiểm repo
make corpus                   # 1. văn bản -> điều/khoản/điểm
make sample                   # 2. VMLU lấy mẫu
DRY=1 make export && make export   # 3. xuất các mức nén
make eval                     # 4. VMLU -> Bảng 3 (RQ1)
make probe                    # 5. sinh tự do -> hàng đợi gán nhãn
#    ... gán nhãn thủ công (scripts/07, hai người) ...
make agreement                # 6. AC1 + hiệu chuẩn -> Bảng 4, 5 (RQ2)
make index && make rag        # 7. truy hồi -> Bảng 6 (RQ3)
make bench                    # 8. CPU -> Bảng 7 (RQ4)
make tables                   # 9. gom mọi bảng -> results/tables/REPORT_TABLES.md
make demo                     # 10. demo offline
```

`logs/runlog.jsonl` ghi mọi lần chạy thật. Cuối tuần copy sang `WEEKLOG.md`.
