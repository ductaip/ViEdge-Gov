# Nhật ký quyết định (ADR)

Chỉ ghi quyết định **có đánh đổi**. Không ghi việc thường ngày.
Hội đồng bán kết đánh giá cao báo cáo thể hiện được quá trình ra quyết định —
mục "Vì sao chọn cách này mà không chọn cách kia" trong quyển lấy trực tiếp từ đây.

Mẫu: `## ADR-nnn · dd/mm · <tiêu đề>` + Bối cảnh / Quyết định / Phương án đã loại / Hệ quả.

---

## ADR-001 · 29/07 · Không dùng ViJudgeBench cho Euréka

**Bối cảnh.** ViJudgeBench đã có codebase và kết quả sơ bộ, dùng lại sẽ tiết kiệm nhiều tuần.

**Quyết định.** Giữ riêng cho SOICT 2026. Euréka làm đề tài khác.

**Phương án đã loại.** Dùng chung một công trình cho hai đích.

**Hệ quả.** Mất lợi thế tái sử dụng, phải làm đề tài mới trong 27 ngày. Đổi lại
không loãng cả hai và không rắc rối về trùng lặp công bố.

---

## ADR-002 · 29/07 · Loại phương án MLQA-TSR (hỏi đáp biển báo đa phương thức)

**Bối cảnh.** VLSP 2025 MLQA-TSR có dữ liệu đã gán nhãn sẵn, có baseline công bố
(F2 truy hồi 64,55%; accuracy QA 86,30%) — rất hợp để so sánh định lượng.

**Quyết định.** Loại.

**Lý do.**
1. Dữ liệu bị khoá sau agreement form gửi email tác giả duyệt → **khâu không kiểm soát được thời gian** trong sprint 27 ngày.
2. Mảng pháp luật tiếng Việt đã bão hoà: DRiLL, LegalSLM, MLQA-TSR (riêng VLSP 2025), cộng ALQAC, VLegal-Bench, ViHERMES — trong đó ViHERMES đã chiếm góc truy vết sửa đổi/hiệu lực.
3. Phản biện "nhóm chỉ chạy lại bộ dữ liệu của người khác" khó gỡ.

**Hệ quả.** Mất baseline công bố để so. Bù lại bằng: mốc tham chiếu BF16 nội bộ +
đối chứng API + bộ dữ liệu tự xây.

---

## ADR-003 · 29/07 · Chốt ViEdge-Gov

**Bối cảnh.** Cần đề tài khả thi 27 ngày, dùng được thế mạnh thật của team
(nén/đo suy luận, retrieval, phương pháp đánh giá), có câu chuyện ứng dụng.

**Quyết định.** Đo suy giảm chất lượng tiếng Việt dưới nén mô hình + trợ lý
hỏi đáp TTHC/giao thông chạy ngoại tuyến trên CPU.

**Vì sao khả thi.**
- Corpus công khai, tải ngay, **không phụ thuộc ai duyệt**
- Harness lm-eval 0.4.12 + Modal đã chạy thông từ chiến dịch Viettel → delta ~1 ngày
- Đã có **bằng chứng sơ bộ**: NF4 làm văn bản ngữ cảnh dài vỡ nghĩa
- Nền lý thuyết sẵn: Marchisio et al. (2024) về nén và ngôn ngữ ít tài nguyên
- Không tranh GPU với fork vLLM của Viettel

**Rủi ro chấp nhận.** Không có baseline ngoài để so; phải tự xây bộ đánh giá.

---

## ADR-004 · 29/07 · AC1 (Gwet) làm chỉ số đồng thuận chính

**Bối cảnh.** Taxonomy lỗi có prevalence rất lệch (E1 có thể chỉ ~2-3% mẫu).

**Quyết định.** AC1 là chỉ số chính; Cohen's kappa báo cáo kèm.

**Lý do.** Kappa sụp về gần 0 khi prevalence lệch dù hai người đồng ý gần hoàn
toàn (nghịch lý kappa). Đã kiểm bằng test: ở 95% đồng thuận thô, AC1 = 0.936
còn kappa chỉ 0.773 (`tests/test_agreement.py::test_kappa_paradox_ac1_more_stable`).

**Hệ quả.** Phải giải thích được trong 1 câu khi phản biện hỏi "vì sao không dùng kappa".

---

## ADR-005 · 29/07 · Không dùng bitsandbytes NF4 làm đường 4-bit chính

**Bối cảnh.** bnb NF4 là cách 4-bit phổ biến nhất trong tutorial.

**Quyết định.** Đường 4-bit chính = AWQ (GPU) + GGUF Q4_K_M (CPU). Giữ **một** lượt
bnb NF4 làm đối chứng "cách làm phổ biến nhưng sai".

**Lý do (đo được).** TPOT 58,3ms vs ~38ms của FP8 — chậm ~50% vì chi phí dequant
ăn hết phần tiết kiệm băng thông; và văn bản ngữ cảnh dài bắt đầu vỡ nghĩa.

**Hệ quả.** Lượt đối chứng bnb trở thành một điểm thảo luận có giá trị thay vì
một thất bại bị che.

---

## ADR-006 · 29/07 · Cắt chunk theo điều/khoản/điểm, không theo số token

**Bối cảnh.** RAG thông thường cắt theo cửa sổ token.

**Quyết định.** Đơn vị truy hồi bám cấu trúc pháp lý, giữ metadata phân cấp.

**Lý do.** "Khoản 3 Điều 22" là địa chỉ pháp lý, không phải đoạn văn tuỳ ý. Cắt
theo token làm mất địa chỉ → mất khả năng sinh trích dẫn kiểm chứng được → mất
luôn cơ chế chống lỗi E3.

**Hệ quả.** Một số điều rất dài vượt ngân sách ngữ cảnh; xử lý ở ADR-009.

---

## ADR-007 · 29/07 · Calibration quantization phải bằng tiếng Việt

**Bối cảnh.** Mặc định của phần lớn công cụ nén là calibrate bằng C4/WikiText tiếng Anh.

**Quyết định.** Bộ calib 256 mẫu **tiếng Việt**, có văn bản pháp luật.

**Lý do.** Calib tiếng Anh chọn scale theo phân bố activation tiếng Anh → tự tay
tạo ra chính hiện tượng suy giảm đang đo → **hỏng tính hợp lệ nội tại của thí nghiệm**.

**Hệ quả (cơ hội).** So calib EN vs VI ở cùng mức nén là thí nghiệm P4. Nếu chênh
lớn, đó là một phát hiện độc lập và một khuyến nghị kỹ thuật rất cụ thể.

---

## ADR-008 · 30/07 · Xử lý việc Nghị định 238/2026 có hiệu lực 15/08, giữa kỳ làm đề tài

