"""
Demo offline. Chạy: make demo   (hoặc python -m viedge.serve.app)

KỊCH BẢN DIỄN TRƯỚC HỘI ĐỒNG CHUNG KẾT — tập đến mức phản xạ:
  1. Mở app, cho hội đồng thấy đây là máy văn phòng bình thường
  2. RÚT CÁP MẠNG / TẮT WIFI NGAY TRƯỚC MẶT HỘI ĐỒNG
  3. Đặt câu hỏi bất kỳ về thủ tục hoặc mức phạt
  4. Chỉ vào phần "Căn cứ pháp lý" — mỗi câu trả lời đều truy được về điều khoản
  5. Chỉ vào chỉ số RAM/tốc độ hiển thị ở góc
Không có đề tài RAG gọi API nào làm được bước 2. Đây là khoảnh khắc quyết định
thứ hạng — chuẩn bị nó nghiêm túc như chuẩn bị bảng số liệu.

DỰ PHÒNG BẮT BUỘC: quay video demo trước, để trong USB. Máy hỏng tại chỗ là
chuyện thường xảy ra.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load_assistant(gguf_path: str | None = None):
    from viedge.data import corpus as CO
    from viedge.rag import citations as C
    from viedge.rag import retrieval as R
    from viedge.rag.pipeline import Assistant

    proc = ROOT / "data" / "processed"
    units = json.loads((proc / "units.json").read_text(encoding="utf-8"))
    with (proc / "bm25.pkl").open("rb") as f:
        bm = pickle.load(f)
    arts = CO.load_articles(proc / "articles.jsonl")
    index = C.CitationIndex.from_articles(arts)
    retriever = R.HybridRetriever(bm25=bm)

    if gguf_path:
        from llama_cpp import Llama

        llm = Llama(model_path=gguf_path, n_ctx=8192, verbose=False)

        def generator(system: str, user: str) -> str:
            out = llm.create_chat_completion(
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.0, max_tokens=512,
            )
            return out["choices"][0]["message"]["content"]
    else:
        def generator(system: str, user: str) -> str:
            return ("[CHƯA NẠP MÔ HÌNH] Truyền --gguf để chạy thật. "
                    "Ngữ cảnh đã truy hồi được hiển thị bên dưới.")

    return Assistant(retriever=retriever, generator=generator, index=index, unit_text=units)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", help="đường dẫn .gguf (bỏ trống = chế độ chỉ truy hồi)")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--cli", action="store_true", help="chạy ở terminal, không cần gradio")
    args = ap.parse_args()

    asst = load_assistant(args.gguf)

    if args.cli:
        print("Trợ lý tra cứu offline. Ctrl-C để thoát.\n")
        while True:
            try:
                q = input("Hỏi > ").strip()
            except (EOFError, KeyboardInterrupt):
                print(); return 0
            if not q:
                continue
            a = asst.answer(q)
            print("\n" + a.render())
            print(f"\n[căn cứ truy hồi: {', '.join(a.retrieved) or 'không có'}]\n")

    try:
        import gradio as gr
    except ImportError:
        print("Chưa có gradio. Cài `pip install gradio` hoặc chạy với --cli"); return 1

    def respond(q: str):
        a = asst.answer(q)
        cites = "\n\n".join(f"**{u}**\n\n{asst.unit_text.get(u,'')[:900]}" for u in a.retrieved)
        status = "🟢 hợp lệ" if not a.blocked else f"🔴 đã chặn — {a.block_reason}"
        return a.render(), cites or "_không truy hồi được điều luật nào_", status

    with gr.Blocks(title="ViEdge-Gov — trợ lý tra cứu offline") as demo:
        gr.Markdown(
            "# ViEdge-Gov\n"
            "### Trợ lý tra cứu thủ tục hành chính & pháp luật giao thông — **chạy hoàn toàn ngoại tuyến**\n"
            "Không gọi API. Không gửi dữ liệu ra ngoài. Có thể rút cáp mạng và vẫn hoạt động."
        )
        with gr.Row():
            with gr.Column(scale=3):
                q = gr.Textbox(label="Câu hỏi", placeholder="Không mang giấy phép lái xe bị phạt bao nhiêu?")
                btn = gr.Button("Tra cứu", variant="primary")
                ans = gr.Markdown(label="Trả lời")
                st = gr.Textbox(label="Cửa kiểm tra trích dẫn", interactive=False)
            with gr.Column(scale=2):
                ctx = gr.Markdown(label="Căn cứ pháp lý đã truy hồi")
        btn.click(respond, inputs=q, outputs=[ans, ctx, st])
        q.submit(respond, inputs=q, outputs=[ans, ctx, st])

    demo.launch(server_port=args.port, share=False)  # share=False: giữ đúng tinh thần offline
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
