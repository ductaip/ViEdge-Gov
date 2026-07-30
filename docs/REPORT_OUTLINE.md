# Dàn ý quyển báo cáo — ánh xạ trực tiếp sang rubric Euréka

Rubric bán kết 100 điểm. Mỗi mục dưới ghi rõ **đang ăn điểm nào**.
Quyển là thứ 97% đề tài chết vì nó. Viết quyển quan trọng hơn chạy thêm thí nghiệm.

| Điểm | Hạng mục rubric |
|---|---|
| 10 | Mục đích, ý nghĩa, khả năng ứng dụng rõ ràng cụ thể |
| 20 | Tính khoa học, sáng tạo, tính mới trong cách đặt & giải quyết vấn đề |
| 30 | Nội dung phù hợp, kết quả & phương pháp rõ ràng |
| 20 | **Giải pháp, kiến nghị có giá trị** |
| 10 | Hình thức trình bày |
| 10 | Trích dẫn nguồn tài liệu tham khảo |

---

## Trang bìa & tóm tắt

> ⚠️ **ẨN DANH.** Không tên tác giả, GVHD, tên trường, logo, hoặc bất kỳ dấu hiệu
> nhận biết. Kiểm cả metadata PDF (`Author`, `Creator`, `Title`) và link repo.

**Tóm tắt (250–300 từ).** Cấu trúc 5 câu: vấn đề xã hội → khoảng trống khoa học →
ta làm gì → con số chính → khuyến nghị. Người đọc chỉ đọc phần này rồi quyết định
thái độ với cả quyển.

---

## Chương 1 · Mở đầu **[10đ ứng dụng]**

**1.1 Đặt vấn đề.** Mở bằng **vấn đề xã hội**, tuyệt đối không mở bằng quantization.
Chuyển đổi số cấp xã → cán bộ và người dân cần tra cứu thủ tục → giải pháp hiện nay
gọi API nước ngoài → dữ liệu công dân rời biên giới + nơi mạng yếu không dùng được.

**1.2 Định hướng chính sách.** Trích Nghị quyết 57-NQ/TW gần như nguyên văn. BTC
đã nêu rõ định hướng này; không trích là tự bỏ điểm.

**1.3 Khoảng trống khoa học.** Giải pháp là mô hình nhỏ chạy tại chỗ, phải nén.
**Chưa ai đo được nén xong tiếng Việt còn lại bao nhiêu.**

**1.4 Mục tiêu & câu hỏi nghiên cứu.** RQ1–RQ4, phát biểu ngắn gọn.

**1.5 Đóng góp.** Đúng 4 gạch đầu dòng, mỗi dòng một câu.

**1.6 Bố cục.**

---

## Chương 2 · Tổng quan **[10đ trích dẫn + nền cho 20đ tính mới]**

**2.1 Nén mô hình ngôn ngữ.** Lượng tử hoá trọng số/kích hoạt, các mức, đánh đổi.

**2.2 Nén và ngôn ngữ ít tài nguyên.** Mục quan trọng nhất chương này. Marchisio
et al. (2024): nén khuếch đại đối xử bất bình đẳng với đặc trưng đuôi dài; ngôn
ngữ chịu ảnh hưởng không đồng đều; **chỉ số tự động đánh giá thấp nghiêm trọng
thiệt hại** (1,7% tự động ↔ 16,0% do người chấm, tiếng Nhật). Tiếng Việt cần ~4×
số token so với tiếng Anh với tokenizer phổ thông → dấu bị chẻ thành sub-word tần
suất thấp.

**2.3 Mô hình ngôn ngữ cho tiếng Việt.** PhoGPT, VinaLLaMA, dòng Qwen đa ngôn ngữ.

**2.4 Đánh giá LLM tiếng Việt.** VMLU (10.880 câu, 58 môn) như chuẩn nội địa.

**2.5 Hỏi đáp pháp luật tiếng Việt.** ALQAC, VLSP-LTER, DRiLL, LegalSLM, MLQA-TSR,
VLegal-Bench, ViHERMES. **Nêu rõ đề tài này KHÁC ở đâu**: các công trình đó đo
*năng lực pháp lý*; đề tài này đo *độ bền ngôn ngữ dưới ràng buộc triển khai*.

