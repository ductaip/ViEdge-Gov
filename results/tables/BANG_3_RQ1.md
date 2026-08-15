## Bảng 3 (RQ1). Suy giảm chất lượng tiếng Việt theo mức nén

VMLU, n = 1047 câu có đáp án, 58 môn. Mốc tham chiếu BF16. Mức đoán mò thực tế 0.2532.
Ngưỡng sàn ở n=1047: accuracy dưới 27.5% không phân biệt được với đoán mò.

| Mô hình | Mức nén | Accuracy | Δ | KTC 95% | đúng→sai | sai→đúng | p (McNemar) | p hiệu chỉnh | Kết luận |
|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct | **bf16** | 49.47% | — | — | — | — | — | — | *tham chiếu* |
| Qwen2.5-1.5B-Instruct | fp8 | 51.29% | +1.82% | [+0.5%, +3.2%] | 19 | 38 | 0.01712 | 0.0856 | không sống sót hiệu chỉnh |
| Qwen2.5-1.5B-Instruct | int8 | 48.90% | -0.57% | [-2.3%, +1.1%] | 48 | 42 | 0.5982 | 1 | không có ý nghĩa |
| Qwen2.5-1.5B-Instruct | int4 | 46.13% | -3.34% | [-6.0%, -0.7%] | 120 | 85 | 0.01757 | 0.0856 | không sống sót hiệu chỉnh |
| gemma-3-1b-it | **bf16** | 40.11% | — | — | — | — | — | — | *tham chiếu* |
| gemma-3-1b-it | fp8 | 40.02% | -0.09% | [-2.0%, +1.8%] | 53 | 52 | 1 | 1 | không có ý nghĩa |
| gemma-3-1b-it | int8 | 37.92% | -2.19% | [-4.4%, +0.0%] | 81 | 58 | 0.06204 | 0.1861 | không có ý nghĩa |
| gemma-3-1b-it | int4 | 31.71% | -8.40% | [-11.8%, -5.0%] | 204 | 116 | 1e-06 | 6e-06 | **có ý nghĩa** |

**Cách đọc bảng.** Cột *p hiệu chỉnh* dùng Holm-Bonferroni cho 6 kiểm định trên cùng bộ dữ liệu. Không hiệu chỉnh thì xác suất có ít nhất một dương tính giả là 26.5%. Chỉ tuyên bố chắc chắn với dòng sống sót hiệu chỉnh.

### Ba kết luận

**1. INT4 làm giảm chất lượng, và model nhỏ hơn chịu thiệt nặng hơn.**  
Gemma-1B mất 8,40 điểm (p hiệu chỉnh 6e-06) — sống sót mọi mức hiệu chỉnh. Qwen-1,5B mất 3,34 điểm cùng hướng. Hai kiến trúc độc lập cùng cho kết quả cùng chiều ở cùng bậc nén là bằng chứng hội tụ, mạnh hơn từng p-value riêng lẻ.

**2. INT8 an toàn ở cả hai mô hình.**  
Qwen −0,57 điểm (p=0,60), Gemma −2,19 điểm (p=0,062). Không mô hình nào cho suy giảm có ý nghĩa. Đây là khuyến nghị triển khai trực tiếp cho Chương 5.

**3. FP8 KHÔNG làm giảm chất lượng — nhưng không tuyên bố là cải thiện.**  
Qwen +1,82 điểm (p thô 0,017) nhưng **mất ý nghĩa sau hiệu chỉnh** (p=0,086), và Gemma không xác nhận (−0,09 điểm, p=1,0). Kết quả ngược hướng giả thuyết mà chỉ một mô hình cho thấy, lại không sống sót hiệu chỉnh, nhiều khả năng là nhiễu. Kết luận an toàn: **FP8 không gây suy giảm đo được**.

### Hạn chế

- Hai mô hình khác *cả kiến trúc lẫn kích thước* (1,5B vs 1,0B); không quy toàn bộ chênh lệch cho kiến trúc.
- Lượng tử hoá dùng RTN data-free, **không** dùng dữ liệu hiệu chuẩn.
- VMLU đo kiến thức tổng quát bằng trắc nghiệm; không đo trực tiếp chất lượng sinh văn bản tiếng Việt — đó là việc của RQ2.