**Bối cảnh.** Nghị định 238/2026/NĐ-CP (ban hành 26/06/2026) sửa đổi Nghị định
168/2024/NĐ-CP, **hiệu lực 15/08/2026** — 10 ngày trước hạn nộp, đúng Tuần 3.
Trước đó rủi ro "văn bản pháp luật thay đổi giữa chừng" được đánh giá là thấp.
**Đánh giá đó SAI:** đây không phải rủi ro, đây là điều chắc chắn xảy ra.

Ngoài ra Nghị định 336/2025/NĐ-CP (hiệu lực 01/03/2026) đã bãi bỏ một số điều
của NĐ 100/2019, 123/2021 và 168/2024.

**Quyết định.**
1. Giữ NĐ 168 **bản gốc**; phần sửa đổi nạp riêng qua lớp phủ (`make amend`).
2. Không ghép văn bản: Điều 19 của NĐ 238 có 17 thao tác ở mức CỤM TỪ, tự động
   áp dụng là một đề tài riêng, sai một thao tác thì mức phạt sai âm thầm.
3. Công tắc `as_of` bật/tắt lớp phủ theo ngày → chạy đối chứng **độ trễ pháp lý**:
   cùng bộ câu hỏi trên corpus trước/sau 15/08, báo cáo tỉ lệ câu đổi kết quả.
4. NĐ 100/2019 **không** vào corpus dưới bất kỳ hình thức nào.

**Vì sao biến rủi ro thành thí nghiệm.** Câu phản biện số 5 trong
`REPORT_OUTLINE.md` là "corpus chốt ở một thời điểm, luật đổi thì sao". Trả lời
bằng lý thuyết thì yếu; trả lời bằng **số đo trên một lần sửa luật có thật, xảy
ra trong lúc làm đề tài** thì mạnh hơn hẳn — và đó là thứ đề tài nào cũng gặp
nhưng không đề tài nào đo.

**Hệ quả vận hành.** Không chốt corpus trước 15/08. Tải bản cập nhật 15–16/08,
chạy lại `make corpus` + `make amend` + `make index`, rồi mới đóng băng ViGovQA-GT.
Mọi câu hỏi loại `muc_phat` phải xác minh lại sau mốc này.

---

## ADR-009 · 04/08 · Đơn vị truy hồi HAI CẤP (điều + khoản)

**Bối cảnh.** ADR-006 chốt cắt theo điều/khoản/điểm, nhưng bản cài đặt đầu tiên
chỉ tạo đơn vị ở cấp ĐIỀU. Đo trên NĐ 168/2024 thật:

| Chỉ số | Giá trị |
|---|---|
| Median kích thước điều | 2.109 ký tự |
| p90 | 11.273 |
| Max (Điều 32) | **30.137** |
| Số điều > 6.000 ký tự | 13/55 |

Ngân sách ngữ cảnh 6.000 ký tự chứa vừa **2 điều nhỏ**, và **không bao giờ** chứa
nổi Điều 6 (18.771) hay Điều 32 (30.137) — đúng những điều chứa mức phạt người
dân hỏi nhiều nhất.

**Lỗi này im lặng.** Pipeline vẫn chạy, mô hình vẫn trả lời, chỉ là trả lời không
hề nhìn thấy căn cứ. Không cửa kiểm nào bắt được vì không có exception.

**Quyết định.** Điều ngắn (≤ `unit_max_chars`) giữ nguyên một đơn vị; điều dài
tách theo khoản, mỗi khoản **mang theo header của điều**.

Header đi kèm vì hai lý do: giữ địa chỉ pháp lý đầy đủ (khoản cũng là địa chỉ hợp
lệ, không vi phạm ADR-006), và giữ tín hiệu từ khoá của tiêu đề cho BM25 — khoản
rời rạc mất ngữ cảnh "xe ô tô" / "xe mô tô" thì truy hồi sai loại xe.

**Kết quả trên corpus thật.** 55 đơn vị → 211 đơn vị; max 30.137 → 8.322 ký tự;
median 1.006.

**Hệ quả bắt buộc.** Gold trong ViGovQA-GT ghi ở cấp ĐIỀU, nên:
- `scripts/10` quy đơn vị khoản về điều trước khi chấm, khử trùng giữ thứ tự hạng
- `AmendmentIndex.for_unit()` quy về cấp điều trước khi tra — không có bước này
  thì đúng những điều dài nhất (cũng là hay bị sửa nhất) không nhận được lớp phủ

---

## ADR-010 · 04/08 · dynamic_top_k phải cắt theo điểm gốc khi chỉ có một retriever

**Bối cảnh.** Chạy thật với BM25 đơn lẻ (chưa cài `sentence-transformers`),
`dynamic_top_k` luôn trả về đúng `max_k` = 10, không bao giờ cắt.

**Nguyên nhân.** Với MỘT run, điểm RRF = `1/(k+rank)` là hàm đơn điệu của hạng.
Tỉ lệ điểm cuối/đầu ≈ `(k+1)/(k+max_k)` = 61/70 ≈ 0,87 — luôn lớn hơn
`drop_ratio` 0,55, nên điều kiện cắt không bao giờ đúng.

**Quyết định.** Khi chỉ có một run, cắt theo **điểm gốc của retriever** đó (BM25
có dải điểm thật, phân biệt được liên quan/không). Từ hai run trở lên mới dùng RRF.

**Vì sao đáng ghi ADR.** Đây là loại lỗi làm hỏng **luận điểm của đề tài**, không
chỉ hỏng code: bảng RQ3 định chứng minh "top-k động tốt hơn top-k cố định", mà với
cấu hình lỗi thì top-k động **chính là** top-k cố định = 10. Kết luận sẽ sai mà số
liệu vẫn đẹp.

---

## ADR-011 · 05/08 · Bỏ FP8 khỏi ma trận chính, dùng thang BF16 → INT8 → INT4 → GGUF

**Bối cảnh.** Phần cứng của nhóm là **RTX 3050 6GB (Ampere, SM 8.6)**; dự phòng là
Kaggle **T4 (Turing, SM 7.5)**.

Tài liệu vLLM: tính toán FP8 W8A8 chỉ được hỗ trợ native trên compute capability
**≥ 8.9** (Ada Lovelace, Hopper). Dưới ngưỡng đó, mô hình FP8 **vẫn chạy** nhưng
rơi về **W8A16 weight-only qua kernel Marlin**.

**Đây là cái bẫy nguy hiểm nhất từ đầu dự án**, vì:
- W8A8 lượng tử hoá **cả activation**; W8A16 thì **không**. Hai sơ đồ khác nhau.
- vLLM **không báo lỗi**, chỉ lặng lẽ đổi kernel.
- Nếu ghi kết quả đó vào Bảng 3 dưới nhãn "FP8", ta báo cáo con số của một sơ đồ
  nén khác dưới tên FP8. Sai về khoa học, mà **không có cách nào phát hiện từ số liệu**.

Nói cách khác: chính đề tài nghiên cứu về suy giảm âm thầm, suýt nữa dính một ca
suy giảm âm thầm ngay trong thiết kế thí nghiệm của mình.

