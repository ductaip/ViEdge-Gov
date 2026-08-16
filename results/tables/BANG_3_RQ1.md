## Bảng 3 (RQ1). Suy giảm chất lượng tiếng Việt theo mức nén

VMLU, n = 1047 câu có đáp án, 58 môn. Mốc tham chiếu BF16. Mức đoán mò thực tế 0.2532.
Ngưỡng sàn ở n=1047: accuracy dưới 27.5% không phân biệt được với đoán mò.

| Mô hình | Mức nén | Accuracy | Δ | KTC 95% | đúng→sai | sai→đúng | p (McNemar) | p hiệu chỉnh | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct | **bf16** | 49.47% | — | — | — | — | — | — | *tham chiếu* |
| Qwen2.5-1.5B-Instruct | fp8 | 51.29% | +1.82% | [+0.5%, +3.2%] | 19 | 38 | 0.01712 | 0.1027 | không sống sót hiệu chỉnh |
| Qwen2.5-1.5B-Instruct | int8 | 48.90% | -0.57% | [-2.3%, +1.1%] | 48 | 42 | 0.5982 | 1 | không có ý nghĩa |
| Qwen2.5-1.5B-Instruct | int4_awq | 46.13% | -3.34% | [-6.0%, -0.7%] | 120 | 85 | 0.01757 | 0.1027 | không sống sót hiệu chỉnh |
| Qwen2.5-1.5B-Instruct | **gguf_q4_k_m** | 47.09% | -2.39% | [-5.4%, +0.5%] | 132 | 107 | 0.1206 | 0.3617 | không có ý nghĩa |
| gemma-3-1b-it | **bf16** | 40.11% | — | — | — | — | — | — | *tham chiếu* |
| gemma-3-1b-it | fp8 | 40.02% | -0.09% | [-2.0%, +1.8%] | 53 | 52 | 1 | 1 | không có ý nghĩa |
| gemma-3-1b-it | int8 | 37.92% | -2.19% | [-4.4%, +0.0%] | 81 | 58 | 0.06204 | 0.2482 | không có ý nghĩa |
| gemma-3-1b-it | int4_awq | 31.71% | -8.40% | [-11.8%, -5.0%] | 204 | 116 | 1e-06 | 8e-06 | **có ý nghĩa** |
| gemma-3-1b-it | **gguf_q4_k_m** | 36.49% | -3.63% | [-6.1%, -1.2%] | 108 | 70 | 0.00555 | 0.0389 | **có ý nghĩa** |

**Cách đọc bảng.** Cột *p hiệu chỉnh* dùng Holm-Bonferroni cho **8** kiểm định trên cùng bộ dữ liệu (thêm GGUF Q4_K_M so với bản trước — 6 kiểm định). Không hiệu chỉnh thì xác suất có ít nhất một dương tính giả tăng theo số kiểm định. Chỉ tuyên bố chắc chắn với dòng sống sót hiệu chỉnh.

### Bốn kết luận

**1. INT4 làm giảm chất lượng, và model nhỏ hơn chịu thiệt nặng hơn.**  
Gemma-1B mất 8,40 điểm (p hiệu chỉnh 6e-06) — sống sót mọi mức hiệu chỉnh. Qwen-1,5B mất 3,34 điểm cùng hướng. Hai kiến trúc độc lập cùng cho kết quả cùng chiều ở cùng bậc nén là bằng chứng hội tụ, mạnh hơn từng p-value riêng lẻ.

**2. INT8 an toàn ở cả hai mô hình.**  
Qwen −0,57 điểm (p=0,60), Gemma −2,19 điểm (p=0,062). Không mô hình nào cho suy giảm có ý nghĩa. Đây là khuyến nghị triển khai trực tiếp cho Chương 5.

