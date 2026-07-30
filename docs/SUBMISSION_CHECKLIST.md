# Checklist nộp hồ sơ — hạn 17g00 ngày 25/08/2026

**Nộp mục tiêu: 24/08.** Không nộp ngày cuối. Cổng đăng ký hay nghẽn giờ chót.

---

## Hồ sơ bắt buộc

- [ ] **Phiếu đăng ký dự thi** theo mẫu BTC
- [ ] **Báo cáo toàn văn** — cả `.docx` **và** `.pdf`
- [ ] **Ảnh chụp/scan thẻ sinh viên** của **tất cả** thành viên
- [ ] Lệ phí **1.000.000đ/đề tài** *(chỉ nếu đi đường Vòng Sơ tuyển tự do)*

## Trước đó: chọn đường vào

- [ ] Đã hỏi Phòng KHCN / Đoàn trường UTH về **suất tiến cử (miễn phí)**
- [ ] Nếu được trường tiến cử → **KHÔNG** đăng ký vòng tự do (điều kiện loại trừ)
- [ ] Nếu không → đăng ký vòng tự do, chuẩn bị lệ phí

## Nhân sự

- [ ] Đúng **≤ 05 sinh viên**. Người thứ 6 trở đi không có tên hồ sơ, không giấy
      chứng nhận, không ghi được CV
- [ ] Mọi thành viên đang là SV tại ĐH/HV/CĐ
- [ ] Thứ tự tên đã thống nhất *(chốt sớm, đừng để tranh lúc gấp)*

## Ẩn danh — kiểm từng dòng

- [ ] Quyển: không tên tác giả, GVHD, tên trường, logo
- [ ] Poster: cùng yêu cầu
- [ ] **Metadata PDF** đã xoá: `Author`, `Creator`, `Producer`, `Title`
      ```bash
      exiftool -all= bao_cao.pdf         # hoặc
      qpdf --empty --pages bao_cao.pdf -- out.pdf
      pdfinfo bao_cao.pdf | head         # xác minh lại
      ```
- [ ] Tên file không chứa tên người/trường
- [ ] Link GitHub trong quyển **không lộ danh tính** *(dùng repo ẩn danh hoặc bỏ link, thay bằng "mã nguồn sẽ công bố sau khi công bố kết quả")*
- [ ] Ảnh chụp màn hình trong quyển không lộ đường dẫn `/home/<tên>/...`
- [ ] Phần lời cảm ơn: **bỏ** khỏi bản nộp, thêm lại sau

## Chất lượng quyển

- [ ] Số trong mọi bảng do `make tables` sinh, **không chép tay**
- [ ] Mọi bảng/hình có số, có chú thích, được dẫn trong thân văn
- [ ] Mọi nguồn trong thân văn có trong danh mục và ngược lại
- [ ] Đọc soát chính tả 1 lượt **đọc ngược từ cuối lên**
- [ ] Mục lục / danh mục bảng / danh mục hình / danh mục viết tắt
- [ ] Nhờ **một người ngoài đề tài** đọc chương 1 — nếu họ không hiểu vấn đề
      trong 2 phút thì viết lại

## Sản phẩm kèm

- [ ] ViGovQA-GT phát hành mở, có DOI Zenodo, link ghi trong quyển
- [ ] Repo mã nguồn sạch, có README, `make smoke` xanh
- [ ] Video demo dự phòng (USB + cloud) — máy hỏng tại chỗ là chuyện thường
- [ ] Poster 0,8 × 1,3 m, in thử A4 để kiểm cỡ chữ

## Sau khi nộp

- [ ] Lưu **ảnh chụp màn hình xác nhận nộp** + email xác nhận
- [ ] Lưu bản `.docx`/`.pdf` đã nộp vào thư mục riêng, **không sửa nữa**
- [ ] Ghi ngày nộp vào `WEEKLOG.md`
- [ ] Đặt nhắc: theo dõi kết quả bán kết (~T10–11)