**Quyết định.** Thang chính đổi thành **BF16 → INT8 (W8A8) → INT4 (W4A16) → GGUF Q4_K_M**.

Bốn bậc, đều chạy native trên SM 8.6, và vẫn phủ đúng dải cần cho RQ1 (16 → 8 → 4 bit).

**FP8 chuyển sang tuỳ chọn P4**, chỉ chạy nếu mượn được máy SM ≥ 8.9 (Modal L4).
Nếu chạy, phải ghi rõ máy nào chạy bậc nào trong phần Thực nghiệm.

**Hệ quả cho Kaggle T4 (SM 7.5).** T4 **không có BF16 native**. Nếu buộc phải dùng
T4, mốc tham chiếu là **FP16**, không phải BF16 — và phải ghi đúng tên trong báo
cáo, không được viết BF16 cho gọn.

**Điểm cộng ngoài dự tính.** Việc này tự nó là một **khuyến nghị triển khai** cho
trục C: *"cơ quan mua máy có GPU Ampere trở xuống thì đừng chọn checkpoint FP8 —
sẽ không được tăng tốc như quảng cáo, và chất lượng là của một sơ đồ khác."*
Rất ít nhóm biết chi tiết này. Đưa vào Chương 5.

**Cơ chế chặn.** `scripts/00e_doctor.py` đọc compute capability và in ra mức nén
nào chạy được; `scripts/04_export_quant.py` tự loại bậc không hợp lệ trước khi
tốn giờ tải mô hình.


---

## ADR-012 · 05/08 · Sàng trần tiếng Việt trước khi chốt model P0

**Bối cảnh.** Chọn hai model P0 khác họ kiến trúc (Qwen + một họ Llama-like) là
đúng hướng: cùng họ thì kết luận RQ1 chỉ đúng cho họ đó, và phản biện sẽ hỏi
*"suy giảm này là của tiếng Việt hay của riêng Qwen?"*.

Nhưng đa dạng kiến trúc **không được đánh đổi bằng trần tiếng Việt**.

**Vấn đề: hiệu ứng sàn.** Đề tài đo hiệu số giữa trần BF16 và các bậc nén. Nếu
một model vốn gần như không biết tiếng Việt, trần của nó nằm sát mức đoán mò
(25% với trắc nghiệm 4 lựa chọn). Khi đó "int4 tụt từ 27% xuống 25%" là nhiễu,
không phải phát hiện.

Nguy hiểm ở chỗ **nó không lộ ra trong bảng**: vẫn có số, vẫn vẽ được đồ thị,
vẫn trông như kết quả. Chỉ hội đồng biết đọc mới thấy.

**Rủi ro cụ thể với SmolLM2-1.7B-Instruct:** dòng SmolLM2 huấn luyện chủ yếu trên
corpus tiếng Anh (FineWeb-Edu, DCLM, Cosmopedia). Khả năng tiếng Việt là phụ phẩm,
không phải mục tiêu thiết kế.

**Quyết định.** Không chốt model P0 bằng suy đoán. Chạy `make screen` đo hai thứ
ở BF16 trước khi cam kết cả ma trận:
1. Accuracy trên 200 câu VMLU → trần định lượng
2. Sinh tự do tiếng Việt → tỉ lệ dấu, mojibake, chuyển ngữ → trần định tính

**Ngưỡng chốt.**

| Tiêu chí | Ngưỡng | Vì sao |
|---|---|---|
| headroom = acc − 25% | ≥ 10 điểm % | dưới mức này không còn chỗ cho suy giảm biểu hiện |
| tỉ lệ dấu | ≥ 0.15 | dưới mức này model gần như không sinh tiếng Việt có dấu |
| mojibake ở BF16 | = 0 | trần đã bẩn thì không quy lỗi cho nén được |

**Ràng buộc kèm theo.** Cả hai model phải là bản **Instruct**. Trộn base với
instruct là biến nhiễu: instruct trả lời trắc nghiệm tốt hơn và sinh văn bản có
cấu trúc — ảnh hưởng thẳng vào RQ2 (base model sinh văn lan man, không phải câu
trả lời, làm hỏng phân bố lỗi).

**Lợi ích phụ.** Bảng sàng model đưa vào **phụ lục quyển**: nó chứng minh việc
chọn model có căn cứ đo đạc chứ không phải chọn bừa — đúng thứ hội đồng hỏi ở
câu phản biện số 6 ("vì sao chỉ 2 mô hình, và vì sao là hai mô hình này").


---

## ADR-013 · 05/08 · Kiểm định BẮT CẶP (McNemar) làm chỉ số chính của Bảng 3

**Hai phát hiện về nguồn dữ liệu, phát hiện cùng lúc.**

**(a) Repo dataset ghi trong docs không tồn tại.** `anhdungitvn/vmlu_v1.5` trả lỗi
truy cập trên HF Hub (kiểm 08/2026). Thay bằng mirror `danganhdat/vmlu-v1-5`,
schema khớp: `question`, `choices`, `answer`/`answer_key`, và cột môn học là
`category` (không phải `subject` như giả định ban đầu).

**(b) Nghiêm trọng hơn: đáp án split TEST của VMLU không công khai.** Test set
dành cho leaderboard. Các công trình trước cũng đánh giá trên validation vì lý do
này — VinaLLaMA ghi rõ họ dùng validation set "since the answers to the test set
are not publicly available".

Nghĩa là **cỡ mẫu chấm được ~1.000 câu, không phải 10.880** như README từng ghi.

**Vấn đề nảy sinh.** Kế hoạch cũ báo cáo sai số lấy mẫu độc lập: n=2.000 cho
±1,98%. Với n≈744 (validation), MoE độc lập là **±3,6%**. Suy giảm dưới 3,6 điểm
sẽ bị tuyên bố "không phân biệt được với nhiễu" — và đó đúng là vùng thú vị nhất
(bậc INT8, nơi suy giảm thường nhỏ). Đề tài mất khả năng kết luận ở chỗ quan
trọng nhất.

**Quyết định: MoE độc lập là CHỈ SỐ SAI cho thiết kế này.**

Ta chấm **cùng một bộ câu hỏi** qua mọi bậc nén — đây là thiết kế **bắt cặp**.
Với dữ liệu bắt cặp, phương sai giữa các câu hỏi bị triệt tiêu; chỉ những câu
ĐỔI kết quả mới mang thông tin. Kiểm định McNemar khai thác đúng điều đó.

Chỉ số chính của Bảng 3 từ nay:
- **McNemar** (nhị thức chính xác khi số câu bất đồng < 25, chi-square Yates khi ≥ 25)
- **Bootstrap bắt cặp** cho CI 95% của Δ
- **MoE độc lập** vẫn báo cáo, nhưng ở **phụ lục**, để đối chiếu

**Bằng chứng số (đã kiểm bằng test).** n=744, mô phỏng suy giảm thật:

