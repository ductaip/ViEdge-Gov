# ViEdge-Gov

**Đo lường suy giảm chất lượng tiếng Việt khi nén mô hình ngôn ngữ nhỏ, và xây dựng trợ lý hỏi đáp thủ tục hành chính – pháp luật giao thông chạy ngoại tuyến trên phần cứng phổ thông**

> Đề tài dự thi **Giải thưởng Sinh viên Nghiên cứu khoa học Euréka lần XXVIII – 2026**
> Lĩnh vực: **Công nghệ thông tin** · Hạn nộp: **17g00 ngày 25/08/2026** · Nộp mục tiêu: **24/08**

```
make setup && make smoke      # kiểm repo lành mạnh (5 phút, không cần GPU)
```

---

## 1. Đề tài một trang

**Chúng ta không cạnh tranh ở "mô hình chính xác hơn."** Chúng ta cạnh tranh ở một
ràng buộc triển khai chưa ai đo lường nghiêm túc cho tiếng Việt: khi nén một mô
hình ngôn ngữ nhỏ xuống đủ nhỏ để chạy tại chỗ trên máy văn phòng không GPU,
**tiếng Việt hỏng bao nhiêu, và hỏng ở đâu?**

Ba trục:

| Trục | Nội dung | Điểm rubric nhắm tới |
|---|---|---|
| **A – Nghiên cứu** | Đo + phân loại suy giảm tiếng Việt theo mức nén | 20đ tính mới + 30đ nội dung/PPNC |
| **B – Ứng dụng** | Trợ lý RAG hỏi đáp TTHC & luật giao thông, chạy **offline** trên CPU | 10đ mục đích/ứng dụng |
| **C – Khuyến nghị** | Bảng cấu hình triển khai cho cơ quan cấp xã | **20đ giải pháp/kiến nghị** |

20đ còn lại là hình thức trình bày và trích dẫn — **điểm miễn phí, không mất một điểm nào.**

## 2. Câu chuyện (bản 60 giây cho hội đồng)

Chuyển đổi số cấp xã theo Nghị quyết 57 đang triển khai. Cán bộ và người dân cần
tra cứu thủ tục — đăng ký xe, cấp đổi GPLX, mức xử phạt.

Mọi giải pháp hiện nay gọi API của mô hình đặt ở nước ngoài: **dữ liệu công dân
rời khỏi biên giới**, và nơi hạ tầng mạng yếu thì không dùng được.

Giải pháp là mô hình nhỏ chạy tại chỗ. Để chạy được, phải nén. **Và chưa ai đo
được nén xong thì tiếng Việt còn lại bao nhiêu.**

## 3. Vì sao câu hỏi này có cơ sở

1. **Nén đánh vào đặc trưng đuôi dài.** Marchisio et al. (2024): nén khuếch đại
   đối xử bất bình đẳng với đặc trưng đuôi dài, gây hệ quả cho ngôn ngữ ít được
   đại diện; và công trình về lượng tử hoá hầu như chỉ đánh giá trên tiếng Anh.
2. **Chỉ số tự động che giấu thiệt hại.** Cùng nghiên cứu: mức giảm 1,7% trên tác
   vụ tự động với tiếng Nhật tương ứng **16,0%** khi người đánh giá chấm.
3. **Tiếng Việt nằm đúng vùng nguy hiểm.** Cần ~4× số token so với tiếng Anh với
   tokenizer phổ thông → dấu bị chẻ thành sub-word tần suất thấp.
4. **Bằng chứng sơ bộ của chính nhóm.** Trong chiến dịch tối ưu suy luận trước đó:
   bnb NF4 trên một SLM làm **văn bản ngữ cảnh dài vỡ nghĩa**, TPOT 58,3ms vs
   ~38ms của FP8; nhiều cấu hình gặp hiện tượng **vỡ dấu**. Ta đã *thấy* hiện
   tượng — đề tài này biến nó thành số.

## 4. Câu hỏi nghiên cứu

| # | Câu hỏi | Bảng đầu ra |
|---|---|---|
| RQ1 | Nén BF16→FP8→INT8→INT4 làm tiếng Việt tụt bao nhiêu? Đường cong có khác tiếng Anh? | Bảng 3 |
| RQ2 | Suy giảm xảy ra **ở đâu**? | **Bảng 4 + 5 — trái tim đề tài** |
| RQ3 | RAG bù lại được bao nhiêu? | Bảng 6 |
| RQ4 | Điểm vận hành tối ưu cho máy cấp xã? | Bảng 7 |

**RQ2 là trục sống còn.** Ai cũng đo được RQ1; taxonomy lỗi tiếng Việt là thứ
chưa ai có.

## 5. Đóng góp tuyên bố

1. Nghiên cứu hệ thống **đầu tiên** về suy giảm tiếng Việt dưới nén mô hình, trên
   dải SLM và bốn mức chính xác số học.
