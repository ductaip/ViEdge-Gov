# Nguồn dữ liệu

Nguyên tắc: **mọi nguồn phải tải được ngay, không phụ thuộc ai duyệt.** Đây là
lý do đề tài này khả thi trong 27 ngày còn phương án MLQA-TSR thì không (ADR-002).

---

## 1. Kho văn bản pháp luật → `data/raw/`

| File | Nội dung | Ghi chú |
|---|---|---|
| `luat_36_2024.txt` | Luật Trật tự, an toàn giao thông đường bộ 36/2024/QH15 | 89 điều |
| `qcvn_41_2024.txt` | QCVN 41:2024/BGTVT — Quy chuẩn quốc gia về báo hiệu đường bộ | 313 điều, nhiều bảng và mã hiệu biển báo |
| `nd_xu_phat.txt` | Nghị định xử phạt vi phạm giao thông đang hiệu lực | **Xác minh hiệu lực tại thời điểm chốt corpus** |
| `tthc_giao_thong.txt` | Thủ tục hành chính lĩnh vực giao thông: đăng ký xe, cấp/đổi GPLX | Trích từ CSDL quốc gia về TTHC |

**Chuẩn bị file:**
1. Tải bản văn bản (ưu tiên nguồn công báo/cổng thông tin chính thức)
2. Chuyển sang `.txt` UTF-8, giữ nguyên đánh số `Điều n.` / `n.` / `a)`
3. Xoá header/footer, số trang, watermark
4. Kiểm nhanh: `python -c "from viedge.data.corpus import parse_document; print(len(parse_document(open('data/raw/x.txt').read(),'X')))"`
5. **Đọc bằng mắt 10 điều** để chắc parser không cắt sai — parser tốt trên mẫu
   sạch nhưng văn bản thật luôn có ca lạ

**Bắt buộc ghi lại:** điền `corpus_snapshot_date` trong `configs/retrieval.yaml`.
Hội đồng sẽ hỏi "luật đổi thì sao" — câu trả lời bắt đầu bằng mốc thời gian này.

> ⚠️ `id` văn bản trong `configs/retrieval.yaml` phải **trùng từng ký tự** với
> trường `doc` trong citations của ViGovQA-GT. Lệch một ký tự → F2 = 0 mà không
> báo lỗi. `scripts/10` in cảnh báo phủ gold trước khi tính điểm — đọc nó.

---

## 2. VMLU — bộ đánh giá tiếng Việt

- HuggingFace: `anhdungitvn/vmlu_v1.5`
- Repo gốc: `github.com/ZaloAI-Jaist/VMLU`
- 10.880 câu trắc nghiệm, 58 môn, 4 nhóm (STEM / KHXH / Nhân văn / Khác)

```bash
make sample     # chạy 01 rồi 02: tải + lấy mẫu phân tầng 2.000 câu, seed 20260825
```

Vì sao dùng VMLU: là chuẩn nội địa được cộng đồng VN nhận diện (2024 có 45 LLM
lên bảng xếp hạng, 155 tổ chức gửi yêu cầu đánh giá). Dùng benchmark nội địa
trước hội đồng Việt Nam là điểm cộng miễn phí.

---

## 3. ViGovQA-GT — bộ tự xây → `data/vigovqa/vigovqa_gt.jsonl`

Xem `ANNOTATION_GUIDELINE.md`. Mục tiêu 400–600 câu, tối thiểu 300.

Nguồn câu hỏi:
1. **Câu hỏi thật** từ diễn đàn/nhóm cộng đồng — ẩn danh hoá, **chỉ lấy nội dung
   câu hỏi**, không lấy thông tin cá nhân, không lấy tên người đăng
2. **Sinh bổ sung có kiểm soát** để phủ đều 4 loại câu hỏi và cả single/multi-hop

Ghi rõ tỉ lệ hai nguồn trong báo cáo (trường `source_of_question`).

---

## 4. Bộ calibration → `data/processed/calib_vi.jsonl`

256 mẫu **tiếng Việt**, gồm cả văn bản pháp luật và văn xuôi thường.

**Không dùng C4/WikiText tiếng Anh.** Calib tiếng Anh chọn scale theo phân bố
activation tiếng Anh → tự tay tạo ra chính hiện tượng suy giảm đang đo → hỏng
tính hợp lệ nội tại của thí nghiệm (ADR-007).

Định dạng: mỗi dòng `{"text": "..."}`.

---

## 5. Mô hình

| Tag | HF id | Ưu tiên |
|---|---|---|
| `qwen3.5-2b` | `Qwen/Qwen3.5-2B` | P0 |
| `lfm2.5-1.2b` | `LiquidAI/LFM2.5-1.2B` | P0 |
| `qwen3.5-4b` | `Qwen/Qwen3.5-4B` | P3 |
| `phogpt-4b-chat` | `vinai/PhoGPT-4B-Chat` | P3 — đối chứng mô hình bản địa |

Kiểm tên và bản mới nhất trên HuggingFace trước khi chạy; danh sách trong
`configs/experiments.yaml` là điểm khởi đầu, không phải chân lý.

---

## Ranh giới đạo đức & pháp lý

- Chỉ dùng văn bản pháp quy **công khai**
- Câu hỏi từ cộng đồng: ẩn danh hoá hoàn toàn, không lưu thông tin cá nhân
- Hệ thống **luôn** hiển thị cảnh báo tham khảo và **luôn** kèm trích dẫn gốc
- Ghi rõ trong báo cáo: nguy cơ trích dẫn văn bản đã hết hiệu lực và cách xử lý
- Không thu thập dữ liệu người dùng trong bản demo
