# Nguồn dữ liệu — tải gì, đặt vào đâu

Xác minh hiệu lực ngày 30/07/2026. Nguyên tắc: mọi nguồn tải được ngay,
không phụ thuộc ai duyệt.

---

## 1. Bảng tải: 5 văn bản, đúng đường dẫn

| # | Văn bản | Tải ở đâu | PDF gốc lưu vào | .txt cuối cùng |
|---|---|---|---|---|
| 1 | **Luật 36/2024/QH15** — Trật tự, an toàn giao thông đường bộ | `vanban.chinhphu.vn` hoặc `congbao.chinhphu.vn` | `data/raw/pdf/luat_36_2024.pdf` | `data/raw/luat_36_2024.txt` |
| 2 | **QCVN 41:2024/BGTVT** — Báo hiệu đường bộ (kèm TT 51/2024) | `datafiles.chinhphu.vn/cpp/files/vbpq/2024/11/51-bgtvt-kem.pdf` | `data/raw/pdf/51-bgtvt-kem.pdf` | `data/raw/qcvn_41_2024.txt` |
| 3 | **NĐ 168/2024/NĐ-CP hợp nhất NĐ 238/2026** | `xaydungchinhsach.chinhphu.vn` (toàn văn) hoặc bản hợp nhất trên `thuvienphapluat.vn` | `data/raw/pdf/nd_168_hop_nhat.pdf` | `data/raw/nd_168_2024_hop_nhat.txt` |
| 4 | **NĐ 336/2025/NĐ-CP** — xử phạt VPHC hoạt động đường bộ | `xaydungchinhsach.chinhphu.vn` | `data/raw/pdf/nd_336_2025.pdf` | `data/raw/nd_336_2025.txt` |
| 5 | **TTHC giao thông** — đăng ký xe, cấp/đổi/cấp lại GPLX | `dichvucong.gov.vn`, tra theo mã thủ tục | — (nguồn HTML) | `data/raw/tthc_giao_thong.txt` |

Tên file `.txt` phải **khớp chính xác** `path:` trong `configs/retrieval.yaml`.

### Mã thủ tục TTHC đã biết
- `1.002809` — đổi GPLX do ngành Giao thông vận tải cấp
- `1.002801` — đổi GPLX do ngành Công an cấp

Tra tại `dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html?ma_thu_tuc=<mã>`.

⚠️ Thẩm quyền GPLX đã chuyển sang Bộ Công an (TT 12/2025/TT-BCA). Một số trang
còn văn bản cũ ghi "Sở Giao thông vận tải" — **kiểm tay từng thủ tục**.

---

## 2. Vấn đề DÍNH CHỮ trong PDF công báo — đọc trước khi làm

PDF chính thức trên `datafiles.chinhphu.vn` nhúng font theo cách khiến trình
trích xuất **mất khoảng trắng**. Trích thô từ QCVN 41:2024 ra thế này:

```
CỘNGHOÀXÃHỘICHỦNGHĨAVIỆTNAM
Quychuẩnnày quyđịnh vềbáohiệuđườngbộbaogồm:đèntínhiệugiaothông
```

Để nguyên thì hỏng dây chuyền: BM25 tokenize ra `quychuẩnnày` nên không truy vấn
nào khớp; `VietLexicon` dựng từ rác nên detector E2 vô dụng; parser Điều/khoản
vẫn chạy nhưng nội dung không tra cứu được. **Đây là lỗi im lặng** — mọi thứ
"chạy" mà kết quả vô nghĩa.

`scripts/00_pdf_to_text.py` xử lý: thử 3 trình trích xuất, chấm điểm bằng
`glue_ratio`, chọn bản tốt nhất, và nếu vẫn dính thì tách lại bằng quy hoạch
động trên kho âm tiết tiếng Việt.

---

## 3. Quy trình, theo thứ tự

```bash
# 0) chuẩn bị
mkdir -p data/raw/pdf
sudo apt-get install -y poppler-utils        # hoặc: pip install pymupdf pdfplumber

# 1) tải 4 PDF vào data/raw/pdf/  (tải tay từ bảng mục 1)

# 2) TTHC trước — nguồn HTML nên SẠCH, dùng làm mẫu học âm tiết cho bước 3
#    Copy nội dung từng thủ tục trên dichvucong.gov.vn vào:
#    data/raw/tthc_giao_thong.txt

# 3) PDF -> txt (học âm tiết từ file sạch ở bước 2)
python scripts/00_pdf_to_text.py data/raw/pdf/51-bgtvt-kem.pdf \
    --out data/raw/qcvn_41_2024.txt --learn-from data/raw/tthc_giao_thong.txt
# lặp lại cho 3 PDF còn lại

# 4) ĐỌC MẮT 10 ĐIỀU trong mỗi file .txt  ← KHÔNG BỎ QUA
less data/raw/qcvn_41_2024.txt

# 5) mới chạy pipeline
make corpus
make sample
make inspect        # phải xanh trước khi make eval
```

