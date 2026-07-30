#!/usr/bin/env python3
"""
Đo TTFT / tok-s / RAM đỉnh / dung lượng đĩa trên MÁY CPU MỤC TIÊU.

Chạy script này trên đúng máy sẽ demo, KHÔNG chạy trên T4 rồi báo cáo.
Toàn bộ luận điểm "chạy được ở cấp xã" đứng trên bảng số này.
"""
import argparse, json
from pathlib import Path
from _common import ROOT, load_yaml, log, append_runlog
from viedge.bench import latency as L

PROMPTS = [
    "Không mang giấy phép lái xe bị phạt bao nhiêu tiền?",
    "Thủ tục cấp đổi giấy phép lái xe hạng B gồm những bước nào?",
    "Biển báo cấm đỗ xe có ý nghĩa gì và áp dụng ở đâu?",
    "Xe ô tô quá hạn kiểm định thì bị xử lý thế nào?",
    "Điều kiện để được đăng ký xe lần đầu là gì?",
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", help="đường dẫn file .gguf")
    ap.add_argument("--tag", default="cpu-run")
    ap.add_argument("--n-threads", type=int, default=None)
    args = ap.parse_args()

    host = L.HostInfo.collect()
    log(f"máy: {host.system} | {host.processor or host.machine} | "
        f"{host.n_cpu_logical} core logic | {host.ram_total_gb} GB RAM")
    log("=> GHI ĐÚNG dòng trên vào phần Thực nghiệm của quyển báo cáo.")

    if not args.gguf:
        log("chưa truyền --gguf, chạy chế độ giả lập để kiểm script")
        import time
        def stream(p):
            time.sleep(0.15)
            for _ in range(64):
                time.sleep(0.02); yield "x"
        res = L.measure(stream, PROMPTS, tag=args.tag + "-mock")
    else:
        try:
            from llama_cpp import Llama
        except ImportError:
            log("Chưa có llama-cpp-python. Cài: pip install llama-cpp-python"); return 1
        cfg = load_yaml("configs/retrieval.yaml")["generation"]
        kw = {"model_path": args.gguf, "n_ctx": cfg["n_ctx"], "verbose": False}
        if args.n_threads:
            kw["n_threads"] = args.n_threads
        llm = Llama(**kw)
        def stream(prompt):
            for chunk in llm(prompt, max_tokens=cfg["max_tokens"],
                             temperature=cfg["temperature"], stream=True):
                yield chunk["choices"][0]["text"]
        res = L.measure(stream, PROMPTS, tag=args.tag)
        res.model_disk_mb = L.dir_size_mb(args.gguf)

    out = ROOT / "results" / "bench" / f"{res.tag}.json"
    L.save(res, out)
    s = res.summary()
    log(f"TTFT median={s['ttft_ms_median']}ms p95={s['ttft_ms_p95']}ms | "
        f"TPOT={s['tpot_ms_median']}ms | {s['tokens_per_s_median']} tok/s | "
        f"RAM đỉnh={s['peak_rss_mb']}MB | đĩa={s['model_disk_mb']}MB")
    append_runlog({"step": "11_bench_cpu", **{k: v for k, v in s.items() if k != "host"}})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
