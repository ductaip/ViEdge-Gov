# 4.2 (RQ2) Lỗi hỏng ở đâu — bản nháp thảo luận Bảng 4, 5

> Bản nháp, viết lại theo văn phong quyển trước khi dùng chính thức. Số liệu lấy trực tiếp từ
> `results/tables/agreement_per_label.json` và `results/tables/detector_calibration.json`
> (201 mẫu, 2 người gán độc lập, `--hide-auto`).

## Bảng 4 — Đồng thuận gán nhãn theo mã lỗi

| Mã | Prevalence | Đồng thuận thô | AC1 | Kappa | Diễn giải |
|---|---|---|---|---|---|
| E1 | 18,9% | 98,5% | **0,979** [0,951–1,0] | 0,950 | cao |
| E2 | 23,9% | 76,1% | **0,698** [0,608–0,786] | 0,000 | khá |
| E3 | 8,5% | 94,5% | **0,939** [0,897–0,973] | 0,496 | cao |
| E4 | 0,5% | 100% | 1,000 | 1,000 | cao (n quá nhỏ, 1/201 mẫu — không kết luận xu hướng) |
| E5 | 10,0% | 90,0% | **0,890** [0,833–0,937] | −0,039 | cao |
| E6 | 73,6% | 82,6% | **0,680** [0,58–0,78] | 0,619 | khá |

**Đọc bảng.** 4/6 mã đạt mức "cao" (AC1 ≥ 0,80); E2 và E6 ở mức "khá" (0,60–0,80) — dưới mục tiêu ban đầu (0,70) nhưng trên ngưỡng tối thiểu chấp nhận được (0,60), nên giữ nguyên kết quả, không gán lại.

**Nghịch lý kappa ở E2 và E5** — đúng như ADR-004 dự đoán trước khi gán nhãn: E5 có kappa **âm** (−0,039) trong khi AC1 vẫn ở mức cao (0,890) trên cùng dữ liệu; E2 kappa bằng 0 trong khi hai người đồng thuận thô tới 76,1%. Cả hai đều là hệ quả của prevalence lệch (E5 chỉ 10%, E2 23,9%) — kappa sụp về gần 0 không phải vì hai người bất đồng nhiều, mà vì công thức kappa trừ đi một mức "đồng thuận ngẫu nhiên" bị thổi phồng khi một nhãn hiếm. Đây là bằng chứng thực nghiệm thứ hai (sau kiểm định giả lập ở `tests/test_agreement.py`) cho quyết định dùng AC1 làm chỉ số chính.

## Bảng 5 — Hiệu chuẩn detector tự động so với nhãn người

| Mã | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| E1 | 0 | 0 | 38 | — | **0,0** |
| E2 | 48 | 0 | 0 | **1,0** | **1,0** |
| E3 | 8 | 52 | 9 | 0,133 | 0,471 |
| E4 | 0 | 0 | 1 | — | 0,0 |
| E5 | 2 | 29 | 18 | 0,065 | 0,1 |
| E6 | 72 | 0 | 76 | **1,0** | 0,486 |

**E2 (mất dấu): detector hoàn hảo trên tập này** (P=R=1,0) — tự động hoá tốt, đúng như thiết kế (đối chiếu từ vựng dựng từ corpus + tỉ lệ dấu tương đối).

**E6 (suy sụp mạch lạc): precision tuyệt đối (1,0), recall vừa phải (0,486)** — mọi cờ tự động bật đều đúng (không dương tính giả), nhưng bỏ sót khoảng một nửa ca thật. Nguyên nhân đã xác định cụ thể: thước đo lặp n-gram (cửa sổ 5 từ) có điểm mù với vòng lặp **dài hơn cửa sổ đo** — ví dụ thực tế: một câu ~16 từ lặp lại 62/67 dòng (92,5%) nhưng chỉ số n-gram đo được 5,1%, dưới hẳn ngưỡng. Đã bổ sung chỉ số lặp theo dòng (`max_line_repeat`) để vá một phần điểm mù này trong quá trình sinh dữ liệu.

