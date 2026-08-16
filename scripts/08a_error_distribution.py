#!/usr/bin/env python3
"""
Bảng 5 (RQ2) — Phân bố lỗi E1-E6 theo (model, precision) từ nhãn NGƯỜI.

Nhãn hợp nhất theo QUY ƯỚC OR: một trong hai người gán nhãn đánh dấu = tính
có lỗi. Ghi vào caption để hội đồng biết quy ước. Đối chiếu với AC1 ở Bảng 4
để biết độ tin cậy từng mã.

Đầu vào : results/taxonomy/labels_*_{A,B}.jsonl  (output của 07_annotate_cli.py)
Đầu ra  :
  results/tables/error_distribution.json
  results/tables/BANG_5_RQ2.md             (dán trực tiếp vào quyển)
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from _common import ROOT, log, save_json, append_runlog
from viedge.taxonomy.detectors import E_LABELS

LABEL_DIR = ROOT / "results" / "taxonomy"
MIN_N_PER_CELL = 15
CODES = list(E_LABELS)  # E1..E6


# ── helpers ──────────────────────────────────────────────────────────────

def load_labels() -> dict[tuple[str, str], dict[str, list[bool]]]:
    """Gộp nhãn A + B theo (tag, id).
    Trả về: {(tag, id): {Ex: [bool_A, bool_B], ...}}
    """
    merged: dict[tuple[str, str], dict[str, list[bool]]] = defaultdict(
        lambda: {c: [] for c in CODES}
    )
    for who in ("A", "B"):
        files = sorted(LABEL_DIR.glob(f"labels_*_{who}.jsonl"))
        for f in files:
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                key = (r.get("tag", ""), r["id"])
                for c in CODES:
                    merged[key][c].append(bool(r.get("labels", {}).get(c, False)))
    return dict(merged)


def or_merge(labs: dict[str, list[bool]]) -> dict[str, bool]:
    """Quy ước OR: có lỗi nếu BẤT KỲ ai đánh dấu."""
    return {c: any(labs.get(c, [])) for c in CODES}


def parse_tag(tag: str) -> tuple[str, str]:
    if "@" not in tag:
        return tag, ""
    model, prec = tag.split("@", 1)
    return model, prec


# ── tính phân bố ─────────────────────────────────────────────────────────

def compute_distribution(
    merged: dict[tuple[str, str], dict[str, list[bool]]],
) -> dict[str, dict[str, float | str | int]]:
    per_tag_counts: dict[str, dict[str, int]] = defaultdict(lambda: {c: 0 for c in CODES})
    per_tag_n: dict[str, int] = defaultdict(int)

    for (tag, _id), labs in merged.items():
        m = or_merge(labs)
        per_tag_n[tag] += 1
        for c in CODES:
            if m[c]:
                per_tag_counts[tag][c] += 1

    out: dict[str, dict] = {}
    for tag in sorted(per_tag_n):
        n = per_tag_n[tag]
        row: dict[str, float | str | int] = {"n": n}
        for c in CODES:
            if n < MIN_N_PER_CELL:
                row[c] = f"n<{MIN_N_PER_CELL}"
            else:
                row[c] = round(100 * per_tag_counts[tag][c] / n, 1)
        out[tag] = row
    return out


# ── xuất markdown ────────────────────────────────────────────────────────

PREC_ORDER = {
    "bf16": 0, "fp8": 1, "int8": 2, "int4_awq": 3,
    "gguf_q4_k_m": 4, "bnb_nf4": 9,
}


def write_markdown(dist: dict, out_path: Path) -> None:
    lines = [
        "## Bảng 5 (RQ2). Phân bố lỗi E1-E6 theo mức nén "
        "(nhãn người, quy ước OR A/B)",
        "",
        f"Mỗi ô = % mẫu có mã lỗi. Ô có n < {MIN_N_PER_CELL} không diễn giải.",
        "",
    ]

    # Header
    code_headers = " | ".join(
        f"{c} ({E_LABELS[c].split('/')[0].strip()})" for c in CODES
    )
    lines.append(f"| Mô hình | Mức nén | n | {code_headers} |")
    lines.append("|---" * (3 + len(CODES)) + "|")

    # Rows — sắp theo (model, precision)
    tags = sorted(
        dist,
        key=lambda t: (parse_tag(t)[0], PREC_ORDER.get(parse_tag(t)[1], 99)),
    )
    for tag in tags:
        model, prec = parse_tag(tag)
        row = dist[tag]
        cells = [
            f"{row[c]}%" if isinstance(row[c], (int, float)) else str(row[c])
            for c in CODES
        ]
        prec_str = f"**{prec}**" if prec == "bf16" else prec
        lines.append(
            f"| {model} | {prec_str} | {row['n']} | " + " | ".join(cells) + " |"
        )

    lines += [
        "",
        "**Cách đọc.** Với mỗi mô hình, so hàng nén với hàng BF16 để thấy "
        "mã lỗi nào tăng theo mức nén. Đây là bằng chứng ĐỊNH TÍNH về "
        "*chỗ hỏng*, bổ trợ cho Bảng 3 chỉ đo *bao nhiêu hỏng*.",
        "",
        "**Quy ước hợp nhất nhãn.** Nếu một trong hai người gán nhãn đánh dấu "
        "mã Ex = có lỗi. Quy ước OR cho ước lượng chặn TRÊN của tỉ lệ lỗi; "
        "đối chiếu với AC1 ở Bảng 4 để biết độ tin cậy từng mã.",
        "",
        "**Hạn chế.** (1) Nhiệt độ sinh 0.7 khác nhiệt độ 0 của VMLU — tăng "
        "đa dạng để kích lỗi, không phản ánh setup triển khai. (2) Bộ probe "
        "do nhóm thiết kế; mã E4 không tự động được nên nhạy nhất với chủ quan "
        "hai người gán nhãn — đọc kèm Bảng 4.",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ── main ─────────────────────────────────────────────────────────────────

def main() -> int:
    if not any(LABEL_DIR.glob("labels_*.jsonl")):
        raise SystemExit(
            f"chưa có labels_*.jsonl trong {LABEL_DIR.relative_to(ROOT)}\n"
            "   chạy scripts/07_annotate_cli.py trước"
        )

    merged = load_labels()
    log(f"nạp {len(merged)} mẫu có nhãn (union A + B theo id)")

    dist = compute_distribution(merged)
    save_json(dist, "results/tables/error_distribution.json")

    md_path = ROOT / "results" / "tables" / "BANG_5_RQ2.md"
    write_markdown(dist, md_path)
    log(f"đã ghi {md_path.relative_to(ROOT)}")

    # Kiểm ô thiếu mẫu
    under = [tag for tag, row in dist.items() if row["n"] < MIN_N_PER_CELL]
    if under:
        log("")
        log(f"⚠️  {len(under)} tag có n < {MIN_N_PER_CELL}, không diễn giải được:")
        for tag in under:
            log(f"   {tag}  n={dist[tag]['n']}")
        log("   → gán thêm mẫu ở các tag này rồi chạy lại.")

    append_runlog({
        "step": "08a_error_dist",
        "n_tags": len(dist),
        "under": under,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
