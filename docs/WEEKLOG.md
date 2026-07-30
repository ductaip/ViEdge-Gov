# Nhật ký tuần — ViEdge-Gov

Ghi **mỗi Chủ nhật**, không để dồn. Mục đích không phải báo cáo cho ai — mục đích
là để đến ngày 22/08 khi viết quyển, mọi số liệu và mọi lý do đều truy lại được.
Thiếu weeklog thì cuối tháng phải chạy lại thí nghiệm chỉ để biết mình đã làm gì.

Copy khối mẫu dưới cho mỗi tuần. **Không sửa các tuần đã ghi** — sai thì ghi
dòng đính chính ở tuần sau, đó chính là dữ liệu về quá trình.

---

## MẪU (copy khối này)

### Tuần N · dd/mm → dd/mm

**Trạng thái:** 🟢 đúng tiến độ / 🟡 trượt nhẹ / 🔴 trượt nặng

#### 1. Số liệu mới tuần này
| Chỉ số | Giá trị | Nguồn (file/lệnh) |
|---|---|---|
| | | |

> Chỉ ghi số đã ghi ra file trong `results/`. Số đọc từ terminal rồi chép tay
> là nguồn sai lệch — nếu chưa có file thì ghi "chưa có".

#### 2. Việc đã xong
- [ ]

#### 3. Việc TRƯỢT và lý do thật
- **Việc:** — **Vì sao:** — **Xử lý:**

> Viết lý do thật, không viết "thiếu thời gian". "Cài llmcompressor xung đột
> torch 2.4, mất 6 giờ" là thông tin dùng được; "chậm tiến độ" thì không.

#### 4. Quyết định đã ra
| Quyết định | Lý do | Cái gì bị bỏ |
|---|---|---|

→ Quyết định lớn (đổi hướng, cắt scope) **phải** chép sang `DECISIONS.md`.

#### 5. Bất ngờ về kỹ thuật
Cái gì hoạt động khác dự đoán? Đây là chỗ phát hiện nghiên cứu thường nảy ra —
chính hiện tượng "NF4 làm vỡ văn bản dài" của đề tài này đến từ một dòng ghi chú
tình cờ trong lúc làm việc khác.

#### 6. Rủi ro mới xuất hiện
| Rủi ro | Mức | Xử lý |
|---|---|---|

#### 7. Đếm ngược & đánh giá tỉnh táo
- Còn **__** ngày đến 25/08
- P0 ██████░░░░ __%  · P1 __%  · P2 __%
- Với tốc độ hiện tại, có kịp không? **có / không** — nếu không, cắt gì?

#### 8. Ba việc ưu tiên tuần tới
1.
2.
3.

---

## Tuần 0 · 29/07 → 30/07 (khởi động)

**Trạng thái:** 🟢

#### Số liệu
| Chỉ số | Giá trị | Nguồn |
|---|---|---|
| Hạn nộp | 25/08/2026 17g00 | xác minh qua BTC |
| Ngày còn lại | 27 | — |
| Test suite | 45 passed | `make test` |
| Smoke pipeline | PASSED | `make smoke` |

#### Đã xong
- [x] Chốt đề tài ViEdge-Gov sau khi loại ViJudgeBench (giữ cho SOICT) và MLQA-TSR (dữ liệu bị khoá)
- [x] Xác minh hạn nộp 25/08
- [x] Dựng repo: 45 test xanh, smoke pipeline chạy đầu-cuối trên fixture

#### Quyết định
| Quyết định | Lý do | Cái gì bị bỏ |
|---|---|---|
| Chọn ViEdge-Gov | Không phụ thuộc bên ngoài; dùng đúng thế mạnh nén/đo của team; có bằng chứng sơ bộ sẵn; demo rút mạng | MLQA-TSR, ViJudgeBench |
| Không dùng bnb NF4 làm đường 4-bit chính | Đã đo TPOT 58.3ms vs ~38ms FP8, văn bản dài vỡ nghĩa | — |

#### Ba việc ưu tiên tuần tới
1. Hỏi UTH về suất tiến cử miễn phí
2. Chốt 5 người đứng tên + phân vai
3. Tải corpus + chạy P0
