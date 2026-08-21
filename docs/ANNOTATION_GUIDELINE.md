# Hướng dẫn gán nhãn — ViEdge-Gov

Đọc hết trước khi gán mẫu đầu tiên. In ra để cạnh máy.

---

## Quy tắc bất di bất dịch

1. **Hai người gán ĐỘC LẬP.** Không xem nhãn của nhau. Không thảo luận ca cụ thể
   trước khi cả hai xong. Vi phạm → AC1 vô nghĩa → hội đồng có quyền loại toàn bộ
   phần phân tích. Đây là rủi ro lớn nhất của cả đề tài về mặt phương pháp.
2. **Bật `--hide-auto`.** Xem cờ tự động trước khi gán tạo hiệu ứng mồi neo, và
   khi đó không thể dùng nhãn người để hiệu chuẩn detector nữa (vòng lặp logic).
3. **Một người không gán cả hai vai.** Nếu team chỉ có 1 người rảnh, hoãn — đừng giả.
4. **Không sửa nhãn cũ sau khi biết người kia gán gì.** Bất đồng được giải quyết ở
   **vòng 3** có mặt cả hai, và phải ghi lại là "đã giải quyết sau thảo luận" —
   AC1 báo cáo là AC1 **trước** thảo luận.

## Lệnh

```bash
python scripts/07_annotate_cli.py --who A --queue results/taxonomy/queue_<tag>.jsonl --hide-auto
python scripts/07_annotate_cli.py --who B --queue results/taxonomy/queue_<tag>.jsonl --hide-auto
python scripts/08_compute_agreement.py
```

Có thể dừng giữa chừng — script tự nhớ mẫu đã gán.

---

## Cách gán

Với mỗi đầu ra, hỏi lần lượt sáu câu, độc lập nhau:

| | Câu hỏi | Bật mã |
|---|---|---|
| 1 | Có ký tự vỡ, không đọc được? | E1 |
| 2 | Có từ mất dấu, hoặc sai dấu thanh làm đổi nghĩa? | E2 |
| 3 | Có dẫn điều/khoản/số hiệu **không tồn tại** trong kho? *(phải TRA, không đoán)* | E3 |
| 4 | Có dùng lẫn thuật ngữ hành chính? *(phải TRA văn bản gốc)* | E4 |
| 5 | Có tiếng nước ngoài chen vào? | E5 |
| 6 | Có lặp bệnh lý, câu cụt, văn bản rã? | E6 |

M��t đầu ra có thể bật nhiều mã. Không bật mã nào cũng là một nhãn hợp lệ.

## Ca khó — quyết trước để hai người xử lý giống nhau

| Tình huống | Xử lý |
|---|---|
| Tên riêng viết không dấu ("Nguyen Van A") | **Không** tính E2 |
| Từ mượn kỹ thuật lẻ ("app", "online", "server") | **Không** tính E5 |
| Văn bản luật lặp cấu trúc hợp lệ ("Phạt tiền từ ... đối với ...") | **Không** tính E6 |
| Trích dẫn tồn tại nhưng dẫn sai chỗ | **Không** tính E3; ghi vào ghi chú |
| Đầu ra rỗng hoặc chỉ có khoảng trắng | Tính **E6** |
| Trả lời đúng nhưng thiếu trích dẫn | **Không** phải lỗi taxonomy (đó là việc của cửa citation-check) |
| Không chắc giữa E2 và E1 | Có ký tự **không đọc được** → E1; chỉ **thiếu dấu** → E2 |
| Ký tự/âm tiết rời rạc, vô nghĩa từ script khác chen vào (Hàn, Hoa, Ả Rập, Hy Lạp...) | Tính **E1** (đọc như vỡ, không phải chuyển ngữ có chủ đích) |
| Cụm từ/câu hoàn chỉnh, có nghĩa bằng ngôn ngữ khác | Tính **E5**, không phải E1 |
| Nội dung sai sự thật nhưng ngôn ngữ hoàn hảo | **Không** bật mã nào; ghi chú `SAI_NOI_DUNG` |
| Thật sự không biết | Ghi chú `KHÔNG_QUYẾT_ĐƯỢC`, không bật mã. Nếu tái diễn ≥5 lần → ứng viên mã mới |

> Ô cuối cùng quan trọng: taxonomy này đo **chất lượng ngôn ngữ dưới nén**, không
> đo tính đúng đắn nội dung. Trộn hai thứ làm cả hai đo không được.

---

## Ngân sách và mục tiêu

| Hạng mục | Mục tiêu | Tối thiểu |
|---|---|---|
| Số mẫu gán chung (2 người) | 150 | 50 |
| Tốc độ | ~2–3 phút/mẫu | — |
| Tổng công | ~6–8 giờ mỗi người | — |
| AC1 từng mã | ≥ 0.70 | ≥ 0.60 |

**Nếu AC1 < 0.60 ở một mã:** dừng, đọc lại định nghĩa cùng nhau, viết rõ hơn,
pilot lại 30 mẫu mới. Đừng gán tiếp 150 mẫu với định nghĩa mơ hồ — công đó sẽ
phải bỏ hết.

---

## Ghi chú cho ViGovQA-GT (bộ đánh giá)

Khác với gán nhãn lỗi, ở đây hai người **cùng xác minh đáp án và trích dẫn**:

1. Người A viết đáp án tham chiếu + trích dẫn từ văn bản gốc
2. Người B xác minh **độc lập** trên văn bản gốc — không đọc đáp án của A trước
3. Lệch nhau → thảo luận; không giải quyết được → **bỏ mẫu** (đừng ép)
4. `make rag` sẽ kiểm mọi gold unit có tồn tại trong index không

Chạy `python -c "from viedge.data.vigovqa import validate, load; ..."` hoặc
`make rag` để chặn dữ liệu sai định dạng trước khi dùng.

**Cạm bẫy đã biết:** trường `doc` trong citations phải **trùng từng ký tự** với
`id` văn bản trong `configs/retrieval.yaml`. Lệch một ký tự → mọi gold unit trượt
→ F2 = 0. Script `10_eval_rag.py` in cảnh báo phủ gold trước khi tính điểm — đọc nó.