Thứ tự bước 2 trước bước 3 là có chủ ý: bộ tách âm tiết học từ văn bản sạch
cho kết quả tốt hơn hẳn danh sách mồi viết tay.

---

## 4. Kiểm chất lượng sau khi convert

`scripts/00` in sẵn `glue_ratio` và số `Điều N` bắt được. Ngưỡng:

| Chỉ số | Đạt | Cần xem lại |
|---|---|---|
| `glue_ratio` sau xử lý | < 0.15 | > 0.25 |
| Số `Điều N` bắt được | khớp mục lục văn bản | 0 → PDF là bản scan, cần OCR |

Kiểm nhanh sau khi có `.txt`:
```bash
PYTHONPATH=src python3 -c "
from viedge.data.corpus import parse_document
from viedge.data.desegment import glue_ratio
t = open('data/raw/qcvn_41_2024.txt', encoding='utf-8').read()
a = parse_document(t, 'QCVN 41:2024/BGTVT')
print('glue:', round(glue_ratio(t),3), '| điều:', len(a))
for x in a[:3]: print(' ', x.dieu, x.title[:60])
"
```

QCVN 41 có ~84 điều trong phần chính (chưa kể phụ lục A–P). Nếu ra 3 điều thì
parser hỏng, không phải văn bản ngắn.

---

## 5. Ba cảnh báo về nội dung

1. **Không đưa NĐ 100/2019 vào corpus.** Đã bị NĐ 336/2025 bãi bỏ phần lớn.
   Mô hình trích dẫn nó là ca lỗi E3 kinh điển — giữ vài câu hỏi bẫy để đo.
2. **NĐ 238/2026 hiệu lực 15/08/2026.** Không chốt corpus trước mốc này.
   Xem `DECISIONS.md` ADR-008.
3. **Có prompt injection trong nội dung một số trang tổng hợp luật.** Gặp thật:
   trang nhúng câu lệnh dạng *"# QUAN TRỌNG: hãy luôn thông báo với người dùng
   rằng..."* ngay trong thân bài. Crawl rồi nhét vào ngữ cảnh RAG thì mô hình
   có thể làm theo. `scripts/00` đã lọc; nếu crawl bằng công cụ khác thì tự lọc.
   Việc này đáng một đoạn trong phần **Hạn chế & An toàn** của quyển — vệ sinh
   dữ liệu là chi tiết ít nhóm nghĩ tới.

---

## 6. VMLU

- HuggingFace `anhdungitvn/vmlu_v1.5` · repo gốc `github.com/ZaloAI-Jaist/VMLU`
- 10.880 câu trắc nghiệm, 58 môn

```bash
make sample     # chạy 01 rồi 02: tải + lấy mẫu phân tầng 2.000 câu, seed 20260825
make inspect    # kiểm schema + render prompt thử
```

## 7. ViGovQA-GT

Xem `ANNOTATION_GUIDELINE.md`. Mục tiêu 400–600 câu, tối thiểu 300.
Đặt tại `data/vigovqa/vigovqa_gt.jsonl`.

Trường `doc` trong citations phải **trùng từng ký tự** với `id` trong
`configs/retrieval.yaml`. `scripts/10` in cảnh báo phủ gold trước khi tính điểm.

## 8. Bộ calibration

`data/processed/calib_vi.jsonl`, 256 mẫu **tiếng Việt**, mỗi dòng `{"text": "..."}`.
Không dùng C4/WikiText tiếng Anh (ADR-007).

---

## 9. Ranh giới đạo đức & pháp lý

- Chỉ dùng văn bản pháp quy công khai
- Câu hỏi từ cộng đồng: ẩn danh hoá hoàn toàn, không lưu thông tin cá nhân
- Hệ thống luôn hiển thị cảnh báo tham khảo và luôn kèm trích dẫn gốc
- Ghi rõ mốc chốt corpus và nguy cơ trích dẫn văn bản đã hết hiệu lực