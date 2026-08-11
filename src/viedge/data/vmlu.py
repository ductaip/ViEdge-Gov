"""
Lấy mẫu phân tầng VMLU.

VMLU (Zalo AI x JAIST) là chuẩn "Make in Vietnam": 10.880 câu trắc nghiệm,
58 môn, 4 nhóm (STEM / Khoa học xã hội / Nhân văn / Khác). Nguồn:
  - github.com/ZaloAI-Jaist/VMLU
  - HuggingFace: anhdungitvn/vmlu_v1.5

Vì sao phải LẤY MẪU: chạy full 10.880 câu x 4 model x 4 mức nén = 174k lượt
suy luận, vượt ngân sách T4. Lấy mẫu phân tầng ~2.000 câu giữ nguyên tỉ lệ
58 môn, kèm seed cố định, là cách chuẩn để giảm chi phí mà vẫn báo cáo được.

BẮT BUỘC ghi vào báo cáo: kích thước mẫu, seed, và quy trình phân tầng.
Hội đồng sẽ hỏi "vì sao không chạy hết" — câu trả lời là ngân sách compute,
nói thẳng, kèm phân tích sai số lấy mẫu (xem sampling_error_note()).
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

SUBJECT_KEY_CANDIDATES = ("subject", "subject_name", "category", "topic")
ANSWER_KEYS = ("answer", "answer_key", "label", "gold")


def detect_subject_key(rows: list[dict]) -> str:
    """Cột môn học. Bản CHÍNH THỨC từ vmlu.ai KHÔNG có cột này — môn nằm ở tiền
    tố của `id` ("28-0001" -> môn 28). Trả về "id" để báo dùng đường tiền tố."""
    for k in SUBJECT_KEY_CANDIDATES:
        if rows and k in rows[0]:
            return k
    if rows and "id" in rows[0] and "-" in str(rows[0]["id"]):
        return "id"
    raise KeyError(f"Không tìm thấy cột môn học trong {list(rows[0].keys()) if rows else []}")


def subject_of(row: dict, key: str | None = None) -> str:
    """Môn học của một câu, chịu được cả hai kiểu schema."""
    if key is None:
        for k in SUBJECT_KEY_CANDIDATES:
            if k in row:
                key = k
                break
        else:
            key = "id"
    if key == "id":
        return str(row.get("id", "")).split("-")[0]
    return str(row.get(key, "UNKNOWN"))


def n_choices(row: dict) -> int:
    ch = row.get("choices")
    if isinstance(ch, (list, tuple)):
        return len(ch)
    if isinstance(ch, str):
        return len([l for l in ch.splitlines() if l.strip()])
    return sum(1 for k in "ABCDE" if row.get(k))


def choice_count_stats(rows: list[dict]) -> dict:
    return dict(sorted(Counter(n_choices(r) for r in rows).items()))


def random_baseline(rows: list[dict]) -> float:
    """Mức đoán mò THỰC TẾ.

    VMLU có câu 3, 4 và 5 lựa chọn, nên mốc KHÔNG phải 0,25 cố định. Dùng 0,25
    khi bộ có câu 3 lựa chọn sẽ ĐÁNH GIÁ THẤP mức đoán mò -> tưởng model có
    năng lực trong khi nó chỉ đang đoán. Sai lầm này đi thẳng vào kết luận RQ1.
    """
    ns = [n_choices(r) for r in rows if n_choices(r) > 0]
    return sum(1.0 / n for n in ns) / len(ns) if ns else 0.25


def answer_balance(rows: list[dict]) -> dict:
    c = Counter()
    for r in rows:
        for k in ANSWER_KEYS:
            v = r.get(k)
            if v is not None and str(v).strip():
                c[str(v).strip().upper()[:1]] += 1
                break
    return dict(sorted(c.items()))


def load_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def stratified_sample(
    rows: list[dict],
    n_target: int,
    subject_key: str | None = None,
    seed: int = 20260825,
    min_per_stratum: int = 5,
) -> list[dict]:
    """Lấy mẫu phân tầng theo môn, giữ tỉ lệ, đảm bảo mỗi môn tối thiểu N câu."""
    if n_target >= len(rows):
        return list(rows)
    key = subject_key or detect_subject_key(rows)
    rng = random.Random(seed)
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        buckets[subject_of(r, key)].append(r)

    total = len(rows)
    quotas: dict[str, int] = {}
    for subj, items in buckets.items():
        q = round(n_target * len(items) / total)
        quotas[subj] = max(min_per_stratum, min(len(items), q))

    # Hiệu chỉnh để tổng khớp n_target
    def total_q() -> int:
        return sum(quotas.values())

    subjects = sorted(buckets)
    while total_q() > n_target:
        adjustable = [s for s in subjects if quotas[s] > min_per_stratum]
        if not adjustable:
            break
        s = max(adjustable, key=lambda x: quotas[x])
        quotas[s] -= 1
    while total_q() < n_target:
        adjustable = [s for s in subjects if quotas[s] < len(buckets[s])]
        if not adjustable:
            break
        s = min(adjustable, key=lambda x: quotas[x] / len(buckets[x]))
        quotas[s] += 1

    out: list[dict] = []
    for subj in subjects:
        items = sorted(buckets[subj], key=lambda r: str(r.get("id", "")))
        out.extend(rng.sample(items, quotas[subj]))
    rng.shuffle(out)
    return out


def sampling_error_note(n_sample: int, n_pop: int, p: float = 0.5, z: float = 1.96) -> dict:
    """Sai số lấy mẫu tối đa cho tỉ lệ chính xác — đưa vào phụ lục báo cáo."""
    if n_sample <= 0:
        return {"margin_of_error": float("nan")}
    fpc = math.sqrt((n_pop - n_sample) / (n_pop - 1)) if n_pop > 1 else 1.0
    moe = z * math.sqrt(p * (1 - p) / n_sample) * fpc
    return {
        "n_sample": n_sample,
        "n_population": n_pop,
        "margin_of_error_abs": round(moe, 4),
        "margin_of_error_pct": round(moe * 100, 2),
        "note": "MoE ở mức tin cậy 95%, giả định p=0.5 (trường hợp xấu nhất), có hiệu chỉnh mẫu hữu hạn.",
    }


def coverage_report(sample: list[dict], population: list[dict], subject_key: str | None = None) -> dict:
    key = subject_key or detect_subject_key(population)
    cs = Counter(subject_of(r, key) for r in sample)
    cp = Counter(subject_of(r, key) for r in population)
    max_dev = 0.0
    for subj in cp:
        share_p = cp[subj] / len(population)
        share_s = cs.get(subj, 0) / len(sample) if sample else 0
        max_dev = max(max_dev, abs(share_p - share_s))
    return {
        "n_subjects_population": len(cp),
        "n_subjects_sample": len(cs),
        "missing_subjects": sorted(set(cp) - set(cs)),
        "max_share_deviation": round(max_dev, 4),
    }
