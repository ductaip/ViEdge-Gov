# Nguồn dữ liệu — tải gì, đặt vào đâu

Xác minh ngày 30/07/2026.

---

## 0. ĐỌC TRƯỚC: hai cái bẫy đã gặp thật

### Bẫy 1 — file `.signed` trên công báo là BẢN SCAN

`238-ndcp.signed.pdf` đã kiểm: **14 trang, 0 ký tự text/trang**, nội dung là ảnh
CCITT 1667×2353. Thứ duy nhất trích ra được là khối metadata chữ ký số.

Quy ước đặt tên trên công báo:
- `*.signed.pdf` / `*nd.signed.pdf` → **ảnh chụp văn bản đã ký** → vô dụng cho NLP
- `*-kem.pdf` (phụ lục "kèm theo") → thường là bản số hoá gốc → dùng được

**Đừng OCR văn bản pháp luật.** Lỗi OCR ở số hiệu văn bản và mức phạt sẽ chui
thẳng vào ViGovQA-GT và vào detector E3 — hỏng đúng thứ đề tài đang đo, mà lại
hỏng âm thầm. Lấy bản **toàn văn HTML** trên `xaydungchinhsach.chinhphu.vn`.

Chạy `make triage` trước để biết file nào dùng được.

### Bẫy 2 — nghị định sửa đổi KHÔNG phải bản hợp nhất

`NĐ 238/2026` chỉ chứa **phần thay đổi**:

> Điều 2. Sửa đổi, bổ sung một số điểm, khoản của Điều 6
> 1. Bổ sung khoản 1a vào trước khoản 1 như sau: "1a. Phạt cảnh cáo…"

Đọc riêng nó gần như vô dụng. Muốn trả lời "không mang GPLX phạt bao nhiêu" thì
cần **NĐ 168/2024 GỐC** — văn bản lớn nhất và quan trọng nhất của cả kho.

Bản hợp nhất chính thức chưa công bố miễn phí (thuvienphapluat/luatvietnam khoá
sau tài khoản trả phí). Ta **không ghép văn bản** — dùng lớp phủ sửa đổi
(`make amend`), xem `src/viedge/data/amendments.py` và ADR-008.

---

## 1. Bảng tải

| # | Văn bản | Lấy ở đâu | Lưu thành |
|---|---|---|---|
| 1 | **NĐ 168/2024/NĐ-CP** (gốc) ⭐ | `xaydungchinhsach.chinhphu.vn` → "Toàn văn Nghị định 168/2024/NĐ-CP" — **HTML, copy thẳng** | `data/raw/nd_168_2024.txt` |
| 2 | **NĐ 238/2026/NĐ-CP** (sửa đổi) | `xaydungchinhsach.chinhphu.vn` HTML *(bản .signed là scan)* | `data/raw/nd_238_2026.txt` |
| 3 | **NĐ 336/2025/NĐ-CP** | `xaydungchinhsach.chinhphu.vn` HTML *(bản .signed là scan)* | `data/raw/nd_336_2025.txt` |
| 4 | **Luật 36/2024/QH15** | 2 file bạn đã có — chạy `make triage` kiểm | `data/raw/luat_36_2024.txt` |
| 5 | **QCVN 41:2024/BGTVT** | `51-bgtvt-kem.pdf` bạn đã có — bản số hoá, **dính chữ**, cần `--learn-from` | `data/raw/qcvn_41_2024.txt` |
| 6 | **TTHC giao thông** | xem mục 2 | `data/raw/tthc_giao_thong.txt` |

⭐ = thiếu thì không có đề tài. Ưu tiên số 1.

**Luật 36/2024 cũng đã bị sửa** bởi **Luật 118/2025/QH15** (căn cứ ghi ngay trong
NĐ 238). Nếu dùng điều luật gốc để trả lời thì phải kiểm điều đó còn nguyên không.

---

## 2. TTHC giao thông — tìm cái gì

Khó tìm vì **thẩm quyền đã chuyển từ Bộ GTVT sang Bộ Công an** trong năm 2025.
Đừng tìm "thủ tục hành chính giao thông" chung chung. Tìm đúng ba nguồn:

### a) Đăng ký xe — nguồn tốt nhất, một văn bản gọn
**Quyết định 1383/QĐ-BCA ngày 28/02/2025** — công bố danh mục TTHC lĩnh vực đăng ký,
quản lý phương tiện giao thông cơ giới, xe máy chuyên dùng, thuộc thẩm quyền Bộ Công an.
Hiệu lực 01/03/2025, thay thế QĐ 9093/QĐ-BCA và QĐ 2609/QĐ-BCA-C08.

Gồm các nhóm thủ tục: cấp mới chứng nhận đăng ký xe và biển số; đổi chứng nhận
đăng ký xe, biển số; thu hồi; đăng ký xe lần đầu trực tuyến toàn trình.

Tìm: `Quyết định 1383/QĐ-BCA 2025 công bố danh mục thủ tục hành chính đăng ký xe`
trên `mps.gov.vn` hoặc `bocongan.gov.vn`.

