# Roadmap ViEdge-Gov — 27 ngày đến 25/08/2026

**Hạn nộp đã xác minh: 17g00 ngày 25/08/2026.** Nộp mục tiêu: **24/08**.
Ngày khởi động thực: **31/07** (29–30/07 dành cho hạn Viettel Phase 1).

Nguyên tắc bất di bất dịch: **cắt scope, không cắt chất lượng viết.**
97% đề tài bị loại ở bán kết — nơi hội đồng chỉ đọc giấy, không thấy code.

---

## Ưu tiên (cắt từ dưới lên khi thiếu thời gian)

| P | Nội dung | Bắt buộc? | Không có thì mất gì |
|---|---|---|---|
| P0 | 2 model × 4 precision × VMLU-sampled | ✅ | Không có đề tài |
| P1 | Taxonomy lỗi E1–E6 + nhãn người + AC1 | ✅ | Mất 20đ tính mới |
| P2 | ViGovQA-GT + RAG on/off | ✅ | Mất trục ứng dụng |
| P3 | 2 model còn lại (Qwen3.5-4B, PhoGPT) | ⬜ | Giảm sức thuyết phục |
| P4 | Đối chứng tiếng Anh + calib EN vs VI | ⬜ | Rất tiếc nhưng bỏ được |

**Ranh giới cắt, quyết trước để khỏi tranh luận lúc gấp:**
> Hết ngày **13/08** mà chưa có phân bố lỗi RQ2 → cắt P3 và P4, giữ 2 model,
> dồn toàn lực vào taxonomy + hệ thống + quyển.

---

## D0 · 29–30/07 · ~2 giờ, song song Viettel

- [x] Xác minh hạn nộp → **25/08** ✔
- [ ] Hỏi Phòng KHCN / Đoàn trường UTH: còn suất tiến cử CNTT? *(miễn phí, tránh 1 triệu)*
- [ ] **Chốt đúng 5 người đứng tên** + phân vai (bảng dưới)
- [ ] Tải corpus vào `data/raw/` (xem `DATA_SOURCES.md`) — chỉ tải, chưa xử lý
- [ ] `make setup && make smoke` → phải xanh trước khi làm gì khác

| Vai | Người | Trách nhiệm |
|---|---|---|
| Chủ nhiệm | | Quyển báo cáo, thủ tục, quyết định cắt scope |
| KT – nén & đo | | quantization, lm-eval, ma trận P0/P3 |
| KT – hệ thống | | retrieval, RAG, citation-check, demo |
| Gán nhãn A | | ViGovQA-GT + taxonomy |
| Gán nhãn B | | Gán nhãn ĐỘC LẬP (phải khác người A) |

---

## Tuần 1 · 31/07 → 06/08 · Dựng nền & pilot

| Ngày | Việc | Lệnh | Ai |
|---|---|---|---|
| 31/07 | Corpus → điều/khoản/điểm; kiểm parser bằng tay 10 điều | `make corpus` | KT-hệ thống |
| 31/07 | Tải + lấy mẫu VMLU, ghim seed | `make sample` | KT-đo |
| 01/08 | Dựng bộ calib **tiếng Việt** (256 mẫu, có văn bản pháp luật) | — | KT-đo |
| 01–02/08 | Xuất bf16/fp8/int8/int4 cho 2 model đầu | `DRY=1 make export` rồi `make export` | KT-đo |
| 02/08 | Thêm task `vmlu_sampled` vào lm-eval 0.4.12 | — | KT-đo |
| 03–04/08 | **Chạy P0** | `make eval` | KT-đo |
| 03/08 | Viết guideline gán nhãn; pilot 50 mẫu | `make probe` | A + B |
| 04/08 | AC1 lần 1 → hiệu chuẩn ngưỡng detector | `make agreement` | A + B |
| 05/08 | Dựng index truy hồi + kiểm phủ gold | `make index` | KT-hệ thống |
| 06/08 | **Cột mốc 1: có Bảng 3 (RQ1)** + ghi WEEKLOG | `make tables` | Chủ nhiệm |

⚠️ Nếu AC1 pilot < 0.60 → gộp mã lỗi mơ hồ, viết lại guideline, pilot lại. **Đừng chạy tiếp với taxonomy không đáng tin.**

---

