# Taxonomy lỗi tiếng Việt do nén mô hình — v0 (nháp)

⚠️ **Đây là v0, dựng từ giả thuyết.** Phải chốt v1 **từ dữ liệu thật** sau pilot
Tuần 1. Nếu báo cáo dùng nguyên v0 mà không hiệu chuẩn, hội đồng có quyền hỏi
"căn cứ nào chia thành đúng 6 loại này" và ta sẽ không trả lời được.

Taxonomy này là **đóng góp số 2** của đề tài. Đường cong suy giảm (RQ1) thì ai
cũng đo được; phân loại *lỗi hỏng ở đâu* là thứ chưa có cho tiếng Việt.

---

## Nguyên tắc thiết kế

1. **Đa nhãn.** Một đầu ra có thể vừa E2 vừa E6. Không gộp thành biến hạng mục
   → đồng thuận phải tính riêng từng mã dưới dạng nhị phân.
2. **Quan sát được, không suy diễn.** Nhãn phải gán được chỉ bằng cách đọc đầu ra
   và tra văn bản gốc. Không có mã kiểu "mô hình không hiểu ngữ cảnh".
3. **Có hệ quả thực tế.** Mỗi mã phải trả lời được: *nếu lỗi này xảy ra ở cơ quan
   cấp xã thì hậu quả là gì?* Mã nào không trả lời được thì bỏ.

---

## Sáu mã lỗi

### E1 — Vỡ dấu / mojibake
Ký tự vỡ mã hoá, không đọc được.

- Ví dụ: `Ngưá»i Ä'iá»u khiá»n phÆ°Æ¡ng tiá»n`
- **Hệ quả:** đầu ra vô dụng hoàn toàn; người dùng mất tin ngay lập tức.
- **Phát hiện tự động:** khá tốt. Hai lớp — round-trip latin-1↔utf-8 (bắt vỡ toàn
  phần) và bigram ký-tự-có-dấu + ký hiệu Latin-1 (bắt vỡ một phần).
- **Lưu ý gán nhãn:** vỡ *một phần* vẫn tính E1.

### E2 — Mất dấu hoặc sai dấu thanh
Từ mất hết dấu, hoặc sai dấu thanh làm đổi nghĩa.

- Ví dụ mất dấu: `Nguoi dieu khien phuong tien phai tuan thu`
- Ví dụ đổi nghĩa: `phạt` → `phát`; `cấm` → `cắm`; `tước` → `tuốc`
- **Hệ quả:** loại đổi nghĩa **nguy hiểm hơn** loại mất dấu — người đọc vẫn hiểu
  được văn bản mất dấu, nhưng "phạt" thành "phát" thì đọc ra nghĩa sai.
- **Phát hiện tự động:** mất dấu tốt (đối chiếu từ vựng dựng từ corpus + tỉ lệ dấu
  tương đối so với BF16). **Sai dấu thanh thì KHÔNG tự động được** — cần người.
- **Lưu ý:** đây là mã kỳ vọng nhạy nhất với mức nén. Giả thuyết trung tâm của
  đề tài nằm ở đây.

### E3 — Bịa số hiệu văn bản / trích dẫn không tồn tại
Dẫn một điều, khoản, hoặc số hiệu văn bản không có trong kho.

- Ví dụ: trích `Nghị định 100/2019/NĐ-CP` khi văn bản hiện hành đã khác; `Điều 4242`
- **Hệ quả:** nghiêm trọng nhất về mặt pháp lý. Người dân tra ra mức phạt sai và
  hành động theo.
- **Phát hiện tự động:** tốt — đối chiếu với index định danh dựng từ corpus.
- **Lưu ý:** phân biệt *bịa* (không tồn tại) với *dẫn sai chỗ* (tồn tại nhưng
  không liên quan). Loại thứ hai ghi vào ghi chú, không tính E3.

### E4 — Sai thuật ngữ hành chính
Dùng lẫn hai thuật ngữ khác nhau về thủ tục, hồ sơ hoặc mức phí.