| | Δ | Kết luận |
|---|---|---|
| MoE độc lập | ±3,59% | −2,55% → "không kết luận được" |
| McNemar bắt cặp | ↓36 ↑8 | p = 0,0024 → **CÓ ý nghĩa** |

Cùng một dữ liệu, hai kết luận trái ngược. `tests/test_significance.py::test_paired_beats_independent_moe`
khoá lại hành vi này ở hai mức suy giảm khác nhau.

**Hệ quả vận hành.**
- `lm_eval` **phải** chạy với `--log_samples` — không có đúng/sai từng câu thì
  không tính McNemar được. Đừng bỏ cờ đó để tiết kiệm dung lượng.
- Bộ câu hỏi phải **giống hệt và cùng thứ tự** qua mọi bậc nén, nếu không phép
  bắt cặp vô nghĩa mà vẫn ra số.
- `scripts/01` đếm và báo cáo split nào có đáp án, thay vì để phát hiện muộn lúc
  accuracy ra 0%.

**Điểm cộng khi phản biện.** Câu hỏi số 1 trong `REPORT_OUTLINE.md` là "vì sao lấy
mẫu mà không chạy hết". Câu trả lời giờ mạnh hơn nhiều: *không phải chúng tôi
chọn không chạy hết — phần lớn VMLU không có đáp án công khai; và chính vì cỡ mẫu
nhỏ nên chúng tôi dùng thiết kế bắt cặp, mạnh hơn hẳn so sánh độc lập.*


---

## ADR-014 · 05/08 · Chọn nguồn VMLU bằng KIỂM CHÉO, không bằng số dòng

**Bối cảnh.** Trên HF có nhiều mirror VMLU. `tridm/VMLU` công bố đủ **10.880 dòng**,
trong khi trang chủ vmlu.ai chỉ cho tải phần Vi-MQA với cỡ mẫu nhỏ hơn nhiều.
Cám dỗ rõ ràng: lấy mirror 10.880 dòng cho cỡ mẫu đẹp.

**Vì sao KHÔNG chọn theo số dòng.** VMLU chính thức **giữ kín đáp án split test**
(dành cho leaderboard). Một mirror công bố đủ 10.880 dòng CÓ đáp án chỉ có thể là:

| Khả năng | Hệ quả |
|---|---|
| (a) chép từ bản gốc lúc còn công khai | dùng được |
| (b) có cột đáp án nhưng rỗng ở phần test | cỡ mẫu thật vẫn nhỏ |
| (c) đáp án phần test do bên thứ ba tự suy/tự sinh | **KHÔNG dùng được** |

Nếu là (c) mà ta dùng, mọi accuracy trong Bảng 3 dựa trên đáp án sai, và **không
so được với bất kỳ công trình nào** dùng VMLU chính thức. Câu phản biện *"số của
em so được với leaderboard VMLU không?"* sẽ không trả lời được.

Nguy hiểm ở chỗ: **cả ba khả năng đều cho ra một bảng số trông giống nhau.**

**Quyết định: phân biệt bằng kiểm chéo, không bằng suy đoán.**

`scripts/01b_verify_vmlu_source.py` lấy các câu xuất hiện ở **cả hai nguồn** trong
phần có đáp án chính thức, đối chiếu đáp án (khoá là băm câu hỏi đã chuẩn hoá NFC
+ khoảng trắng + hoa/thường, nên chịu được khác biệt định dạng):

| Tỉ lệ khớp | Kết luận |
|---|---|
| ≥ 99% | mirror chép từ bản gốc — **dùng được** |
| 95–99% | lệch nhẹ — kiểm tay vài ca trước khi dùng |
| < 95% | ít nhất một nguồn có đáp án tự sinh — **LOẠI** |

Kèm theo: kiểm **phân bố đáp án A/B/C/D**. Bộ đề thật khá đều; lệch nặng
(vd. 90% đáp án A) là dấu hiệu đáp án được suy đoán hoặc sinh máy.

**Về bốn bộ trên vmlu.ai.** Bản VMLU Benchmarks (ACL 2025) gồm bốn bộ đo bốn năng
lực khác nhau: **Vi-MQA** (kiến thức tổng quát, trắc nghiệm), Vi-SQuAD (đọc hiểu),
Vi-Drop (suy luận), Vi-Dialog (hội thoại).

Đề tài này chỉ dùng **Vi-MQA**, vì:
- Chấm bằng loglikelihood → tái lập được, không cần LLM-as-judge (thêm biến nhiễu
  vào đúng thứ đang đo)
- Là bộ mà cộng đồng VN nhận diện là "VMLU"
- Ba bộ còn lại cần chấm sinh tự do; **trục RQ2 của đề tài đã có bộ probe riêng**,
  thiết kế đúng cho taxonomy lỗi, tốt hơn là mượn bộ khác.

Ghi rõ trong quyển: dùng Vi-MQA, không dùng ba bộ kia, và nêu lý do trên. Nói
trước thì đó là quyết định phạm vi; để hội đồng hỏi thì thành thiếu sót.

**Nguyên tắc chốt cuối.** Ưu tiên **độ tin cậy của đáp án** hơn cỡ mẫu. Cỡ mẫu nhỏ
đã được bù bằng thiết kế bắt cặp (ADR-013); đáp án sai thì không có cách nào bù.


---

## ADR-015 · 05/08 · Chốt nguồn VMLU: file chính thức từ vmlu.ai, n = 1.047

**Kết quả kiểm chéo (đã chạy thật).** Ba nguồn, cùng một kết luận:

| Nguồn | test | dev/train | valid |
|---|---|---|---|
| vmlu.ai (tải tay) | 9.833 câu, **0 đáp án** | 303 ✅ | 744 ✅ |
| `tridm/VMLU` | 9.833 câu, **0 đáp án** | 303 ✅ | 744 ✅ |
| `danganhdat/vmlu-v1-5` | 9.833 câu, **0 đáp án** | 303 ✅ | 744 ✅ |

Con số "10.880 dòng" của mirror là **tổng số dòng**, không phải số câu chấm được.
Không mirror nào có đáp án test — nghi ngờ ở ADR-014 được giải quyết theo hướng
tốt: không nguồn nào tự sinh đáp án.

**Quyết định.** Nguồn chính = **file tải tay từ vmlu.ai** đặt tại
`data/raw/vmlu/`. Mirror HF chỉ là dự phòng. Lý do: bản gốc của nhóm tác giả,
không qua trung gian.

**Cỡ mẫu chốt: n = 1.047** (dev 303 + valid 744), phủ **đủ 58 môn**, 10–20 câu
mỗi môn, dev ∩ valid = ∅. Vì 1.047 < 2.000 nên **dùng hết, không lấy mẫu** —
`stratified_sample` tự nhận ra và bỏ qua.

**Hai lỗi trong code bị lộ ra nhờ dữ liệu thật:**