2. **Taxonomy 6 loại lỗi tiếng Việt do nén** (E1–E6), kèm phân bố định lượng.
3. **ViGovQA-GT** — bộ đánh giá 400–600 câu TTHC & pháp luật giao thông, có trích
   dẫn nguồn, phát hành mở kèm DOI.
4. **Hệ thống chạy hoàn toàn ngoại tuyến** trên máy không GPU + bản khuyến nghị
   cấu hình triển khai.

---

## 5b. Cấu hình đã chốt (06/08/2026)

**Hai model P0, khác họ kiến trúc.** Cả hai đã qua cửa sàng trần tiếng Việt
(`make screen`) — bảng sàng ở `results/tables/model_screening.json`, đưa vào phụ lục quyển.

| Model | Họ | Accuracy BF16 | Headroom | VRAM | Biên tụt (n=1047) |
|---|---|---|---|---|---|
| `Qwen/Qwen2.5-1.5B-Instruct` | Qwen | 52,0% | +26,8đ | 2,88 GB | 24,6 điểm |
| `google/gemma-3-1b-it` | Gemma | 39,5% | +14,3đ | 1,87 GB | 12,1 điểm |

**Thang nén 4 bậc:** `bf16` (tham chiếu) → `int8` (W8A8) → `int4_awq` (W4A16) → `gguf_q4_k_m` (CPU).

FP8 **không** nằm trong thang chính: RTX 3050 là SM 8.6, dưới ngưỡng 8.9 mà FP8
W8A8 cần; dưới ngưỡng thì vLLM âm thầm rơi về W8A16 và ta đo nhầm sơ đồ khác (ADR-011).

**Bộ đánh giá:** VMLU **1.047 câu** có đáp án (dev 303 + valid 744, phủ đủ 58 môn).
9.833 câu test không có đáp án — dùng riêng để đo flip rate so với BF16 (ADR-016).
Mức đoán mò thực tế **0,2532**, không phải 0,25, vì số lựa chọn thay đổi theo câu.

> ⚠️ **Hạn chế phải ghi trong quyển:** hai model khác *cả kiến trúc lẫn kích thước*
> (1,5B vs 1,0B). Không quy toàn bộ chênh lệch cho kiến trúc.

Lịch sử chọn model: `docs/DECISIONS.md` ADR-011, 012, 017, 018, 019.

## 6. Cấu trúc repo

```
configs/          experiments.yaml (ma trận P0–P4) · retrieval.yaml (corpus, retriever)
docs/             PLAN · WEEKLOG · DECISIONS · ERROR_TAXONOMY
                  ANNOTATION_GUIDELINE · REPORT_OUTLINE · SUBMISSION_CHECKLIST
                  DATA_SOURCES · SETUP
src/viedge/
  vitext.py       Xử lý dấu tiếng Việt, phát hiện mojibake, từ vựng từ corpus
  data/           vmlu (lấy mẫu phân tầng) · corpus (parser điều/khoản/điểm) · vigovqa (schema)
  quant/          export (BF16/FP8/INT8/INT4/GGUF)
  eval/           runner (bọc lm-eval) + bảng suy giảm
  taxonomy/       detectors (E1–E6) · agreement (AC1, kappa, bootstrap CI)
  rag/            citations · retrieval (BM25+dense+RRF+top-k động) · pipeline
  serve/          app (demo offline, gradio hoặc CLI)
  bench/          latency (TTFT/tok-s/RAM trên CPU)
scripts/          01…12 theo thứ tự pipeline · 99_smoke_all.py
tests/            45 test
results/tables/   REPORT_TABLES.md — bảng dán trực tiếp vào quyển
logs/runlog.jsonl mọi lần chạy thật
```

## 7. Thứ tự chạy

```bash
make smoke                          # 0. kiểm repo (fixture, không cần GPU)
make corpus                         # 1. văn bản -> điều/khoản/điểm      -> Bảng 1
make sample                         # 2. VMLU lấy mẫu phân tầng          -> Bảng 2
DRY=1 make export && make export    # 3. xuất các mức nén (review lệnh trước!)
make eval                           # 4. VMLU                            -> Bảng 3 (RQ1)
make probe                          # 5. sinh tự do -> hàng đợi gán nhãn
#   ... gán nhãn thủ công: scripts/07, HAI NGƯỜI ĐỘC LẬP ...
make agreement                      # 6. AC1 + hiệu chuẩn detector       -> Bảng 4,5 (RQ2)
make index && make rag              # 7. truy hồi                        -> Bảng 6 (RQ3)
make bench                          # 8. CPU (chạy trên máy thật!)       -> Bảng 7 (RQ4)
make tables                         # 9. gom mọi bảng
make demo                           # 10. demo offline
```

## 8. Bảy điều dễ làm sai — đọc trước khi chạy

