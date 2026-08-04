"""
Lớp phủ sửa đổi: nối văn bản SỬA ĐỔI vào đúng điều mà nó sửa.

BÀI TOÁN. Nghị định 238/2026 sửa đổi Nghị định 168/2024, hiệu lực 15/08/2026.
Đọc riêng NĐ 238 gần như vô dụng vì nó chỉ chứa phần thay đổi:

    "Điều 2. Sửa đổi, bổ sung một số điểm, khoản của Điều 6
     1. Bổ sung khoản 1a vào trước khoản 1 như sau:
     '1a. Phạt cảnh cáo đối với người điều khiển xe ô tô chở trẻ em dưới 10 tuổi...'"

Muốn trả lời "chở trẻ em dưới 10 tuổi bị phạt gì" thì phải có CẢ HAI văn bản,
và phải biết khoản 1a này thuộc về Điều 6 của NĐ 168.

VÌ SAO KHÔNG HỢP NHẤT BẰNG CÁCH GHÉP VĂN BẢN. Nghe thì gọn, nhưng Điều 19 của
NĐ 238 có 17 thao tác ở mức CỤM TỪ, kiểu:

    "Bổ sung cụm từ ', trừ hành vi vi phạm quy định tại điểm b khoản 3a Điều 29
     của Nghị định này' vào sau cụm từ 'xe được kéo khi kéo nhau' tại điểm h
     khoản 3 Điều 6."

Tự động áp dụng chuỗi thao tác đó lên văn bản gốc là một đề tài riêng, và sai
một thao tác thì mức phạt trong ViGovQA-GT sai theo mà không ai phát hiện.

CÁCH LÀM Ở ĐÂY. Giữ hai văn bản RIÊNG trong kho, dựng một chỉ mục ánh xạ
"điều bị sửa" -> "các quy định sửa nó". Khi truy hồi trả về Điều 6 của NĐ 168,
lớp phủ tự chèn thêm phần NĐ 238 sửa Điều 6, có đánh dấu hiệu lực.

Được ba thứ:
  1. Không có rủi ro ghép sai văn bản.
  2. Giữ nguyên xuất xứ — câu trả lời trích dẫn được cả hai, người dùng tự kiểm.
  3. Mốc 15/08/2026 xử lý được tự nhiên: trước mốc thì tắt lớp phủ, sau thì bật.
     Đây chính là cơ chế đo "độ trễ pháp lý" ở ADR-008.

Lưu ý phạm vi: truy vết hiệu lực/sửa đổi văn bản pháp luật tiếng Việt đã có
công trình đi trước (ViHERMES). Ở đề tài này nó là MỘT THÀNH PHẦN HỆ THỐNG
phục vụ trục ứng dụng, không phải tuyên bố tính mới. Viết đúng như vậy trong
quyển — nhận công không phải của mình là chỗ hội đồng phản biện bắt lỗi nhanh nhất.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

# "Điều 2. Sửa đổi, bổ sung một số điểm, khoản của Điều 6"
_ART_HEAD = re.compile(r"^\s*Điều\s+(\d+[a-zA-Z]?)\s*[.．:]\s*(.*)$", re.MULTILINE)

# Động từ báo hiệu đây là điều SỬA ĐỔI, không phải điều nội dung.
_OP_WORDS = ("sửa đổi", "bổ sung", "thay thế", "bãi bỏ", "bỏ cụm từ")

# Trong tiêu đề: điều bị sửa là "Điều N" xuất hiện SAU CÙNG.
_DIEU_REF = re.compile(r"Điều\s+(\d+[a-zA-Z]?)")

# Với điều kiểu "Điều 19" (sửa cụm từ, không nêu mục tiêu ở tiêu đề), phải quét
# thân. Cạm bẫy: phần văn bản ĐƯỢC CHÈN nằm trong ngoặc kép và bản thân nó cũng
# trích dẫn điều khác — vd. chèn cụm từ '... quy định tại điểm b khoản 3a Điều 29
# của Nghị định này'. Điều 29 ở đây là trích dẫn chéo trong nội dung mới, KHÔNG
# phải điều bị sửa. Vì vậy: bỏ mọi đoạn trong ngoặc kép TRƯỚC khi dò mục tiêu.
_QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
_SELF_REF = re.compile(r"Điều\s+này", re.IGNORECASE)


def _strip_quoted(text: str) -> str:
    """Xoá nội dung trong ngoặc kép — đó là văn bản được chèn, không phải vị trí."""
    return _SELF_REF.sub("", _QUOTED.sub(" ", text))

_KHOAN = re.compile(r"khoản\s+(\d+[a-zA-Z]?)", re.IGNORECASE)
_DIEM = re.compile(r"điểm\s+([a-zđ]\d?)\b", re.IGNORECASE)


@dataclass
class Amendment:
    """Một quy định sửa đổi, đã biết nó sửa điều nào của văn bản nào."""

    source_doc: str          # vd. "Nghị định 238/2026/NĐ-CP"
    source_dieu: str         # điều số mấy TRONG văn bản sửa đổi
    target_doc: str          # vd. "Nghị định 168/2024/NĐ-CP"
    target_dieu: str         # điều bị sửa
    title: str
    text: str
    effective_date: str = ""
    khoan: list[str] = field(default_factory=list)
    diem: list[str] = field(default_factory=list)

    @property
    def target_unit_id(self) -> str:
        return f"{self.target_doc}::dieu-{self.target_dieu}"

    def render(self) -> str:
        loc = ""
        if self.khoan:
            loc = " (khoản " + ", ".join(self.khoan[:4]) + ")"
        return (
            f"[SỬA ĐỔI — {self.source_doc}, Điều {self.source_dieu}"
            f"{', hiệu lực ' + self.effective_date if self.effective_date else ''}]"
            f"{loc}\n{self.text}"
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["target_unit_id"] = self.target_unit_id
        return d


def parse_amending_document(
    text: str,
    source_doc: str,
    target_doc: str,
    effective_date: str = "",
) -> list[Amendment]:
    """Bóc một nghị định sửa đổi thành danh sách Amendment.

    Điều nào không trỏ tới điều nào của văn bản gốc (vd. "Điều khoản thi hành",
    "Điều khoản chuyển tiếp") thì bỏ qua — đúng như mong muốn.
    """
    heads = list(_ART_HEAD.finditer(text))
    out: list[Amendment] = []
    for i, m in enumerate(heads):
        src_no, title = m.group(1), m.group(2).strip()
        body = text[m.end() : heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        low_title = title.lower()
        if not any(w in low_title for w in _OP_WORDS):
            continue  # điều thi hành / chuyển tiếp -> không phải sửa đổi

        targets: list[str] = []
        in_title = _DIEU_REF.findall(title)
        if in_title:
            targets = [in_title[-1]]          # tiêu đề: lấy "Điều N" cuối cùng
        else:
            # Kiểu Điều 19: mục tiêu nằm rải trong thân. Bỏ ngoặc kép trước.
            targets = sorted(
                set(_DIEU_REF.findall(_strip_quoted(body))),
                key=lambda x: int(re.sub(r"\D", "", x) or 0),
            )

        full = (title + "\n" + body).strip()
        for t in targets:
            out.append(
                Amendment(
                    source_doc=source_doc,
                    source_dieu=src_no,
                    target_doc=target_doc,
                    target_dieu=t,
                    title=title,
                    text=re.sub(r"\n{3,}", "\n\n", full).strip(),
                    effective_date=effective_date,
                    khoan=sorted(set(_KHOAN.findall(title)), key=lambda x: (len(x), x)),
                    diem=sorted(set(_DIEM.findall(title))),
                )
            )
    return out


@dataclass
class AmendmentIndex:
    """Tra nhanh: điều nào của văn bản gốc đang bị sửa bởi những gì."""

    by_target: dict[str, list[Amendment]] = field(default_factory=dict)

    @classmethod
    def from_amendments(cls, amendments: list[Amendment]) -> "AmendmentIndex":
        idx: dict[str, list[Amendment]] = {}
        for a in amendments:
            idx.setdefault(a.target_unit_id, []).append(a)
        return cls(idx)

    def for_unit(self, unit_id: str, as_of: str | None = None) -> list[Amendment]:
        """Các sửa đổi áp dụng cho một điều.

        as_of: ngày dạng 'YYYY-MM-DD'. Chỉ trả về sửa đổi ĐÃ có hiệu lực tính
        đến ngày đó. Truyền None = lấy tất cả (dùng cho nhánh corpus "mới").
        Đây là công tắc để chạy đối chứng độ trễ pháp lý (ADR-008).
        """
        items = self.by_target.get(unit_id, [])
        if as_of is None:
            return items
        return [a for a in items if not a.effective_date or a.effective_date <= as_of]

    def affected_units(self) -> list[str]:
        return sorted(self.by_target)

    def stats(self) -> dict:
        return {
            "n_amendments": sum(len(v) for v in self.by_target.values()),
            "n_affected_dieu": len(self.by_target),
            "affected_dieu": [k.split("dieu-")[-1] for k in sorted(self.by_target)],
        }

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        rows = [a.to_dict() for v in self.by_target.values() for a in v]
        p.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8"
        )


def augment_context(
    unit_ids: list[str],
    unit_text: dict[str, str],
    index: AmendmentIndex,
    as_of: str | None = None,
    max_chars: int = 6000,
) -> str:
    """Dựng ngữ cảnh cho mô hình: điều gốc + phần sửa đổi đang có hiệu lực.

    Phần sửa đổi đặt NGAY SAU điều gốc và ghi rõ nhãn, để mô hình thấy quan hệ
    và trích dẫn được cả hai. Đặt ở cuối ngữ cảnh thì mô hình hay bỏ sót.
    """
    parts: list[str] = []
    total = 0
    for uid in unit_ids:
        base = unit_text.get(uid, "")
        if not base:
            continue
        block = [base]
        for a in index.for_unit(uid, as_of=as_of):
            block.append(a.render())
        chunk = "\n\n".join(block)
        if total + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n\n---\n\n".join(parts)