**(1) Không có cột môn học.** Cấu hình cũ ghi `stratify_by: category`. Bản chính
thức chỉ có 4 cột: `id`, `question`, `choices`, `answer`. Môn nằm ở **tiền tố của
`id`** (`"28-0001"` → môn 28). `detect_subject_key` nay trả `"id"` và
`subject_of()` tách tiền tố.

**(2) Mức đoán mò KHÔNG phải 0,25.** Số lựa chọn thay đổi theo câu:

| Số lựa chọn | Số câu |
|---|---|
| 3 | 42 |
| 4 | 1.003 |
| 5 | 2 |

Mức đoán mò thực tế = **0,2532**. Chênh với 0,25 chỉ 0,3 điểm — nhỏ, nhưng sai
theo hướng **nguy hiểm**: dùng 0,25 sẽ ĐÁNH GIÁ THẤP mức đoán mò, làm headroom
trông lớn hơn thực tế, và có thể kết luận một model "có năng lực tiếng Việt"
trong khi nó đang đoán. Sai lầm này đi thẳng vào ngưỡng sàng model (ADR-012) và
vào kết luận RQ1.

`random_baseline()` nay tính từ dữ liệu; `configs/experiments.yaml` ghi
`random_baseline: 0.2532` để đối chiếu.

**Xác nhận chất lượng nguồn.** Phân bố đáp án A 256 / B 264 / C 278 / D 248 / E 1
— cân đối, đúng dạng đề thi thật, không có dấu hiệu đáp án sinh máy.

**Đưa vào quyển.** Bảng ba nguồn ở trên vào **phụ lục**. Nó trả lời trước câu
phản biện số 1 (*"vì sao không chạy hết 10.880 câu?"*) bằng bằng chứng: không
phải nhóm chọn không chạy — đáp án phần còn lại không tồn tại công khai.


---

## ADR-016 · 05/08 · Dùng 9.833 câu KHÔNG đáp án để đo flip rate

**Bối cảnh.** ADR-015 chốt n = 1.047 câu có đáp án. Câu hỏi tự nhiên: 9.833 câu
còn lại có bỏ đi không?

**Không.** Đề tài KHÔNG hỏi *"model trả lời đúng không"* — đề tài hỏi *"nén làm
model thay đổi thế nào"*. Câu hỏi thứ hai trả lời được mà không cần đáp án:

> Cùng một câu, BF16 chọn A. Nén xuống INT4, model chọn C. Đó là một lần **đổi
> dự đoán**. Đếm tỉ lệ đổi trên 9.833 câu → **flip rate**.

**Ba thứ flip rate cho mà accuracy trên 1.047 câu không cho:**

| | 1.047 câu (accuracy) | 9.833 câu (flip rate) |
|---|---|---|
| Sai số 95% | ±3,03% | **±0,99%** |
| Câu/môn | 10–20 → không tách được | ~170 → **tách theo môn được** |
| Bị chặn bởi trần năng lực | có | **không** |

Việc tách theo môn mở ra một kết quả phụ cho RQ2: *nén làm hỏng môn nào nhiều
nhất?* Với 1.047 câu thì mỗi ô quá nhỏ để nói gì.

**Cạm bẫy — và một lỗi tôi đã mắc rồi sửa.**

Flip rate không phải accuracy: đổi dự đoán có thể là đổi từ SAI sang ĐÚNG. Nên
phải kiểm chứng proxy trên phần có đáp án trước khi suy rộng.

Bản đầu của `validate_proxy` đặt ngưỡng *"tỉ lệ đúng→sai > 0,65 thì flip rate là
proxy tốt"*. **Ngưỡng đó luôn bị vượt với mọi dữ liệu**, vì:

- đổi một câu ĐANG ĐÚNG thì chắc chắn thành sai (xác suất 1)
- đổi một câu ĐANG SAI thì chỉ thành đúng với xác suất 1/(k−1)

Nên ngay khi việc đổi hoàn toàn vô hướng, tỉ lệ "đúng→sai" đã tự nhiên rất cao:

| Accuracy gốc | Kỳ vọng harmful nếu đổi NGẪU NHIÊN (k=4) |
|---|---|
| 30% | 56,2% |
| 50% | 75,0% |
| 65% | **84,8%** |
| 80% | 92,3% |

Một phép kiểm không bao giờ trượt thì không kiểm gì cả — nó chỉ tạo cảm giác
đã kiểm chứng.

**Sửa.** So với **kỳ vọng ngẫu nhiên tính từ accuracy gốc và số lựa chọn**, không
so với hằng số. Kiểm định nhị thức một phía trả lời: *nén có phá hỏng câu đúng
NHIỀU HƠN mức một nhiễu cùng cường độ sẽ gây ra không?*

Độ nhạy đã đo (n=1.047, 4 lựa chọn):

| Mức thiên lệch | Số lần đổi | p | Phát hiện? |
|---|---|---|---|
| 1,0 (nhiễu thuần) | 60 | 0,202 | không (đúng) |
| 1,5 | 109 | 0,0023 | ✅ |
| 2,5 | 170 | 0,0017 | ✅ |

**Cách báo cáo trong quyển.** Ba chỉ số, nêu rõ vai trò từng cái:
1. **Accuracy + McNemar** trên 1.047 câu — chỉ số chính, có ground truth
2. **Flip rate** trên 9.833 câu — độ trung thành với mô hình gốc, cỡ mẫu lớn
3. **Kiểm chứng proxy** — bằng chứng rằng (2) nói lên điều gì

Nếu kiểm chứng thất bại, báo cáo trung thực: flip rate chỉ đo **độ lung lay**,
không suy ra suy giảm chất lượng. Đó vẫn là một kết quả — và nói ra trước thì
mạnh hơn để hội đồng phát hiện.


---

## ADR-017 · 05/08 · Kết quả sàng model: loại SmolLM2, giữ Qwen2.5-1.5B

**Số đo thật** (200 câu VMLU, BF16, RTX 3050, mức đoán mò thực tế 0,2524):

| Model | Accuracy | Headroom | Tỉ lệ dấu | Mojibake | VRAM | Kết luận |
|---|---|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct | **52,0%** | **+26,8%** | 0,287 | 0 | 2,88 GB | ✅ ĐẠT |
| SmolLM2-1.7B-Instruct | 29,0% | +3,8% | 0,301 | 0 | 3,20 GB | ❌ LOẠI |

**Quyết định.** Qwen2.5-1.5B-Instruct là model P0 thứ nhất. SmolLM2 bị loại vì
hiệu ứng sàn: trần 29,0% chỉ hơn đoán mò 3,8 điểm, không còn chỗ cho suy giảm
biểu hiện. Nếu vẫn dùng, mọi Δ đo được ở INT8/INT4 đều là nhiễu quanh mức đoán mò.

**Phát hiện phụ, quan trọng hơn cả kết quả loại/giữ.**

SmolLM2 có **tỉ lệ dấu 0,301 — hoàn toàn bình thường**, cao hơn cả Qwen (0,287).
Không mojibake. Theo mọi chỉ số tự động về *hình thức* tiếng Việt, nó đạt.