| # | Cạm bẫy | Hậu quả |
|---|---|---|
| 1 | Calibration bằng C4/WikiText **tiếng Anh** | Tự tạo ra chính hiện tượng đang đo → **hỏng tính hợp lệ thí nghiệm** (ADR-007) |
| 2 | Hai người gán nhãn không độc lập | AC1 vô nghĩa → hội đồng loại cả phần phân tích |
| 3 | `id` văn bản lệch trường `doc` trong citations | F2 = 0 mà không báo lỗi *(scripts/10 có cửa kiểm — đọc nó)* |
| 4 | Đo hiệu năng trên T4 rồi báo cáo | Luận điểm "chạy được ở cấp xã" mất căn cứ |
| 5 | Dùng bnb NF4 làm đường 4-bit chính | Chậm ~50% và vỡ văn bản dài (ADR-005) |
| 6 | Chép số từ terminal vào quyển bằng tay | Số trong bảng lệch số trong thân văn — hội đồng phát hiện |
| 7 | Quên ẩn danh metadata PDF | Vi phạm quy định chấm phản biện độc lập |

## 8b. Chạy trên GPU thuê (Modal)

```bash
pip install modal && modal setup
modal secret create huggingface HF_TOKEN=hf_...
make modal-doctor      # xác nhận SM 8.9 -> FP8 chạy được
make modal-export DRY=1 && make modal-export
make modal-eval && make modal-pull
```

L4 là SM 8.9 nên **chạy được FP8** — bậc mà RTX 3050 (SM 8.6) không chạy được.
Thang nén từ 4 bậc thành 5.

⚠️ **Bảng 7 (độ trễ) vẫn BẮT BUỘC đo trên CPU laptop.** Đo trên L4 rồi báo cáo
"chạy được ở cấp xã" là mất căn cứ toàn bộ trục ứng dụng.

Chi tiết, chi phí và quy tắc nhất quán phần cứng: `docs/MODAL.md`, ADR-020.

## 9. Tài nguyên

| Tài nguyên | Dùng cho |
|---|---|
| Kaggle T4 ×2 (free) | Toàn bộ P0–P2. Đủ dùng — đề tài không tranh GPU với việc khác |
| Máy CPU cá nhân | Bảng 7 + demo. **Ghi rõ cấu hình vào quyển** |
| Modal L4 (SM 8.9) | Job dài + **bậc FP8** mà RTX 3050 không chạy được. Xem `docs/MODAL.md`. **Không** tạo nhiều tài khoản lách hạn mức |

## 10. Nhịp làm việc

- **Chủ nhật: ghi `docs/WEEKLOG.md`.** Không để dồn. Thiếu weeklog thì đến 22/08
  phải chạy lại thí nghiệm chỉ để biết mình đã làm gì.
- Mọi quyết định có đánh đổi → `docs/DECISIONS.md`. Mục "vì sao chọn cách này"
  trong quyển lấy trực tiếp từ đây.
- `make tables` trước khi viết mỗi chương.
- Ranh giới cắt scope đã quyết trước: **hết 13/08 chưa có phân bố lỗi RQ2 → cắt
  P3 và P4**, dồn lực vào taxonomy + hệ thống + quyển.

## 11. Nhắc nhở tỉnh táo

Ở Euréka, khoảng cách giữa giải khuyến khích và giải ba nằm ở **quyển báo cáo và
phần demo**, không nằm ở thuật toán. 97% đề tài bị loại ở bán kết — nơi hội đồng
chỉ đọc giấy, không thấy code.

Xác suất thô cho "giải ba trở lên" khoảng **2,3%** (51/2.179 đề tài năm 2025).
Mục tiêu vận hành: **vào 3% chung kết**, rồi mới nói thứ hạng. Không ai đảm bảo
được hơn thế, và tin ngược lại sẽ dẫn tới quyết định sai.

**Đừng đổi đề tài nữa.** Mỗi ngày dành cho việc so sánh đề tài là một ngày mất
khỏi thời gian thi công.

---

## Tài liệu

| File | Đọc khi nào |
|---|---|
| `docs/PLAN.md` | **Bắt đầu ở đây** — roadmap từng ngày |
| `docs/SETUP.md` | Cài môi trường, cạm bẫy phiên bản |
| `docs/DATA_SOURCES.md` | Chuẩn bị dữ liệu |
| `docs/ERROR_TAXONOMY.md` | Trước khi gán nhãn |
| `docs/ANNOTATION_GUIDELINE.md` | Trước khi gán mẫu đầu tiên |
| `docs/REPORT_OUTLINE.md` | Khi viết quyển + luyện phản biện |
| `docs/SUBMISSION_CHECKLIST.md` | Tuần 4 |
| `docs/DECISIONS.md` | Khi cần biết vì sao chọn cách này |
| `docs/WEEKLOG.md` | **Mỗi Chủ nhật** |
