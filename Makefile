.PHONY: help setup test smoke corpus sample export eval probe agreement index rag bench tables demo clean
PY := PYTHONPATH=src python3

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22

setup:            ## Cài dependency lõi
	pip install -r requirements.txt

test:             ## Chạy pytest
	PYTHONPATH=src pytest -q tests/

smoke:            ## Chạy toàn pipeline trên dữ liệu fixture (không cần GPU/model)
	$(PY) scripts/99_smoke_all.py

corpus:           ## Bóc văn bản pháp luật -> điều/khoản/điểm
	$(PY) scripts/03_build_corpus.py

sample:           ## Lấy mẫu phân tầng VMLU
	$(PY) scripts/02_sample_vmlu.py

export:           ## Xuất mô hình theo các mức nén (DRY=1 để chỉ in lệnh)
	$(PY) scripts/04_export_quant.py

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