Nhưng nội dung sinh ra vô nghĩa:

> *"Trong thủ tục đăng ký xe ô tô làm việc, bạn cần có thể thử nghiệm với một số
> bước như sau: 1. Bạn cần tại một trang web chuyên về đăng ký xe ô tô..."*

Đúng chính tả, đúng dấu, sai hoàn toàn về nội dung và ngữ pháp chức năng.

**Đây là bằng chứng THỰC NGHIỆM cho quyết định ở ADR-004 và ERROR_TAXONOMY:**
detector tự động **không thay thế được người gán nhãn**. Tỉ lệ dấu, mojibake,
chuyển ngữ đều bắt được lỗi *hình thức*; không chỉ số tự động nào trong bộ E1–E6
bắt được ca "tiếng Việt trôi chảy nhưng rỗng nghĩa".

Đưa ví dụ này vào quyển, mục 3.7 (quy trình gán nhãn) và mục 4.5 (thảo luận). Nó
biến một lựa chọn phương pháp trông như thận trọng quá mức thành một quyết định
có căn cứ đo đạc.

**Phương án A (ưu tiên): tìm model thứ hai KHÁC HỌ.**
Ứng viên xếp theo khả năng đạt: `vilm/vinallama-2.7b-chat` (Llama-2 arch + tiền
huấn luyện tiếng Việt — khác họ Qwen VÀ có tiếng Việt), `google/gemma-3-1b-it`,
`meta-llama/Llama-3.2-1B-Instruct` (gated).

**Phương án B (nếu không ứng viên nào đạt): đổi TRỤC so sánh.**
Thay "hai họ kiến trúc" bằng **thang kích thước cùng họ**: Qwen2.5-0.5B / 1.5B / 3B.

Câu hỏi đổi từ *"suy giảm có phụ thuộc kiến trúc không?"* thành *"model càng nhỏ
có càng dễ hỏng khi nén không?"* — và câu thứ hai **sát với đề tài hơn**: trục ứng
dụng là chọn model nhỏ nhất còn dùng được cho máy cấp xã, nên biết ngưỡng kích
thước nào chịu được nén là khuyến nghị trực tiếp cho Chương 5.

Đánh đổi: mất khả năng khái quát qua kiến trúc. Phải ghi thẳng vào mục Hạn chế:
*"kết luận về đường cong suy giảm được thiết lập trên họ Qwen2.5; kiểm chứng trên
họ khác là hướng phát triển tiếp theo."* Nói trước thì là phạm vi; để hội đồng
hỏi thì thành thiếu sót.


---

## ADR-018 · 05/08 · Chốt hai model P0 và thêm cửa kiểm SÀN cho từng bậc nén

**Kết quả sàng cuối** (200 câu VMLU, BF16, mức đoán mò 0,2524):

| Model | Họ | Accuracy | Headroom | Dấu | VRAM | Kết luận |
|---|---|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct | Qwen | 52,0% | +26,8 | 0,287 | 2,88 GB | ✅ P0 |
| **google/gemma-3-1b-it** | **Gemma** | 39,5% | +14,3 | 0,283 | 1,87 GB | ✅ P0 |
| SmolLM2-1.7B-Instruct | Llama-like | 29,0% | +3,8 | 0,301 | 3,20 GB | ❌ loại |

Hai model P0 **khác họ kiến trúc** → luận điểm tổng quát của RQ1 giữ được, không
phải lùi về phương án B (thang kích thước cùng họ).

**Hạn chế phải ghi vào quyển.** Gemma-3-1B nhỏ hơn Qwen2.5-1.5B (1B vs 1,5B), nên
khác biệt giữa hai model lẫn **cả kiến trúc lẫn kích thước**. Không được quy toàn
bộ chênh lệch cho kiến trúc. Nói trước thì là phạm vi; để hội đồng chỉ ra thì
thành lỗi thiết kế.

**Rủi ro mới: Gemma có headroom hẹp.** +14,3 điểm so với +26,8 của Qwen. Nếu INT4
làm tụt 10 điểm, Gemma còn ~29,5% — sát mức đoán mò.

Khi một biến thể chạm sàn, mọi so sánh sau đó **vô nghĩa**: "INT4 tệ hơn INT8 5
điểm" không nói lên gì nếu cả hai đều không khác đoán mò. Nhưng bảng số vẫn có số,
đồ thị vẫn vẽ được — lại một ca suy giảm âm thầm.

**Quyết định.** Thêm `significance.at_floor()`: kiểm định z một phía xem accuracy
có LỚN HƠN mức đoán mò không. `scripts/05` chạy tự động cho mọi biến thể và in
cảnh báo. Biến thể chạm sàn được ghi nhận là **"mất năng lực"**, KHÔNG diễn giải
mức tụt tiếp theo và KHÔNG vẽ đường cong xuống dưới điểm đó.

Ngưỡng đã kiểm (baseline 0,2524):

| n | acc 29,5% | Kết luận |
|---|---|---|
| 200 | p = 0,083 | chạm sàn |
| 1.047 | p = 0,0008 | còn phân biệt được |

Cỡ mẫu đầy đủ 1.047 câu đẩy được ngưỡng phát hiện xuống thấp hơn — thêm một lý do
chạy eval trên toàn bộ 1.047 câu chứ không chỉ 200 câu như lúc sàng.


---

## ADR-019 · 06/08 · Đính chính cảnh báo sàn của Gemma; giữ nguyên hai model P0

**Đính chính một cảnh báo SAI của chính ADR-018.** ADR-018 lo Gemma-3-1B có
headroom hẹp (+14,3 điểm) và INT4 có thể làm nó chạm sàn. Con số đó tính trên
**cỡ mẫu sàng n=200**, không phải cỡ mẫu eval chính thức n=1.047.

Ngưỡng sàn phụ thuộc mạnh vào n:

| Cỡ mẫu | Accuracy dưới mức này = không phân biệt được với đoán mò |
|---|---|
| n = 200 (lúc sàng) | 30,3% |
| **n = 1.047 (eval thật)** | **27,4%** |

Biên tụt thực tế trên eval chính thức:

| Model | BF16 | Biên tụt trước khi chạm sàn |
|---|---|---|
| Qwen2.5-1.5B-it | 52,0% | **24,6 điểm** |
| gemma-3-1b-it | 39,5% | **12,1 điểm** |

Nén 4-bit thường làm tụt 3–8 điểm ở cỡ model này, nên 12,1 điểm là **đủ an toàn**.
Không cần đổi model.

**Bài học phương pháp.** Ngưỡng thống kê tính trên cỡ mẫu thăm dò không được đem
áp cho cỡ mẫu chính thức. Suýt nữa loại oan một model đạt. `scripts/00g` nay in
thêm cột BIÊN TỤT tính theo n của eval chính thức, để không lặp lại nhầm lẫn này.