## Tuần 2 · 07/08 → 13/08 · Trục tính mới (quan trọng nhất)

| Ngày | Việc | Ai |
|---|---|---|
| 07/08 | Mở bộ probe lên **≥150 prompt** tiếng Việt, phủ 4 loại câu hỏi | A |
| 07–08/08 | Sinh tự do trên mọi mức nén → `results/taxonomy/generations/` | KT-đo |
| 08/08 | Chạy detector → hàng đợi gán nhãn | KT-đo |
| 09–11/08 | **Gán nhãn E1–E6, hai người độc lập, ≥150 mẫu** | A + B |
| 11/08 | AC1 + hiệu chuẩn detector (P/R từng mã) | Chủ nhiệm |
| 09–11/08 | Hoàn tất **ViGovQA-GT 400–600 câu** | A + B |
| 12/08 | Chốt taxonomy v1 **từ dữ liệu thật** (v0 chỉ là nháp) | Chủ nhiệm |
| 12–13/08 | Viết quyển chương 1–2 (mở đầu, tổng quan) | Chủ nhiệm |
| 13/08 | **Cột mốc 2: Bảng 4 + Bảng 5 (RQ2)** — trái tim đề tài | — |

---

## Tuần 3 · 14/08 → 20/08 · Ứng dụng & hiệu năng

> ⚠️ **XUNG ĐỘT: Viettel Phase 2 ngày 17–19/08.**
> Phân công cứng từ D0: nhóm Viettel **không chạm** Euréka 3 ngày này;
> nhóm Euréka **không bị gọi** hỗ trợ Viettel. Quyết trước, không thương lượng giữa chừng.

| Ngày | Việc | Lệnh | Ai |
|---|---|---|---|
| 14/08 | Chạy P2: ViGovQA-GT × {no-RAG, RAG}; so top-k động vs cố định | `make rag` | KT-hệ thống |
| 14/08 | Xuất GGUF Q8_0 + Q4_K_M | `make export` | KT-đo |
| 15/08 | Đo trên **máy CPU thật** (ghi rõ cấu hình) | `make bench` | KT-đo |
| 15/08 | Cơ chế citation-check nối vào pipeline | — | KT-hệ thống |
| 16/08 | Demo offline chạy đầu-cuối | `make demo` | KT-hệ thống |
| 17–19/08 | *(Viettel Phase 2 — nhóm Euréka viết quyển chương 3–4)* | — | Chủ nhiệm |
| 20/08 | Đường Pareto, chốt điểm vận hành khuyến nghị | `make tables` | Chủ nhiệm |
| 20/08 | **Cột mốc 3: rút mạng mà hệ thống vẫn trả lời** | — | — |

---

## Tuần 4 · 21/08 → 24/08 · Đóng gói

| Ngày | Việc |
|---|---|
| 21/08 | Bản khuyến nghị cấu hình triển khai (trục C — 20đ) |
| 21/08 | Phát hành ViGovQA-GT + DOI Zenodo |
| 22/08 | Quyển chương 5 (kết luận, kiến nghị) + phụ lục |
| 22/08 | **Rà toàn bộ trích dẫn** — 10đ miễn phí, đừng mất |
| 23/08 | Poster 0,8 × 1,3 m |
| 23/08 | **Ẩn danh hoá**: xoá tên tác giả/GVHD/trường/logo, metadata PDF, link repo |
| 23/08 | Ảnh thẻ SV cả 5 thành viên; quay video demo dự phòng |
| 24/08 | Đọc lại toàn bộ 1 lượt · **NỘP** |

---

## Sau khi nộp

- **~T10–11**: vòng bán kết → luyện phản biện, chuẩn bị 20 câu hỏi khó (xem `REPORT_OUTLINE.md` §Phản biện)
- **~T12**: chung kết → tập kịch bản demo rút mạng đến mức phản xạ

## Việc lặp mỗi tuần (không được bỏ)

1. **Chủ nhật: ghi `WEEKLOG.md`** — số liệu mới, quyết định, việc trượt, rủi ro mới
2. `make tables` để bảng luôn khớp dữ liệu nguồn
3. Ghi mọi quyết định đổi hướng vào `DECISIONS.md`
4. Kiểm `logs/runlog.jsonl` có đủ mọi lần chạy thật
