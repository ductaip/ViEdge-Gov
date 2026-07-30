# Nhật ký quyết định (ADR)

Chỉ ghi quyết định **có đánh đổi**. Không ghi việc thường ngày.
Hội đồng bán kết đánh giá cao báo cáo thể hiện được quá trình ra quyết định —
mục "Vì sao chọn cách này mà không chọn cách kia" trong quyển lấy trực tiếp từ đây.

M��u: `## ADR-nnn · dd/mm · <tiêu đề>` + Bối cảnh / Quyết định / Phương án đã loại / Hệ quả.

---

## ADR-001 · 29/07 · Không dùng ViJudgeBench cho Euréka

**Bối cảnh.** ViJudgeBench đã có codebase và kết quả sơ bộ, dùng lại sẽ tiết kiệm nhiều tuần.

**Quyết định.** Giữ riêng cho SOICT 2026. Euréka làm đề tài khác.

**Phương án đã loại.** Dùng chung một công trình cho hai đích.

**Hệ quả.** Mất lợi thế tái sử dụng, phải làm đề tài mới trong 27 ngày. Đổi lại
không loãng cả hai và không rắc rối về trùng lặp công bố.

---

## ADR-002 · 29/07 · Loại phương án MLQA-TSR (hỏi đáp biển báo đa phương thức)

**Bối cảnh.** VLSP 2025 MLQA-TSR có dữ liệu đã gán nhãn sẵn, có baseline công bố
(F2 truy hồi 64,55%; accuracy QA 86,30%) — rất hợp để so sánh định lượng.

**Quyết định.** Loại.

**Lý do.**
1. Dữ liệu bị khoá sau agreement form gửi email tác giả duyệt → **khâu không kiểm soát được thời gian** trong sprint 27 ngày.
2. Mảng pháp luật tiếng Việt đã bão hoà: DRiLL, LegalSLM, MLQA-TSR (riêng VLSP 2025), cộng ALQAC, VLegal-Bench, ViHERMES — trong đó ViHERMES đã chiếm góc truy vết sửa đổi/hiệu lực.
3. Phản biện "nhóm chỉ chạy lại bộ dữ liệu của người khác" khó gỡ.

**Hệ quả.** Mất baseline công bố để so. Bù lại bằng: mốc tham chiếu BF16 nội bộ +
đối chứng API + bộ dữ liệu tự xây.

---

## ADR-003 · 29/07 · Chốt ViEdge-Gov

**Bối cảnh.** Cần đề tài khả thi 27 ngày, dùng được thế mạnh thật của team
(nén/đo suy luận, retrieval, phương pháp đánh giá), có câu chuyện ứng dụng.

**Quyết định.** Đo suy giảm chất lượng tiếng Việt dưới nén mô hình + trợ lý
hỏi đáp TTHC/giao thông chạy ngoại tuyến trên CPU.

**Vì sao khả thi.**
- Corpus công khai, tải ngay, **không phụ thuộc ai duyệt**
- Harness lm-eval 0.4.12 + Modal đã chạy thông từ chiến dịch Viettel → delta ~1 ngày
- Đã có **bằng chứng sơ bộ**: NF4 làm văn bản ngữ cảnh dài vỡ nghĩa
- Nền lý thuyết sẵn: Marchisio et al. (2024) về nén và ngôn ngữ ít tài nguyên
- Không tranh GPU với fork vLLM của Viettel

**Rủi ro chấp nhận.** Không có baseline ngoài để so; phải tự xây bộ đánh giá.

---

## ADR-004 · 29/07 · AC1 (Gwet) làm chỉ số đồng thuận chính

**Bối cảnh.** Taxonomy lỗi có prevalence rất lệch (E1 có thể chỉ ~2-3% mẫu).

**Quyết định.** AC1 là chỉ số chính; Cohen's kappa báo cáo kèm.

**Lý do.** Kappa sụp về gần 0 khi prevalence lệch dù hai người đồng ý gần hoàn
toàn (nghịch lý kappa). Đã kiểm bằng test: ở 95% đồng thuận thô, AC1 = 0.936
còn kappa chỉ 0.773 (`tests/test_agreement.py::test_kappa_paradox_ac1_more_stable`).

**Hệ quả.** Phải giải thích được trong 1 câu khi phản biện hỏi "vì sao không dùng kappa".

---

## ADR-005 · 29/07 · Không dùng bitsandbytes NF4 làm đường 4-bit chính

**Bối cảnh.** bnb NF4 là cách 4-bit phổ biến nhất trong tutorial.

**Quyết định.** Đường 4-bit chính = AWQ (GPU) + GGUF Q4_K_M (CPU). Giữ **một** lượt
bnb NF4 làm đối chứng "cách làm phổ biến nhưng sai".

**Lý do (đo được).** TPOT 58,3ms vs ~38ms của FP8 — chậm ~50% vì chi phí dequant
ăn hết phần tiết kiệm băng thông; và văn bản ngữ cảnh dài bắt đầu vỡ nghĩa.

**Hệ quả.** Lượt đối chứng bnb trở thành một điểm thảo luận có giá trị thay vì
một thất bại bị che.

---

## ADR-006 · 29/07 · Cắt chunk theo điều/khoản/điểm, không theo số token

**Bối cảnh.** RAG thông thường cắt theo cửa sổ token.

**Quyết định.** Đơn vị truy hồi = một điều luật, giữ metadata phân cấp.

**Lý do.** "Khoản 3 Điều 22" là địa chỉ pháp lý, không phải đoạn văn tuỳ ý. Cắt
theo token làm mất địa chỉ → mất khả năng sinh trích dẫn kiểm chứng được → mất
luôn cơ chế chống lỗi E3.

**Hệ quả.** Một số điều rất dài vượt ngân sách ngữ cảnh; xử lý bằng cắt ở tầng
khoản khi cần, không cắt giữa câu.

---

## ADR-007 · 29/07 · Calibration quantization phải bằng tiếng Việt

**Bối cảnh.** Mặc định của phần lớn công cụ nén là calibrate bằng C4/WikiText tiếng Anh.

**Quyết định.** Bộ calib 256 mẫu **tiếng Việt**, có văn bản pháp luật.

**Lý do.** Calib tiếng Anh chọn scale theo phân bố activation tiếng Anh → tự tay
tạo ra chính hiện tượng suy giảm đang đo → **hỏng tính hợp lệ nội tại của thí nghiệm**.

**Hệ quả (cơ hội).** So calib EN vs VI ở cùng mức nén là thí nghiệm P4. Nếu chênh
lớn, đó là một phát hiện độc lập và một khuyến nghị kỹ thuật rất cụ thể.
