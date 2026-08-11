.PHONY: help setup test smoke check modal-secret modal-doctor modal-export modal-eval modal-probe modal-pull hf-login doctor models screen vmlu-verify triage pdf doc paste corpus verify amend calib sample inspect export eval probe agreement index rag bench tables demo clean
PY := PYTHONPATH=src python3

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22

setup:            ## Cài dependency lõi
	pip install -r requirements.txt

test:             ## Chạy pytest
	PYTHONPATH=src pytest -q tests/

smoke:            ## Chạy toàn pipeline trên dữ liệu fixture (không cần GPU/model)
	$(PY) scripts/99_smoke_all.py

pdf:              ## PDF -> .txt sạch (PDF=<file> OUT=<file>)
	$(PY) scripts/00_pdf_to_text.py $(PDF) --out $(OUT) --learn-from data/raw/*.txt

doc:              ## .doc/.docx -> .txt (DOC=<file> OUT=<file>) — ƯU TIÊN hơn pdf
	$(PY) scripts/00c_doc_to_text.py $(DOC) --out $(OUT)

paste:            ## Dọn text copy từ tab Toàn văn (SRC=<file> OUT=<file>)
	$(PY) scripts/00d_clean_pasted.py $(SRC) --out $(OUT)

corpus:           ## Bóc văn bản pháp luật -> điều/khoản/điểm
	$(PY) scripts/03_build_corpus.py

verify:           ## Kiểm cấu trúc kho văn bản (thiếu/trùng/rỗng điều)
	$(PY) scripts/03c_verify_corpus.py

amend:            ## Dựng lớp phủ sửa đổi (chạy sau corpus)
	$(PY) scripts/03b_build_amendments.py

models:           ## Kiểm model trong config có tồn tại / vừa VRAM không
	$(PY) scripts/00f_check_models.py

screen:           ## Sàng model: đo TRẦN tiếng Việt ở BF16 (chạy trước export)
	$(PY) scripts/00g_screen_models.py --n 200

modal-secret:     ## [Modal] Tạo secret HF từ .env (token không qua shell history)
	$(PY) scripts/00i_modal_secret.py

modal-doctor:     ## [Modal] Kiểm môi trường GPU trên Modal (xác nhận SM 8.9 -> FP8)
	modal run modal_app.py --step doctor

modal-export:     ## [Modal] Xuất model trên L4 (DRY=1 để chỉ in lệnh)
	modal run modal_app.py --step export $(if $(DRY),--dry,) $(if $(PREC),--precisions $(PREC),)

modal-eval:       ## [Modal] Chạy lm-eval + McNemar trên L4 -> Bảng 3
	modal run modal_app.py --step evaluate

modal-probe:      ## [Modal] Sinh tự do cho taxonomy lỗi (RQ2)
	modal run modal_app.py --step probe

modal-pull:       ## [Modal] Kéo kết quả từ Volume về máy local
	modal volume get viedge-results / ./results --force

hf-login:         ## Đăng nhập HF một lần (đọc token từ .env)
	$(PY) scripts/00h_hf_login.py

check:            ## Kiểm repo đủ file/đúng phiên bản (chạy TRƯỚC job dài)
	$(PY) scripts/00j_check_repo.py

doctor:           ## Kiểm GPU + thư viện, cho biết mức nén nào chạy được
	$(PY) scripts/00e_doctor.py

triage:           ## Phân loại PDF trong data/raw/pdf (chạy ĐẦU TIÊN)
	$(PY) scripts/00b_triage_pdfs.py

vmlu-verify:      ## Kiểm chéo đáp án giữa các mirror VMLU (chạy TRƯỚC sample)
	$(PY) scripts/01b_verify_vmlu_source.py

sample:           ## Tải VMLU rồi lấy mẫu phân tầng
	$(PY) scripts/01_download_vmlu.py
	$(PY) scripts/02_sample_vmlu.py

calib:            ## Dựng bộ calibration tiếng Việt (CHẶN ĐƯỜNG export)
	$(PY) scripts/02c_build_calib.py

export:           ## Xuất mô hình theo các mức nén (DRY=1 để chỉ in lệnh)
	$(PY) scripts/04_export_quant.py

inspect:          ## Kiểm schema VMLU + render prompt thử (CHẠY TRƯỚC eval)
	$(PY) scripts/02b_inspect_vmlu.py

eval:             ## Chạy lm-eval trên VMLU đã lấy mẫu
	$(PY) scripts/05_run_eval.py

probe:            ## Sinh tự do để lấy văn bản cho taxonomy lỗi
	$(PY) scripts/06_run_error_probe.py

agreement:        ## Tính AC1/kappa giữa hai người gán nhãn
	$(PY) scripts/08_compute_agreement.py

index:            ## Dựng index truy hồi
	$(PY) scripts/09_build_index.py

rag:              ## Đánh giá RAG trên ViGovQA-GT
	$(PY) scripts/10_eval_rag.py

bench:            ## Đo TTFT/tok-s/RAM trên máy CPU mục tiêu
	$(PY) scripts/11_bench_cpu.py

tables:           ## Sinh mọi bảng cho quyển báo cáo
	$(PY) scripts/12_make_report_tables.py

demo:             ## Chạy demo offline
	$(PY) -m viedge.serve.app

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