**2.6 Kết luận chương: khoảng trống.** Ba câu.

---

## Chương 3 · Phương pháp **[30đ nội dung/PPNC]**

**3.1 Tổng quan thiết kế.** Sơ đồ hai trục + một trục khuyến nghị.

**3.2 Kho văn bản.** Nguồn, mốc thời gian chốt corpus, số liệu (**Bảng 1**).
Giải thích cắt theo điều/khoản/điểm chứ không theo token — và vì sao (ADR-006).

**3.3 ViGovQA-GT.** Quy trình xây, schema, hai người xác minh, số liệu bộ dữ liệu.

**3.4 Mô hình & mức nén.** Ma trận, và **vì sao không dùng bnb NF4** làm đường
4-bit chính (số đo cụ thể — ADR-005). Nêu calibration bằng tiếng Việt và lý do
(ADR-007) — đây là chi tiết cho thấy nhóm hiểu việc mình làm.

**3.5 Giao thức đánh giá.** VMLU lấy mẫu phân tầng: cỡ mẫu, seed, sai số ±1,98%
(**Bảng 2**). Nói thẳng vì sao không chạy hết: ngân sách compute.

**3.6 Taxonomy lỗi.** E1–E6, định nghĩa, ví dụ, hệ quả thực tế.

**3.7 Quy trình gán nhãn.** Hai người độc lập, ẩn cờ tự động, AC1 là chỉ số chính
và **vì sao AC1 chứ không phải kappa** (ADR-004). Detector chỉ triage, nhãn cuối
là nhãn người — nêu rõ, vì đây chính là điểm mà tài liệu đã cảnh báo.

**3.8 Truy hồi lai.** BM25 + dense + RRF + top-k động. Vì sao RRF (hợp nhất theo
hạng nên không cần chuẩn hoá thang điểm). Vì sao index cả dạng bỏ dấu.

**3.9 Cơ chế kiểm trích dẫn.** Nối RQ2 → giải pháp: E3 tìm ra ở chương 4 được
chặn bằng cửa này. **Mạch nghiên cứu → giải pháp là thứ hội đồng muốn thấy.**

**3.10 Đo hiệu năng.** Cấu hình máy CPU mục tiêu, ghi rõ CPU/RAM/OS.

---

## Chương 4 · Kết quả **[30đ + 20đ tính mới]**

**4.1 (RQ1) Đường cong suy giảm.** **Bảng 3** + đồ thị. Nêu ngưỡng phá vỡ.

**4.2 (RQ2) Lỗi hỏng ở đâu.** **Bảng 4** (đồng thuận) + **Bảng 5** (hiệu chuẩn
detector) + phân bố lỗi theo mức nén. **Đây là mục quan trọng nhất cả quyển.**
Nếu chỉ có thời gian viết tốt một mục, viết mục này.

**4.3 (RQ3) RAG bù được bao nhiêu.** **Bảng 6**. So top-k động vs cố định.

**4.4 (RQ4) Đánh đổi chất lượng–chi phí.** **Bảng 7** + đường Pareto + điểm khuyến nghị.

**4.5 Thảo luận.**
- Đường cong tiếng Việt có khác dự đoán từ tài liệu tiếng Anh?
- Mô hình bản địa (PhoGPT) có bền hơn dưới nén? *(nếu chạy được P3)*
- **Hạn chế, nói thẳng:** cỡ mẫu, số mô hình, corpus một thời điểm, chỉ tiếng Việt.

> Mục hạn chế viết trung thực làm **tăng** điểm. Hội đồng phản biện tìm hạn chế;
> nếu ta nêu trước thì mất vũ khí của họ, còn giấu thì mất uy tín.

---

## Chương 5 · Kết luận & kiến nghị **[20đ giải pháp/kiến nghị]**

Chương này **20 điểm** và là chương đề tài học thuật thuần hay bỏ qua. Đừng bỏ.