**Về câu hỏi "chạy tuần tự để nâng Gemma lên cỡ lớn hơn".**

Script sàng và script export **vốn đã chạy tuần tự** — nạp một model, đo, giải
phóng VRAM, nạp model kế. Không có lúc nào hai model cùng nằm trên GPU. Nên chạy
tuần tự không mở thêm được dung lượng: trần vẫn là **một model phải vừa 6 GB**.

Gemma-3-4B ở BF16 cần ~8 GB — không vừa kể cả khi chạy một mình. Mốc tham chiếu
BF16 là bắt buộc cho toàn đề tài (không có nó thì mọi Δ vô nghĩa), nên model P0
buộc phải ≤ 2B trên phần cứng này.

**Nếu muốn mạnh hơn, hướng đúng không phải nâng Gemma mà là TÁCH BIẾN.**

Hạn chế hiện tại: Qwen 1,5B vs Gemma 1B khác **cả kiến trúc lẫn kích thước**, nên
không quy được chênh lệch cho yếu tố nào. Thêm **Qwen2.5-0.5B-Instruct** làm model
thứ ba (ưu tiên P1) sẽ tách được:

- Qwen-1,5B ↔ Gemma-1B → khác kiến trúc (lẫn kích thước)
- Qwen-1,5B ↔ Qwen-0,5B → **chỉ khác kích thước**, cùng kiến trúc và cùng dữ liệu

Có cặp thứ hai thì mới nói được *"suy giảm phụ thuộc kích thước hay kiến trúc"* —
và câu đó trực tiếp phục vụ khuyến nghị Chương 5 (chọn model nhỏ nhất còn dùng được).

Chi phí thấp: 0,5B chỉ ~1,2 GB VRAM, export và eval nhanh. Nhưng **phải sàng
trước** — model 0,5B có rủi ro trần tiếng Việt thấp, và nếu nó không đạt thì bỏ,
không cố.


---

## ADR-020 · 10/08 · Đưa Modal vào pipeline và quy tắc nhất quán phần cứng

**Bối cảnh.** Máy local RTX 3050 6GB chạy được P0 nhưng chiếm máy nhiều giờ, và
SM 8.6 không chạy được FP8 (ADR-011).

**Quyết định 1: tích hợp Modal, nhưng KHÔNG viết lại logic.**

`modal_app.py` chỉ dựng môi trường rồi gọi đúng những script trong `scripts/` mà
ta vẫn chạy ở local. Không có bản logic riêng cho Modal.

Lý do: nếu có hai bản, chúng sẽ phân kỳ, và có ngày Bảng 3 chạy trên Modal khác
Bảng 3 chạy ở nhà — mà không ai biết bản nào đúng. Với đề tài mà sản phẩm chính
là số liệu, đó là rủi ro không chấp nhận được.

**Quyết định 2: L4 khôi phục bậc FP8.**

L4 là compute capability **8.9**, đúng ngưỡng FP8 W8A8 native. Thang nén từ 4 bậc
thành 5:

```
bf16 → fp8 → int8 → int4 → gguf(CPU)
        ↑ bậc này không chạy được trên RTX 3050
```

Thêm một điểm đo giữa 16-bit và 8-bit là thêm độ phân giải ở đúng vùng suy giảm
bắt đầu xuất hiện.

**Quyết định 3 — QUAN TRỌNG NHẤT: quy tắc nhất quán phần cứng.**

Toàn bộ ma trận accuracy chạy trên **MỘT máy**. Nếu BF16 chạy local còn INT4 chạy
Modal, mọi Δ trong Bảng 3 lẫn cả hiệu ứng phần cứng và **không tách ra được** —
lại đúng kiểu nhiễu âm thầm mà đề tài này nghiên cứu.

Phân vai máy, chốt trước:

| Bảng | Máy | Bắt buộc? |
|---|---|---|
| Bảng 3 (RQ1 accuracy) | Modal L4 | nhất quán, chạy hết trên L4 |
| Bảng 4,5 (RQ2 taxonomy) | Modal L4 sinh, người gán nhãn ở nhà | |
| Bảng 6 (RQ3 truy hồi) | Local CPU | corpus ở máy, không cần GPU |
| **Bảng 7 (RQ4 độ trễ)** | **CPU laptop** | **BẮT BUỘC** — đây LÀ luận điểm ứng dụng |

Bảng 7 đo trên L4 rồi báo cáo "chạy được ở xã" là mất căn cứ toàn bộ trục ứng dụng.
Phần Thực nghiệm của quyển phải ghi cấu hình phần cứng của **từng bảng**.

**Rủi ro chi phí.** Credit miễn phí dễ hết giữa chừng job dài. Ba lớp bảo vệ:
`DRY=1` bắt buộc trước mỗi lần chạy thật; Volume giữ phần đã xong (chạy lại bỏ
qua biến thể đã có); chạy từng bước thay vì dồn một job 6 giờ.

Nếu hết credit: bf16/int8/int4/gguf vẫn chạy được ở local, chỉ mất bậc FP8.
**Đề tài không chết vì thiếu FP8** — nó là bậc bổ sung, không phải bậc nền.

Tuyệt đối không tạo nhiều tài khoản để lách hạn mức: vi phạm điều khoản và rủi ro
mất luôn công cụ đang phụ thuộc.


---

## ADR-020 · 10/08 · Tích hợp Modal; khôi phục FP8; ghi dấu vết máy

**Bối cảnh.** Máy local (RTX 3050, SM 8.6) chạy được thang 4 bậc nhưng KHÔNG chạy
được FP8 (cần SM 8.9 — ADR-011). Job export/eval cũng chiếm GPU máy làm việc
hàng giờ.

**Quyết định 1: đưa Modal vào như một BỘ THỰC THI, không phải một nhánh code.**
`modal_app.py` chỉ đóng gói môi trường rồi gọi ĐÚNG các script trong `scripts/`.
Không có logic riêng cho Modal. Lý do: hai bản logic sẽ phân kỳ, và sẽ có ngày
Bảng 3 chạy trên Modal khác Bảng 3 chạy ở nhà mà không ai biết bản nào đúng.

**Quyết định 2: khôi phục FP8 khi chạy trên Modal.** L4 là SM 8.9 nên FP8 W8A8
chạy native. Thang nén thành 5 bậc: bf16 → fp8 → int8 → int4 → gguf. FP8 là điểm
giữa thú vị nhất giữa 8-bit và 4-bit; có nó thì đường cong RQ1 mịn hơn hẳn.

Ghi đè qua biến môi trường `VIEDGE_PRECISIONS`, không sửa config — để cấu hình
mặc định vẫn là thang an toàn cho máy local.

**Quyết định 3: ghi dấu vết máy vào MỌI thư mục kết quả.**

Đây là phần quan trọng nhất của ADR này. Khi FP8 chạy trên Modal còn INT4 chạy ở
nhà, hai bậc trong **cùng một đường cong** được đo trên hai máy khác nhau:

