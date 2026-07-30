"""
Truy hồi lai cho văn bản pháp luật tiếng Việt.

Ba quyết định thiết kế phải bảo vệ được trước hội đồng:

1. BM25 KHÔNG bỏ được. Câu hỏi pháp lý chứa định danh rời rạc — "Điều 22",
   "biển B.7a", "Nghị định 168". Dense embedding làm nhoè chính xác những
   token này. Lai BM25 + dense ăn cả hai đầu.

2. Dấu tiếng Việt được xử lý HAI CHIỀU: index cả dạng có dấu và dạng bỏ dấu,
   vì người dùng thật gõ không dấu rất nhiều ("bien bao cam do xe").

3. top-k ĐỘNG, không cố định. Số điều luật liên quan mỗi câu dao động mạnh
   (có câu cần 1 điều, có câu cần 10). top-k cố định bóp recall, mà chỉ số
   F2 lại thiên về recall.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from viedge import vitext


def tokenize(text: str, include_folded: bool = True) -> list[str]:
    """Token hoá song ngữ dấu: giữ dạng có dấu, thêm dạng bỏ dấu.

    Nhờ vậy truy vấn "bien bao cam do xe" vẫn khớp "biển báo cấm đỗ xe".
    """
    toks = [w.lower() for w in vitext.words(text)]
    if not include_folded:
        return toks
    out = list(toks)
    for t in toks:
        f = vitext.fold(t)
        if f != t:
            out.append(f)
    return out


class BM25:
    """BM25 Okapi, cài tay để không thêm dependency và để kiểm soát tokenizer."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.doc_ids: list[str] = []
        self.doc_len: list[int] = []
        self.tf: list[Counter] = []
        self.df: Counter = Counter()
        self.avgdl: float = 0.0
        self.N: int = 0

    def fit(self, docs: dict[str, str]) -> "BM25":
        self.doc_ids = list(docs.keys())
        self.tf, self.doc_len, self.df = [], [], Counter()
        for did in self.doc_ids:
            toks = tokenize(docs[did])
            c = Counter(toks)
            self.tf.append(c)
            self.doc_len.append(len(toks))
            for term in c:
                self.df[term] += 1
        self.N = len(self.doc_ids)
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        return self

    def _idf(self, term: str) -> float:
        n_q = self.df.get(term, 0)
        return math.log(1 + (self.N - n_q + 0.5) / (n_q + 0.5))

    def search(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        q_toks = tokenize(query)
        scores: list[tuple[str, float]] = []
        for i, did in enumerate(self.doc_ids):
            tf, dl, s = self.tf[i], self.doc_len[i], 0.0
            for term in q_toks:
                f = tf.get(term, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += self._idf(term) * (f * (self.k1 + 1)) / denom
            if s > 0:
                scores.append((did, s))
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]


class DenseIndex:
    """Index ngữ nghĩa. Nhận vào một hàm encode để không ràng buộc mô hình cụ thể.

    Trong repo này encode được nạp từ configs/retrieval.yaml. Với quy mô kho
    ~400 điều, tìm kiếm vét cạn bằng cosine là đủ nhanh — KHÔNG cần FAISS.
    Đừng thêm phức tạp không cần thiết chỉ vì nghe có vẻ chuyên nghiệp.
    """

    def __init__(self, encode: Callable[[Sequence[str]], list[list[float]]]):
        self.encode = encode
        self.doc_ids: list[str] = []
        self.vecs: list[list[float]] = []

    @staticmethod
    def _norm(v: Sequence[float]) -> list[float]:
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def fit(self, docs: dict[str, str]) -> "DenseIndex":
        self.doc_ids = list(docs.keys())
        raw = self.encode([docs[d] for d in self.doc_ids])
        self.vecs = [self._norm(v) for v in raw]
        return self

    def search(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        q = self._norm(self.encode([query])[0])
        sims = [(self.doc_ids[i], sum(a * b for a, b in zip(q, v))) for i, v in enumerate(self.vecs)]
        sims.sort(key=lambda x: -x[1])
        return sims[:top_k]


def rrf_fuse(
    runs: Iterable[Sequence[tuple[str, float]]],
    k: int = 60,
    weights: Sequence[float] | None = None,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion.

    Hợp nhất theo HẠNG chứ không theo điểm, nên không cần chuẩn hoá thang
    điểm giữa BM25 (không chặn trên) và cosine (trong [-1,1]). Đây là lý do
    RRF hợp hơn weighted-sum cho bài này.
    """
    runs = list(runs)
    if weights is None:
        weights = [1.0] * len(runs)
    if len(weights) != len(runs):
        raise ValueError("weights phải cùng độ dài với runs")
    acc: dict[str, float] = defaultdict(float)
    for w, run in zip(weights, runs):
        for rank, (doc_id, _score) in enumerate(run, start=1):
            acc[doc_id] += w / (k + rank)
    fused = sorted(acc.items(), key=lambda x: -x[1])
    return fused


def dynamic_top_k(
    fused: Sequence[tuple[str, float]],
    min_k: int = 1,
    max_k: int = 10,
    drop_ratio: float = 0.55,
) -> list[tuple[str, float]]:
    """Cắt danh sách tại điểm sụt lớn nhất, trong khung [min_k, max_k].

    Thay cho top-5 cố định. Cắt tại chỗ điểm RRF tụt mạnh nhất so với điểm
    đầu, nên câu hỏi cần 1 điều thì trả 1, câu cần 8 điều thì trả 8.
    """
    if not fused:
        return []
    fused = list(fused[:max_k])
    if len(fused) <= min_k:
        return fused
    top = fused[0][1] or 1e-9
    cut = len(fused)
    for i in range(min_k, len(fused)):
        if fused[i][1] / top < drop_ratio:
            cut = i
            break
    return fused[: max(min_k, cut)]


@dataclass
class HybridRetriever:
    bm25: BM25
    dense: DenseIndex | None = None
    rrf_k: int = 60
    bm25_weight: float = 1.0
    dense_weight: float = 1.0
    pool: int = 30
    min_k: int = 1
    max_k: int = 10
    drop_ratio: float = 0.55

    def retrieve(self, query: str) -> list[tuple[str, float]]:
        runs = [self.bm25.search(query, top_k=self.pool)]
        weights = [self.bm25_weight]
        if self.dense is not None:
            runs.append(self.dense.search(query, top_k=self.pool))
            weights.append(self.dense_weight)
        fused = rrf_fuse(runs, k=self.rrf_k, weights=weights)
        return dynamic_top_k(
            fused, min_k=self.min_k, max_k=self.max_k, drop_ratio=self.drop_ratio
        )


# ---------------------------------------------------------------------------
# Chỉ số đánh giá truy hồi
# ---------------------------------------------------------------------------


def prf(retrieved: Sequence[str], gold: Sequence[str], beta: float = 2.0) -> dict[str, float]:
    """Precision / Recall / F-beta. beta=2 vì recall quan trọng hơn khi trích luật:
    thiếu một điều thì câu trả lời sai; thừa một điều chỉ tốn ngữ cảnh."""
    r, g = set(retrieved), set(gold)
    if not g:
        return {"precision": 0.0, "recall": 0.0, f"f{beta:g}": 0.0}
    tp = len(r & g)
    p = tp / len(r) if r else 0.0
    rec = tp / len(g)
    b2 = beta * beta
    f = ((1 + b2) * p * rec / (b2 * p + rec)) if (p + rec) else 0.0
    return {"precision": p, "recall": rec, f"f{beta:g}": f}