- Cặp dễ nhầm: cấp đổi ↔ cấp lại · tạm giữ ↔ tước quyền sử dụng ·
  phạt tiền ↔ phạt bổ sung · GPLX ↔ giấy đăng ký xe · đăng ký lần đầu ↔ sang tên
- **Hệ quả:** người dân chuẩn bị sai hồ sơ, đi lại nhiều lần.
- **Phát hiện tự động:** **KHÔNG THỂ.** Máy chỉ báo "có mặt thuật ngữ trong cặp
  dễ nhầm" để đưa vào hàng đợi; đúng/sai do người phán, đối chiếu văn bản gốc.
- **Bổ sung cặp mới** khi gặp trong pilot → ghi vào `WEEKLOG.md` và cập nhật
  `ADMIN_CONFUSION_PAIRS` trong `detectors.py`.

### E5 — Chuyển ngữ ngoài ý muốn
Chèn tiếng Anh/Trung/ngôn ngữ khác vào giữa câu tiếng Việt.

- Ví dụ: `Theo quy định, the driver must comply with...`
- **Hệ quả:** cán bộ và người dân không đọc được; phá vỡ tính chuyên nghiệp.
- **Phát hiện tự động:** tốt cho chữ viết khác (CJK, Cyrillic, Thai) và chuỗi ≥3
  từ chức năng tiếng Anh liền nhau. Từ mượn lẻ (`app`, `online`) **không tính**.

### E6 — Suy sụp mạch lạc
Lặp vô hạn, câu cụt, mất chủ ngữ, văn bản rã.

- Ví dụ: `Phạt tiền từ 800.000 đồng. Phạt tiền từ 800.000 đồng. Phạt tiền...`
- **Hệ quả:** đầu ra không dùng được; nếu xảy ra trong hệ thống thật thì treo phiên.
- **Phát hiện tự động:** khá — tỉ lệ lặp n-gram cao nhất + kiểm câu cụt.
- **Lưu ý:** phân biệt lặp *bệnh lý* với lặp *hợp lệ* của văn bản pháp luật
  (văn bản luật vốn hay lặp cấu trúc "Phạt tiền từ ... đối với ..."). Đây là
  nguồn dương tính giả chính của mã này — **hiệu chuẩn ngưỡng trên corpus thật**.

---

## Bảng tổng hợp

| Mã | Loại | Tự động được? | Mức nghiêm trọng | Nguồn dương tính giả chính |
|---|---|---|---|---|
| E1 | Vỡ dấu | ✅ tốt | Cao | ký hiệu Latin-1 hợp lệ (°, ») |
| E2 | Mất/sai dấu | ⚠️ một phần | **Rất cao** (loại đổi nghĩa) | tên riêng, viết tắt không dấu |
| E3 | Bịa trích dẫn | ✅ tốt | **Rất cao** | corpus thiếu văn bản → báo oan |
| E4 | Sai thuật ngữ | ❌ không | Cao | — (chỉ triage) |
| E5 | Chuyển ngữ | ✅ tốt | Trung bình | từ mượn kỹ thuật |
| E6 | Suy sụp mạch lạc | ⚠️ khá | Cao | văn bản luật lặp cấu trúc hợp lệ |

---

## Quy trình chốt v1 (làm trong Tuần 1–2)

1. Pilot 50 mẫu, hai người gán độc lập theo v0.
2. Tính AC1 từng mã. **Mã nào AC1 < 0.60 thì hoặc viết lại định nghĩa, hoặc gộp
   với mã lân cận, hoặc bỏ.** Đừng giữ mã không đo được chỉ vì nghe hợp lý.
3. Ghi lại mọi ca "không biết xếp vào đâu" → nếu tái diễn ≥5 lần, đó là ứng viên
   mã E7 mới.
4. Hiệu chuẩn ngưỡng detector trên corpus thật (`Thresholds` trong `detectors.py`).
5. Chốt v1, ghi vào `DECISIONS.md`, **đóng băng** — không đổi taxonomy giữa lúc
   gán nhãn chính thức.