- kernel khác theo kiến trúc (Marlin trên Ampere vs cutlass trên Ada)
- thứ tự cộng dồn float khác → chênh nhỏ ở loglikelihood
- phiên bản thư viện trên image Modal khác máy local

Chênh lệch nhỏ. Nhưng **suy giảm ta đang đo cũng nhỏ**: nếu Δ(INT8) là 2 điểm mà
sai khác do máy là 0,5 điểm thì một phần tư "phát hiện" là nhiễu phần cứng.

`viedge/provenance.py` ghi `hardware.json` (GPU, SM, VRAM, phiên bản torch/
transformers/llmcompressor, runner local hay modal) vào từng thư mục biến thể.
`scripts/05` đối chiếu và **in cảnh báo nếu một model có các bậc chạy khác máy**.

**Quy tắc vận hành.** Chạy toàn thang của một model trên MỘT máy. Hai cách đúng:

| Cách | Khi nào |
|---|---|
| Toàn bộ trên Modal (5 bậc, có FP8) | có credit — sạch nhất |
| Toàn bộ ở local (4 bậc, không FP8) + ghi rõ trong quyển | hết credit |

Cách sai: bf16/int8/int4 ở local, fp8 trên Modal, xếp chung một bảng không ghi chú.

**Ranh giới không đổi.** Bảng 7 (RQ4 — độ trễ trên máy cấp xã) và demo rút cáp
mạng BẮT BUỘC ở máy local. Đo trên L4 rồi báo cáo "chạy được ở xã" thì luận điểm
ứng dụng mất căn cứ — và đó là 10 điểm mục "khả năng ứng dụng" của rubric.

**Nhắc lại cảnh báo cũ.** Không tạo nhiều tài khoản để lách hạn mức credit: vi
phạm điều khoản dịch vụ, rủi ro mất công cụ giữa lúc gấp. Hết credit thì lùi về
local 4 bậc — mất FP8 chứ không mất đề tài.


---

## ADR-021 · 11/08 · Bảng 3 lần đầu; và phát hiện calibration CHƯA từng được dùng

**Kết quả chạy thật** (Modal L4, VMLU 1.047 câu, mức đoán mò 0,2532):

| Model | bf16 | fp8 | int8 | int4 |
|---|---|---|---|---|
| Qwen2.5-1.5B-it | 49,47% | **51,29%** (+1,82) | 48,90% (−0,57) | 46,13% (−3,34) |
| gemma-3-1b-it | 40,11% | 40,02% (−0,09) | 37,92% (−2,19) | **31,71% (−8,40)** |

Hai quan sát đáng theo đuổi:

1. **Model nhỏ hơn tụt sâu hơn ở 4-bit.** Gemma-1B mất 8,40 điểm còn Qwen-1,5B chỉ
   mất 3,34. Nếu kiểm định bắt cặp xác nhận, đây là kết quả trực tiếp phục vụ
   khuyến nghị Chương 5: model càng nhỏ càng phải thận trọng khi nén sâu.
2. **FP8 của Qwen CAO HƠN bf16 1,82 điểm.** Chưa kết luận được — sai số chuẩn của
   mỗi số là ±1,55 điểm. Phải chờ McNemar bắt cặp; rất có thể là nhiễu.

**Lỗi 1 — model_tag bị hỏng, và nó âm thầm TẮT chỉ số chính.**

lm-eval tạo thêm một cấp thư mục đặt tên theo đường dẫn model đã làm sạch:

```
results/eval/gemma3-1b-it@bf16/__root__viedge__models__gemma3-1b-it@bf16/results_*.json
             ^^^^^^^^^^^^^^^^ tag thật     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ lm-eval đặt
```

`collect_results` lấy `f.parent.name` nên ra tag sai. Hệ quả dây chuyền:
`load_per_sample` tra theo tag sai → không thấy file nào → **McNemar bị bỏ qua**
với đúng một dòng log nhỏ. Bảng vẫn in ra đầy đủ, chỉ thiếu chỉ số quyết định.

Đã sửa: lấy cấp thư mục ngay dưới `out_dir`.

**Lỗi 2 — nghiêm trọng hơn: bộ calib tiếng Việt CHƯA từng được dùng.**

Log llm-compressor nói thẳng ở CẢ BA bậc:

```
Inferred `DataFreePipeline` for `QuantizationModifier`
```

`QuantizationModifier` một mình là **data-free**. Dù ta truyền dataset vào
`oneshot()`, nó không chạy lượt calibration nào:

| Bậc | Cơ chế thật | Có dùng calib? |
|---|---|---|
| FP8_DYNAMIC | data-free theo thiết kế | không |
| W8A8 | RTN trọng số + activation lượng tử hoá **động** | không |
| W4A16 | RTN trọng số | **không** |

Nghĩa là ADR-007 (*"calib phải bằng tiếng Việt, dùng C4 tiếng Anh sẽ tự tạo ra
chính hiện tượng đang đo"*) **chưa hề có hiệu lực**, và cảnh báo "chỉ có 124/256
mẫu calib" là vô nghĩa. Thí nghiệm P4 (so calib EN vs VI) cũng không thể chạy như
đang cấu hình — hai nhánh sẽ cho kết quả GIỐNG HỆT nhau.

Nguy hiểm ở chỗ: mọi thứ chạy trơn tru, ra số đẹp, và nếu không đọc kỹ log thì
sẽ viết vào quyển một tuyên bố về calibration mà thí nghiệm không hề chứng minh.

**Sửa.** Thêm `--use-gptq` cho bậc W4A16. GPTQ dùng dữ liệu calib để chọn thứ tự
lượng tử hoá và bù sai số, nên calib mới thực sự tham gia. Bật bằng
`calibration.use_gptq: true` trong config.

**Quyết định về báo cáo — chọn một trong hai, không được lập lờ:**

| Phương án | Việc phải làm | Rủi ro |
|---|---|---|
| **A. Giữ data-free (RTN)** | BỎ mọi tuyên bố về calibration khỏi quyển; bỏ thí nghiệm P4; ghi rõ "lượng tử hoá RTN, không dùng dữ liệu hiệu chuẩn" | mất một điểm tính mới, nhưng trung thực và đã có số |
| **B. Chạy lại W4A16 bằng GPTQ** | `use_gptq: true`, nâng calib lên 256 mẫu, export + eval lại bậc int4 | tốn thêm ~1 giờ L4; đổi lại ADR-007 và P4 có nghĩa |

**Khuyến nghị: phương án B, nhưng CHỈ cho bậc int4.** GPTQ thường cải thiện đáng
kể chất lượng 4-bit — chính là bậc đang tụt sâu nhất (Gemma −8,40 điểm). Nếu GPTQ
kéo được mức tụt đó lên, bản thân so sánh RTN vs GPTQ đã là một kết quả có giá trị
cho khuyến nghị triển khai, ngoài việc làm ADR-007 có hiệu lực.
