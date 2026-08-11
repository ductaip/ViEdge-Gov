#!/usr/bin/env python3
"""
SÀNG model ứng viên: đo TRẦN tiếng Việt ở BF16 trước khi cam kết cả ma trận.

VÌ SAO ĐÂY LÀ BƯỚC BẮT BUỘC, KHÔNG PHẢI CHO ĐẸP:

Đề tài đo SUY GIẢM. Suy giảm là hiệu số giữa trần (BF16) và các bậc nén. Nếu một
model vốn đã gần như không biết tiếng Việt, trần của nó nằm sát ngưỡng đoán mò
(25% với trắc nghiệm 4 lựa chọn). Khi đó:

    int4 tụt từ 27% xuống 25%  ->  "suy giảm 2 điểm"

Con số đó VÔ NGHĨA — cả hai đều là nhiễu quanh mức đoán mò. Đây là **hiệu ứng sàn**
(floor effect), và nó không lộ ra trong bảng kết quả: bảng vẫn có số, vẫn vẽ được
đồ thị, vẫn trông như một phát hiện. Hội đồng phản biện biết đọc ra ngay.

Quy tắc chốt: model chỉ dùng được nếu **trần BF16 cao hơn mức đoán mò đủ xa** để
còn chỗ cho suy giảm biểu hiện. Ngưỡng đề nghị: headroom >= 10 điểm phần trăm.

Script này đo hai thứ cho từng ứng viên:
  1. Accuracy trên N câu VMLU (trần định lượng)
  2. Sinh tự do tiếng Việt -> tỉ lệ dấu, mojibake, chuyển ngữ (trần định tính)

Chạy TRƯỚC `make export`. Mất ~10 phút, tiết kiệm cả ngày GPU chạy nhầm model.

    python scripts/00g_screen_models.py --n 200
    python scripts/00g_screen_models.py --n 200 --extra Qwen/Qwen2.5-1.5B-Instruct
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from _common import ROOT, load_yaml, log, save_json

sys.path.insert(0, str(ROOT / "configs" / "lm_eval_tasks"))

# ⚠️ KHÔNG cứng 0.25: VMLU có câu 3, 4 và 5 lựa chọn. Dùng 0.25 khi bộ có câu
# 3 lựa chọn sẽ ĐÁNH GIÁ THẤP mức đoán mò -> tưởng model có năng lực trong khi
# nó chỉ đang đoán. Giá trị thật tính từ dữ liệu trong main().
RANDOM_BASELINE = 0.25          # chỉ là mặc định; bị ghi đè bởi dữ liệu thật
MIN_HEADROOM = 0.10             # trần phải hơn đoán mò >= 10 điểm phần trăm
MIN_DIACRITIC = 0.15            # văn bản tiếng Việt sạch thường 0.18-0.35

VI_PROMPTS = [
    "Hãy giải thích ngắn gọn thủ tục đăng ký xe ô tô lần đầu tại Việt Nam.",
    "Viết một đoạn 150 từ về vai trò của biển báo hiệu đường bộ đối với an toàn giao thông.",
    "Nêu ba nghĩa vụ của người điều khiển phương tiện tham gia giao thông đường bộ.",
    "Tóm tắt vì sao cần giữ khoảng cách an toàn giữa các xe khi lưu thông trên đường cao tốc.",
]


def load_vmlu(n: int) -> list[dict]:
    for rel in ("data/processed/vmlu_sampled.jsonl", "data/raw/vmlu_full.jsonl"):
        p = ROOT / rel
        if p.exists():
            rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
            log(f"dùng {rel} ({len(rows)} câu, lấy {min(n, len(rows))})")
            return rows[:n]
    return []


def _choice_token_ids(tok, choices: list[str]):
    """id token ĐẦU TIÊN của từng lựa chọn (" A", " B", ...).

    Trả None nếu có lựa chọn không mã hoá được thành ít nhất 1 token.
    """
    ids = []
    for ch in choices:
        enc = tok(ch, add_special_tokens=False).input_ids
        if not enc:
            return None
        ids.append(enc[0])
    return ids if len(set(ids)) == len(ids) else None


def score_mcq(model, tok, docs: list[dict], device: str, max_len: int = 1536) -> float:
    """Accuracy bằng loglikelihood.

    HAI SỬA QUAN TRỌNG so với bản đầu (bản đầu làm sập CUDA trên 6GB):

    1. MỘT forward cho MỖI CÂU, không phải một forward cho MỖI LỰA CHỌN.
       Đáp án là chữ cái đơn (" A".." E") -> chỉ cần logits ở VỊ TRÍ CUỐI của
       ngữ cảnh rồi đọc xác suất từng chữ cái. Bản cũ chạy 4-5 forward/câu:
       với 200 câu là ~900 lượt thay vì 200.

    2. KHÔNG ép cả ma trận logits sang float32. Bản cũ gọi
       `logits[0, :-1].float()` — với vocab 151k và seq 200 token, riêng bản
       float32 đó đã ~122 MB, cộng thêm log_softmax ra bản thứ hai. Lặp 900 lần
       trên GPU 6GB đang giữ 3,5 GB trọng số -> phân mảnh bộ nhớ và CUDA vào
       trạng thái hỏng, báo `cudaErrorUnknown` chứ không báo OOM tử tế.
       Nay chỉ lấy MỘT hàng logits (vị trí cuối) rồi mới float().
    """
    import torch
    import utils

    correct = 0
    for i, d in enumerate(docs):
        ctx = utils.doc_to_text(d)
        choices = utils.doc_to_choice(d)
        gold = utils.doc_to_target(d)

        enc = tok(ctx, return_tensors="pt", truncation=True, max_length=max_len)
        input_ids = enc.input_ids.to(device)

        cids = _choice_token_ids(tok, choices)
        with torch.inference_mode():
            out = model(input_ids)
            if cids is not None:
                # Đường nhanh: chỉ cần hàng logits cuối cùng
                row = out.logits[0, -1].float()
                lp = torch.log_softmax(row, dim=-1)
                scores = [lp[c].item() for c in cids]
            else:
                # Đường chậm: lựa chọn nhiều token -> chấm từng lựa chọn
                scores = []
                n_ctx = input_ids.shape[1]
                for ch in choices:
                    full = tok(ctx + ch, return_tensors="pt", truncation=True,
                               max_length=max_len).input_ids.to(device)
                    o = model(full)
                    tgt = full[0, n_ctx:]
                    if tgt.numel() == 0:
                        scores.append(float("-inf")); continue
                    rows = o.logits[0, n_ctx - 1: -1].float()
                    lp = torch.log_softmax(rows, dim=-1)
                    scores.append(lp.gather(1, tgt.unsqueeze(1)).sum().item())
                    del o, rows, lp

        if max(range(len(scores)), key=lambda j: scores[j]) == gold:
            correct += 1
        del out, input_ids
        # Dọn định kỳ: giữ phân mảnh trong tầm kiểm soát trên GPU nhỏ
        if device == "cuda" and (i + 1) % 50 == 0:
            torch.cuda.empty_cache()
    return correct / len(docs) if docs else 0.0


def probe_vietnamese(model, tok, device: str, max_new: int = 120) -> dict:
    import torch
    from viedge import vitext
    outs = []
    for p in VI_PROMPTS:
        msgs = [{"role": "user", "content": p}]
        try:
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        except Exception:
            text = p + "\n"
        ids = tok(text, return_tensors="pt", truncation=True,
                  max_length=1024).input_ids.to(device)
        with torch.inference_mode():
            gen = model.generate(ids, max_new_tokens=max_new, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        outs.append(tok.decode(gen[0, ids.shape[1]:], skip_special_tokens=True))
    joined = "\n".join(outs)
    return {
        "diacritic_ratio": round(vitext.diacritic_ratio(joined), 4),
        "n_mojibake": len(vitext.mojibake_hits(joined)),
        "n_foreign_script": len(vitext.foreign_script_hits(joined)),
        "n_english_runs": len(vitext.english_run_hits(joined)),
        "sample": outs[0][:220].replace("\n", " "),
    }


def verdict(acc: float, vi: dict, baseline: float = RANDOM_BASELINE) -> tuple[str, str]:
    head = acc - baseline
    if head < MIN_HEADROOM:
        return "❌ LOẠI", (f"trần BF16 {acc:.1%} chỉ hơn đoán mò {head:+.1%} — "
                          "hiệu ứng sàn, đo suy giảm sẽ vô nghĩa")
    if vi["diacritic_ratio"] < MIN_DIACRITIC:
        return "❌ LOẠI", (f"tỉ lệ dấu {vi['diacritic_ratio']} quá thấp — "
                          "model gần như không sinh tiếng Việt có dấu ở BF16")
    if vi["n_mojibake"] or vi["n_foreign_script"] > 2:
        return "⚠️ CÂN NHẮC", "đã lỗi tiếng Việt NGAY Ở BF16 — trần đã bẩn, khó quy lỗi cho nén"
    return "✅ DÙNG ĐƯỢC", f"headroom {head:+.1%}, còn chỗ cho suy giảm biểu hiện"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="số câu VMLU để đo trần")
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--skip-gen", action="store_true", help="bỏ phần sinh tự do (nhanh hơn)")
    ap.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto",
                    help="ép thiết bị; cpu chậm nhưng luôn chạy được")
    args = ap.parse_args()

    docs = load_vmlu(args.n)
    if not docs:
        log("chưa có dữ liệu VMLU — chạy `make sample` trước"); return 1
    from viedge.data import vmlu as V
    baseline = V.random_baseline(docs)
    log(f"mức đoán mò thực tế trên {len(docs)} câu này = {baseline:.4f} "
        f"(số lựa chọn: {V.choice_count_stats(docs)})")

    cfg = load_yaml("configs/experiments.yaml")
    cands = [(m["tag"], m["hf_id"]) for m in cfg["models"] if m.get("priority", "P0") == "P0"]
    cands += [(e.split("/")[-1].lower(), e) for e in args.extra]

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        log(f"thiếu thư viện: {e}"); return 1

    from viedge.env import hf_token, mask
    tok_hf = hf_token()
    log(f"HF_TOKEN: {mask(tok_hf)}")
    if not tok_hf:
        log("  (không có token -> tải chậm hơn do rate limit; tạo .env từ .env.example)")

    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    if device == "cuda":
        props = torch.cuda.get_device_properties(0)
        log(f"thiết bị: cuda — {props.name}, {props.total_memory/1024**3:.1f} GB VRAM")
    else:
        log("thiết bị: CPU — sẽ RẤT chậm. Kiểm `make doctor` xem torch có thấy GPU không.")
    log("Lần đầu mỗi model phải TẢI VỀ (~3.5 GB cho 1.5B). Các lần sau dùng cache,")
    log("không tải lại. Cache nằm ở $HF_HOME hoặc ~/.cache/huggingface.")

    rows = []
    for tag, repo in cands:
        log(f"--- {tag} ({repo}) ---")
        try:
            kw = {"trust_remote_code": True}
            if tok_hf:
                kw["token"] = tok_hf
            tok = AutoTokenizer.from_pretrained(repo, **kw)
            model = AutoModelForCausalLM.from_pretrained(
                repo, dtype=torch.bfloat16 if device == "cuda" else torch.float32,
                device_map=device, low_cpu_mem_usage=True, **kw).eval()
            if device == "cuda":
                torch.cuda.reset_peak_memory_stats()
                used = torch.cuda.memory_allocated() / 1024**3
                log(f"  đã nạp, chiếm {used:.2f} GB VRAM")
        except Exception as e:
            log(f"KHÔNG NẠP ĐƯỢC: {type(e).__name__}: {str(e)[:90]}")
            rows.append({"tag": tag, "repo": repo, "status": "❌ LỖI NẠP", "note": str(e)[:60]})
            continue

        try:
            acc = score_mcq(model, tok, docs, device)
        except Exception as e:
            name = type(e).__name__
            log(f"  LỖI khi chấm: {name}: {str(e)[:100]}")
            if "CUDA" in str(e) or "cuda" in name.lower():
                log("  Chẩn đoán CUDA:")
                log("    1. Chạy lại với CUDA_LAUNCH_BLOCKING=1 để thấy lỗi THẬT:")
                log("       CUDA_LAUNCH_BLOCKING=1 python scripts/00g_screen_models.py --n 50")
                log("    2. Giảm tải: --n 50 (ít câu hơn) và --skip-gen")
                log("    3. GPU laptop hay tụt xung/mất context khi tiết kiệm điện —")
                log("       cắm sạc, đặt chế độ hiệu năng cao, đóng ứng dụng dùng GPU khác")
                log("    4. nvidia-smi xem GPU còn trống bao nhiêu (trình duyệt cũng ăn VRAM)")
                log("    5. Nếu vẫn lỗi: --device cpu (chậm nhưng ra được số để sàng)")
            rows.append({"tag": tag, "repo": repo, "status": "❌ LỖI CHẤM", "note": str(e)[:70]})
            del model, tok
            import gc; gc.collect()
            if device == "cuda":
                torch.cuda.empty_cache()
            continue
        vi = {"diacritic_ratio": 1.0, "n_mojibake": 0, "n_foreign_script": 0,
              "n_english_runs": 0, "sample": "(bỏ qua)"}
        if not args.skip_gen:
            vi = probe_vietnamese(model, tok, device)
        # Đỉnh VRAM trong lúc CHẤM (batch 1). Eval chính thức chạy batch 4 nên
        # tốn hơn — ước lượng thêm phần KV cache tăng theo batch.
        peak = vram_load = 0.0
        if device == "cuda":
            peak = torch.cuda.max_memory_allocated() / 1024**3
            vram_load = torch.cuda.memory_allocated() / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            kv_b1 = max(peak - vram_load, 0.05)
            est_b4 = vram_load + kv_b1 * 4
            flag = "✅" if est_b4 < total * 0.92 else "⚠️ RỦI RO OOM"
            log(f"  VRAM: trọng số {vram_load:.2f} GB | đỉnh khi chấm (batch 1) {peak:.2f} GB")
            log(f"        ước tính eval batch 4: ~{est_b4:.2f} / {total:.1f} GB  {flag}")
            if est_b4 >= total * 0.92:
                log("        -> giảm evaluation.batch_size trong configs/experiments.yaml")

        st, note = verdict(acc, vi, baseline)
        log(f"  accuracy VMLU({len(docs)}) = {acc:.1%} | tỉ lệ dấu = {vi['diacritic_ratio']}")
        log(f"  mẫu sinh: {vi['sample'][:150]}")
        log(f"  => {st}: {note}")
        rows.append({"tag": tag, "repo": repo, "status": st, "acc_bf16": round(acc, 4),
                     "random_baseline": round(baseline, 4),
                     "headroom": round(acc - baseline, 4),
                     "vram_weights_gb": round(vram_load, 2),
                     "vram_peak_b1_gb": round(peak, 2), **vi, "note": note})
        # Giải phóng đúng cách trước khi nạp model kế: nếu không, model thứ hai
        # OOM trên 6GB dù bản thân nó vừa.
        del model, tok
        import gc; gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

    # Biên tụt tính trên cỡ mẫu EVAL CHÍNH THỨC, không phải cỡ mẫu sàng.
    # Ngưỡng sàn phụ thuộc mạnh vào n: sàng 200 câu cho ngưỡng 30,3% còn eval
    # 1.047 câu cho 27,4%. Đọc nhầm cột này theo cỡ mẫu sàng sẽ loại oan model.
    from viedge.eval.significance import floor_accuracy
    n_eval = 0
    sp = ROOT / "data" / "processed" / "vmlu_sampled.jsonl"
    if sp.exists():
        n_eval = sum(1 for l in sp.read_text(encoding="utf-8").splitlines() if l.strip())
    floor_full = floor_accuracy(n_eval, baseline) if n_eval else None

    print(f"\n{'TAG':<20}{'ACC':>8}{'HEADROOM':>10}{'DẤU':>8}{'MOJI':>6}"
          f"{'BIÊN TỤT':>10}  KẾT LUẬN")
    print("-" * 100)
    for r in rows:
        acc = r.get("acc_bf16", 0)
        budget = f"{(acc - floor_full) * 100:>8.1f}đ" if floor_full and acc else "     —"
        print(f"{r['tag']:<20}{acc:>8.1%}{r.get('headroom', 0):>+10.1%}"
              f"{r.get('diacritic_ratio', 0):>8.3f}{r.get('n_mojibake', 0):>6}"
              f"{budget:>10}  {r['status']}")
    if floor_full:
        print(f"\n  BIÊN TỤT = số điểm còn tụt được trên eval chính thức (n={n_eval}) "
              f"trước khi chạm sàn {floor_full:.1%}.")
        print("  Nén 4-bit thường làm tụt 3-8 điểm ở cỡ model này -> biên >= 12đ là an toàn.")
    save_json(rows, "results/tables/model_screening.json")

    ok = [r for r in rows if r["status"].startswith("✅")]
    print()
    if len(ok) < 2:
        log(f"CHỈ CÓ {len(ok)} model đạt. P0 cần >= 2 để đường cong có ý nghĩa so sánh.")
        log("Thử ứng viên khác bằng --extra <repo_id>.")
    else:
        log(f"{len(ok)} model đạt: {[r['tag'] for r in ok]} — chốt vào configs/experiments.yaml rồi export.")
    log("Bảng này đưa vào PHỤ LỤC quyển: nó chứng minh việc chọn model có căn cứ,")
    log("không phải chọn bừa — đúng thứ hội đồng hỏi ở câu phản biện số 6.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