### b) Giấy phép lái xe — ⚠️ ĐANG BIẾN ĐỘNG
Thông tư 12/2025/TT-BCA (28/02/2025) quy định cấp GPLX, nhưng **vừa bị một thông tư
mới thay thế cuối tháng 7/2026**. Trước khi đưa vào corpus phải xác minh văn bản
nào đang hiệu lực tại ngày chốt corpus.

**Khuyến nghị: tạm để GPLX ra ngoài phạm vi TTHC.** Vẫn giữ các câu hỏi *mức phạt*
liên quan GPLX (nằm trong NĐ 168, ổn định). Lý do: 26 ngày không đủ để theo một
văn bản vừa thay đổi, mà sai thì sai ở phần người dùng tra nhiều nhất.

### c) Cổng dịch vụ công — tra từng thủ tục
`dichvucong.gov.vn`, mục "Tra cứu thủ tục hành chính". Mỗi thủ tục có mã và các
phần chuẩn: Trình tự thực hiện · Thành phần hồ sơ · Thời hạn giải quyết · Lệ phí ·
Căn cứ pháp lý. Đây là nguồn HTML **sạch**, dùng luôn làm mẫu học âm tiết cho
`scripts/00 --learn-from`.

Lọc theo: Cơ quan = Bộ Công an · Lĩnh vực = Đăng ký, quản lý phương tiện giao thông.

⚠️ Một số trang còn văn bản cũ ghi "Sở Giao thông vận tải" — kiểm tay, đừng crawl mù.

### Phạm vi TTHC đề nghị chốt
Lấy **6–10 thủ tục đăng ký xe** theo QĐ 1383/QĐ-BCA. Đủ để trục ứng dụng có câu
chuyện hành chính công thật, không kéo theo rủi ro của mảng GPLX đang đổi.

---
## 3. Vấn đề DÍNH CHỮ trong PDF công báo — đọc trước khi làm

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

## 4. Quy trình, theo thứ tự

```bash
# 0) chuẩn bị
mkdir -p data/raw/pdf
sudo apt-get install -y poppler-utils        # hoặc: pip install pymupdf pdfplumber

# 1) tải 4 PDF vào data/raw/pdf/  (tải tay từ bảng mục 1)

# 2) TTHC trước — nguồn HTML nên SẠCH, dùng làm mẫu học âm tiết cho bước 3
#    Copy nội dung từng thủ tục trên dichvucong.gov.vn vào:
#    data/raw/tthc_giao_thong.txt

# 3) PDF -> txt (học âm tiết từ file sạch ở bước 2)
make triage      # phân loại: file nào scan, file nào dính chữ
python scripts/00_pdf_to_text.py data/raw/pdf/51-bgtvt-kem.pdf \
    --out data/raw/qcvn_41_2024.txt --learn-from data/raw/tthc_giao_thong.txt
# lặp lại cho 3 PDF còn lại

# 4) ĐỌC MẮT 10 ĐIỀU trong mỗi file .txt  ← KHÔNG BỎ QUA
less data/raw/qcvn_41_2024.txt

# 5) mới chạy pipeline
make corpus
make amend          # lớp phủ sửa đổi NĐ 238 -> NĐ 168
make sample
make inspect        # phải xanh trước khi make eval
```

Thứ tự bước 2 trước bước 3 là có chủ ý: bộ tách âm tiết học từ văn bản sạch
cho kết quả tốt hơn hẳn danh sách mồi viết tay.

---

## 5. Kiểm chất lượng sau khi convert

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

## 6. Ba cảnh báo về nội dung

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

## 7. VMLU

- HuggingFace `anhdungitvn/vmlu_v1.5` · repo gốc `github.com/ZaloAI-Jaist/VMLU`
- 10.880 câu trắc nghiệm, 58 môn

```bash
make sample     # chạy 01 rồi 02: tải + lấy mẫu phân tầng 2.000 câu, seed 20260825
make inspect    # kiểm schema + render prompt thử
```

## 8. ViGovQA-GT

Xem `ANNOTATION_GUIDELINE.md`. Mục tiêu 400–600 câu, tối thiểu 300.
Đặt tại `data/vigovqa/vigovqa_gt.jsonl`.

Trường `doc` trong citations phải **trùng từng ký tự** với `id` trong
`configs/retrieval.yaml`. `scripts/10` in cảnh báo phủ gold trước khi tính điểm.

## 9. Bộ calibration

`data/processed/calib_vi.jsonl`, 256 mẫu **tiếng Việt**, mỗi dòng `{"text": "..."}`.
Không dùng C4/WikiText tiếng Anh (ADR-007).

---

## 10. Ranh giới đạo đức & pháp lý

- Chỉ dùng văn bản pháp quy công khai
- Câu hỏi từ cộng đồng: ẩn danh hoá hoàn toàn, không lưu thông tin cá nhân
- Hệ thống luôn hiển thị cảnh báo tham khảo và luôn kèm trích dẫn gốc
- Ghi rõ mốc chốt corpus và nguy cơ trích dẫn văn bản đã hết hiệu lực