**3. FP8 KHÔNG làm giảm chất lượng — nhưng không tuyên bố là cải thiện.**  
Qwen +1,82 điểm (p thô 0,017) nhưng **mất ý nghĩa sau hiệu chỉnh** (p=0,103), và Gemma không xác nhận (−0,09 điểm, p=1,0). Kết quả ngược hướng giả thuyết mà chỉ một mô hình cho thấy, lại không sống sót hiệu chỉnh, nhiều khả năng là nhiễu. Kết luận an toàn: **FP8 không gây suy giảm đo được**.

**4. GGUF Q4_K_M (cấu hình khuyến nghị triển khai CPU) — suy giảm thật, và không đều giữa hai mô hình.**  
Gemma-1B mất 3,63 điểm (p hiệu chỉnh 0,039) — **sống sót hiệu chỉnh**, dù nhẹ hơn nhiều so với INT4_AWQ cùng model (−8,40 điểm). Qwen-1,5B mất 2,39 điểm nhưng **không có ý nghĩa** kể cả trước hiệu chỉnh (p=0,12). Hai điều rút ra: (i) GGUF Q4_K_M ổn định hơn INT4_AWQ ở cùng model — hợp lý vì K-quant giữ độ chính xác cao hơn ở các tensor nhạy cảm (attention, embedding) thay vì lượng tử đều; (ii) mức chịu đựng vẫn khác nhau giữa hai kiến trúc, nên khuyến nghị triển khai (Chương 5) không thể dùng chung một ngưỡng cho mọi model — phải kiểm từng model trước khi chốt cấu hình.

### Hạn chế

- Hai mô hình khác *cả kiến trúc lẫn kích thước* (1,5B vs 1,0B); không quy toàn bộ chênh lệch cho kiến trúc.
- Lượng tử hoá dùng RTN data-free, **không** dùng dữ liệu hiệu chuẩn.
- VMLU đo kiến thức tổng quát bằng trắc nghiệm; không đo trực tiếp chất lượng sinh văn bản tiếng Việt — đó là việc của RQ2.

**Ghi chú phương pháp.**
 
(a) Cả 4 bậc (BF16, FP8, INT8, INT4) của cả hai mô hình đều đo trên **cùng
một máy — Modal L4 (SM 8.9, Ada Lovelace)**, xác nhận bằng `hardware.json`
ghi kèm mỗi kết quả và `viedge.provenance.check_consistency()` (không phát
hiện trộn máy). Không có bậc nào đo trên RTX 3050 (SM 8.6, Ampere) — máy đó
chỉ dùng cho bậc GGUF (mục d), đúng vai trò đại diện triển khai CPU. Xem
ADR-011 và ADR-020.
 
(b) INT4_AWQ dùng RTN data-free — không có calibration set. Kết luận
«INT4 hại tiếng Việt» tương ứng với cách nén PHỔ THÔNG nhất (không cần
dữ liệu riêng, ai cũng có thể chạy). Hướng mở GPTQ + calibration tiếng
Việt xem Chương 6 và ADR-021.
 
(c) BF16 accuracy 49.47% trên VMLU 1 047 câu chệch nhẹ so với sàng model
n = 200 (52.0%) do cỡ mẫu và tập con VMLU khác nhau; khoảng tin cậy 95%
của hai ước lượng chồng nhau.
 
(d) Bậc GGUF Q4_K_M đo bằng `llama-cpp-python` đọc trực tiếp logits (KHÔNG qua
`lm_eval --model gguf`/llama-server — đã thử, không tương thích: backend đó
viết cho schema logprobs cũ của OpenAI Completions API mà `llama-server` bản
hiện tại không còn trả về khi echo). Cùng prompt template và cùng 1047 câu với
các bậc khác (`configs/lm_eval_tasks/utils.py`), nên McNemar so sánh hợp lệ.
Xem `scripts/05b_run_eval_gguf.py`.
 
(e) Bậc BF16/FP8/INT8/INT4_AWQ mỗi bậc chạy 2 lần cùng seed = 0, cùng accuracy
— kết quả tái lập. Bậc GGUF Q4_K_M mới chạy **1 lần** (chưa kiểm tái lập) —
nếu còn thời gian, chạy lại 1 lần nữa trước khi đưa vào quyển chính thức.