**E1 (mojibake): recall bằng 0 tuyệt đối — không phải detector hỏng, mà là ranh giới taxonomy chưa rõ trước khi gán nhãn.** Đối chiếu 37 ca người gán E1: 35/37 ca chỉ gán E1 (không kèm E5), và trong số đó ~27 ca detector `foreign_script_hits()` (vốn dùng cho E5) **thực ra có bắt được** ký tự lạ (Hàn, Hoa, Ả Rập, Thái, Nga...). Người gán nhãn xếp "ký tự/âm tiết rời rạc, vô nghĩa từ script khác" vào E1 ("đọc như vỡ"), trong khi thiết kế ban đầu của hệ thống xếp mọi ký tự ngoài Latin vào E5 ("chuyển ngữ"). Đây là điểm mơ hồ thực sự của định nghĩa taxonomy — đã bổ sung quy tắc rõ ràng vào `docs/ANNOTATION_GUIDELINE.md` cho vòng gán nhãn tiếp theo. Hệ quả kéo theo: **E5 có precision thấp (0,065)** phần lớn vì cùng nguyên nhân — detector đúng chức năng nhưng bị tính là "dương tính giả" do người xếp ca đó vào E1.

**E3 (bịa trích dẫn): precision thấp (0,133)** — detector đối chiếu index dựng từ corpus khá nhạy nhưng bắt nhầm nhiều diễn giải hợp lệ (paraphrase một điều luật có thật) thành "trích dẫn không tồn tại". Cần thu hẹp điều kiện khớp trong `viedge.rag.citations` ở vòng phát triển tiếp theo.

## Phân bố E6 theo mức nén — phát hiện chính của RQ2

| Model | bf16 | int8 | int4_awq |
|---|---|---|---|
| gemma-3-1b-it | 10,0% | 13,3% | **44,0%** |
| qwen2.5-1.5b-it | 17,3% | 37,3% | **38,7%** |

Suy sụp mạch lạc tăng mạnh và nhất quán theo mức nén ở **cả hai kiến trúc độc lập** — từ ~10-17% ở BF16 lên 38,7-44,0% ở INT4_AWQ, tăng gấp 2,2–4,4 lần. Xu hướng này **khớp trực tiếp với Bảng 3 (RQ1)**: INT4_AWQ là bậc duy nhất gây suy giảm accuracy có ý nghĩa thống kê sau hiệu chỉnh Holm-Bonferroni ở cả hai model. Hai phép đo độc lập (trắc nghiệm tự động và taxonomy gán nhãn người) cùng hội tụ về một kết luận — bằng chứng mạnh hơn hẳn từng phép đo riêng lẻ.

**E2 (mất dấu) ổn định bất ngờ** — dao động hẹp quanh 20-25% ở mọi mức nén quan sát được, không tăng rõ theo mức nén như E6. Gợi ý rằng lượng tử hoá ảnh hưởng đến **mạch lạc/cấu trúc sinh văn bản** nhiều hơn là đến **khả năng tái tạo dấu thanh** — một phân biệt cụ thể mà chỉ taxonomy đa nhãn mới lộ ra được, trắc nghiệm MCQ không đo được.

## Hạn chế (đưa vào phần Hạn chế chung của Chương 4)

- RQ2 chỉ đo trên 3/5 bậc nén (BF16, INT8, INT4_AWQ) do giới hạn thời gian gán nhãn thủ công; không đo FP8 và GGUF_Q4_K_M — hai bậc này có dữ liệu ở Bảng 3 (RQ1) nhưng chưa có taxonomy tương ứng.
- Mã E4 chỉ xuất hiện 1/201 mẫu — không đủ dữ liệu để kết luận bất kỳ xu hướng nào.
- Detector E3/E5 có precision thấp, phù hợp làm công cụ triage (sàng lọc mẫu cho người xem) nhưng không đủ tin cậy để dùng độc lập — đúng tinh thần thiết kế ban đầu của đề tài.