**5.1 Kết luận.** Bốn đoạn, mỗi đoạn một RQ, mỗi đoạn có con số.

**5.2 Khuyến nghị cấu hình triển khai.** Bảng cụ thể: *cơ quan có máy cấu hình X
nên dùng mô hình Y ở mức nén Z, kèm RAG, chờ khoảng T giây, tốn R GB RAM.*
Cụ thể đến mức người đọc làm theo được ngay.

**5.3 Khuyến nghị quy trình kiểm định.** Checklist cho đơn vị triển khai LLM tiếng
Việt: kiểm gì trước khi đưa vào dùng, ngưỡng nào là không chấp nhận được.

**5.4 Sản phẩm chuyển giao.** ViGovQA-GT (mở, có DOI), mã nguồn công cụ đo,
hệ thống demo.

**5.5 Hướng phát triển.**

---

## Phụ lục

A. Báo cáo lấy mẫu VMLU (seed, phủ môn, sai số)
B. Hướng dẫn gán nhãn (bản đầy đủ)
C. Bộ prompt probe
D. Ví dụ từng mã lỗi (ảnh chụp đầu ra thật)
E. Cấu hình phần cứng & phần mềm (phiên bản thư viện — quan trọng cho tái lập)
F. Danh mục mã nguồn

---

## Hình thức **[20đ — điểm miễn phí, đừng mất một điểm nào]**

- [ ] Font, cỡ, giãn dòng, lề theo đúng quy định BTC
- [ ] Mọi bảng/hình **có số và có chú thích**, được **dẫn trong thân văn**
- [ ] Số trong bảng khớp số trong thân văn → sinh bảng bằng `make tables`, **không chép tay**
- [ ] Trích dẫn thống nhất một chuẩn từ đầu đến cuối
- [ ] Mọi nguồn trong thân văn có trong danh mục, và ngược lại
- [ ] Không lỗi chính tả *(đọc ngược từ cuối lên để bắt lỗi)*
- [ ] Mục lục, danh mục bảng, danh mục hình, danh mục viết tắt
- [ ] Ẩn danh hoàn toàn, kể cả metadata PDF

---

## Chuẩn bị phản biện (dùng cho bán kết & chung kết)

Viết sẵn câu trả lời, tập nói thành tiếng. 20 câu dự kiến:

1. Vì sao lấy mẫu VMLU mà không chạy hết 10.880 câu?
2. Vì sao AC1 chứ không phải Cohen's kappa?
3. Chỉ hai người gán nhãn, có đủ tin cậy không?
4. Nếu hệ thống trả lời sai và người dân bị phạt thì trách nhiệm ai?
5. Corpus chốt ở một thời điểm — luật đổi thì sao?
6. Vì sao chỉ 2 (hoặc 4) mô hình?
7. Detector tự động có thiên lệch không?
8. Đóng góp khác gì ViHERMES / MLQA-TSR / LegalSLM?
9. Vì sao không dùng mô hình lớn hơn cho chính xác hơn?
10. Vì sao không dùng bitsandbytes như mọi người?
11. Calibration tiếng Việt ảnh hưởng kết quả thế nào?
12. Đây là nghiên cứu hay chỉ là làm sản phẩm?
13. Ai sẽ dùng hệ thống này, đã thử với người dùng thật chưa?
14. Chi phí triển khai thực tế cho một xã là bao nhiêu?
15. So với gọi API thì rẻ hơn hay đắt hơn?
16. Bảo mật: mô hình chạy tại chỗ nhưng cập nhật văn bản thế nào?
17. Kết quả có tái lập được không?
18. Nếu suy giảm nhỏ thì kết luận của đề tài còn giá trị gì?
19. Nhóm tự đánh giá hạn chế lớn nhất là gì?
20. Định hướng tiếp theo?

**Câu 18 phải trả lời được cho cả hai chiều.** Nếu suy giảm nhỏ, kết luận là
*"tiếng Việt bền hơn dự đoán, có thể triển khai an toàn ở mức X"* — đó vẫn là
khuyến nghị dùng được, và phải nói ra trước khi hội đồng gài.
