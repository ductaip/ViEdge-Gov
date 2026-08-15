"""
Bóc tách văn bản pháp luật thành đơn vị điều / khoản / điểm.

Vì sao không cắt chunk theo số token như RAG thông thường: văn bản quy phạm
có cấu trúc phân cấp mang nghĩa. "Khoản 3 Điều 22" là một địa chỉ pháp lý,
không phải một đoạn văn tuỳ ý. Cắt theo token làm mất địa chỉ đó, và mất
luôn khả năng sinh trích dẫn kiểm chứng được — tức là mất luôn cơ chế chống
lỗi E3. Đây là quyết định thiết kế phải giải thích được trước hội đồng.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

DIEU_HEAD = re.compile(r"^\s*Điều\s+(\d+[a-zA-Z]?)\s*[.．:]?\s*(.*)$", re.MULTILINE)
KHOAN_HEAD = re.compile(r"^\s*(\d+)\s*[.．)]\s+(.*)$")
DIEM_HEAD = re.compile(r"^\s*([a-zđ])\s*[.．)]\s+(.*)$")
BIENBAO_IN_TEXT = re.compile(r"\b([PBWRISDE])\.(\d{1,3}[a-z]?)\b")


@dataclass
class Diem:
    diem: str
    text: str


@dataclass
class Khoan:
    khoan: str
    text: str
    diem: list[Diem] = field(default_factory=list)


@dataclass
class Article:
    """Một điều luật — đơn vị truy hồi cơ bản."""

    doc_id: str
    dieu: str
    title: str
    text: str
    khoan: list[Khoan] = field(default_factory=list)
    bienbao: list[str] = field(default_factory=list)

    @property
    def unit_id(self) -> str:
        return f"{self.doc_id}::dieu-{self.dieu}"

    def retrieval_text(self) -> str:
        """Văn bản đưa vào index — gồm tiêu đề để tăng tín hiệu từ khoá."""
        return f"{self.doc_id} — Điều {self.dieu}. {self.title}\n{self.text}".strip()

    def khoan_units(self) -> list[tuple[str, str]]:
        """Tách điều thành đơn vị cấp KHOẢN. Trả về [(unit_id, text)].

        Mỗi khoản mang theo header của điều, vì hai lý do:
          - giữ ĐỊA CHỈ PHÁP LÝ đầy đủ: "Điều 6 khoản 3" vẫn trích dẫn được,
            không vi phạm nguyên tắc ở ADR-006 (khoản cũng là địa chỉ hợp lệ)
          - giữ tín hiệu từ khoá của tiêu đề điều cho BM25, nếu không thì
            khoản rời rạc mất ngữ cảnh "xe ô tô" / "xe mô tô" và truy hồi sai
        """
        head = f"{self.doc_id} — Điều {self.dieu}. {self.title}"
        out: list[tuple[str, str]] = []
        for k in self.khoan:
            body = k.text
            if k.diem:
                body += " " + " ".join(f"{d.diem}) {d.text}" for d in k.diem)
            out.append((f"{self.unit_id}::khoan-{k.khoan}",
                        f"{head}\nKhoản {k.khoan}. {body}".strip()))
        return out

    def to_dict(self) -> dict:
        d = asdict(self)
        d["unit_id"] = self.unit_id
        return d


def _parse_body(body: str) -> tuple[list[Khoan], str]:
    """Tách phần thân một điều thành các khoản, mỗi khoản có thể có điểm."""
    khoans: list[Khoan] = []
    preamble: list[str] = []
    current: Khoan | None = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m_k = KHOAN_HEAD.match(line)
        if m_k:
            current = Khoan(khoan=m_k.group(1), text=m_k.group(2).strip())
            khoans.append(current)
            continue
        m_d = DIEM_HEAD.match(line)
        if m_d and current is not None:
            current.diem.append(Diem(diem=m_d.group(1), text=m_d.group(2).strip()))
            continue
        if current is None:
            preamble.append(line)
        elif current.diem:
            current.diem[-1].text += " " + line
        else:
            current.text += " " + line
    return khoans, " ".join(preamble)


def parse_document(text: str, doc_id: str) -> list[Article]:
    """Bóc một văn bản (đã ở dạng text thuần) thành danh sách điều."""
    heads = list(DIEU_HEAD.finditer(text))
    articles: list[Article] = []
    for i, m in enumerate(heads):
        start = m.end()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[start:end]
        khoans, preamble = _parse_body(body)
        full = (preamble + " " + body).strip()
        articles.append(
            Article(
                doc_id=doc_id,
                dieu=m.group(1),
                title=m.group(2).strip(),
                text=re.sub(r"\s+", " ", full),
                khoan=khoans,
                bienbao=sorted({f"{a}.{b}" for a, b in BIENBAO_IN_TEXT.findall(body)}),
            )
        )
    return articles


def save_articles(articles: list[Article], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for a in articles:
            f.write(json.dumps(a.to_dict(), ensure_ascii=False) + "\n")


def load_articles(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


TTHC_MARKER = "Mã thủ tục"


@dataclass
class Procedure:
    """Một thủ tục hành chính — đơn vị truy hồi cho corpus TTHC.

    Khác Article: TTHC không có 'Điều N' nên parse_document() luôn trả về
    rỗng cho loại văn bản này (đã kiểm thật — 0 điều trên file chép từ
    dichvucong.gov.vn). Tách theo tiêu đề thủ tục + dòng 'Mã thủ tục',
    đúng định dạng khi copy nguyên khối từ cổng dịch vụ công.
    """

    doc_id: str
    ma: str            # mã thủ tục, vd. "1.010910"
    ten: str           # tên đầy đủ của thủ tục
    text: str          # toàn bộ nội dung: lĩnh vực, cơ quan, trình tự, hồ sơ...

    @property
    def unit_id(self) -> str:
        return f"{self.doc_id}::tthc-{self.ma}"

    def retrieval_text(self) -> str:
        return f"{self.doc_id} — Thủ tục {self.ma}: {self.ten}\n{self.text}".strip()

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "ma": self.ma,
            "ten": self.ten,
            "title": self.ten,   # alias cho build_retrieval_units
            "text": self.text,
            "dieu": self.ma,     # alias cho CitationIndex.from_articles / corpus_stats
            "khoan": [],
            "bienbao": [],
            "unit_id": self.unit_id,
        }


def parse_tthc(text: str, doc_id: str) -> list[Procedure]:
    """Bóc văn bản TTHC thành danh sách thủ tục.

    Mỗi thủ tục: dòng tiêu đề ngay TRƯỚC 'Mã thủ tục', mã ngay SAU nó — đúng
    thứ tự khi copy nguyên khối một trang chi tiết thủ tục từ dichvucong.gov.vn.
    """
    lines = text.splitlines()
    marker_idx = [i for i, l in enumerate(lines) if l.strip() == TTHC_MARKER]
    procs: list[Procedure] = []
    for k, mi in enumerate(marker_idx):
        ten = lines[mi - 1].strip() if mi > 0 else ""
        ma = lines[mi + 1].strip() if mi + 1 < len(lines) else ""
        start = mi - 1 if mi > 0 else mi
        end = marker_idx[k + 1] - 1 if k + 1 < len(marker_idx) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        procs.append(Procedure(doc_id=doc_id, ma=ma, ten=ten, text=body))
    return procs


def article_of(unit_id: str) -> str:
    """Đưa unit_id cấp khoản về unit_id cấp điều.

    Gold trong ViGovQA-GT ghi ở cấp ĐIỀU, nên mọi phép chấm truy hồi phải
    quy về cấp điều trước khi so — nếu không, retrieve đúng khoản vẫn bị
    tính là trượt.
    """
    return unit_id.split("::khoan-")[0]


def build_retrieval_units(articles: list[dict], max_chars: int = 6000) -> dict[str, str]:
    """Đơn vị truy hồi hai cấp.

    Vì sao cần: NĐ 168 có điều dài tới 30.137 ký tự (Điều 32), median 2.109.
    Ngân sách ngữ cảnh 6.000 ký tự nhét vừa 2 điều nhỏ và KHÔNG BAO GIỜ vừa
    Điều 6 hay Điều 32 — tức là câu hỏi về mức phạt phổ biến nhất thì mô hình
    không hề nhìn thấy căn cứ. Lỗi này im lặng: pipeline vẫn chạy, vẫn trả lời,
    chỉ là trả lời không có căn cứ.

    Quy tắc: điều ngắn giữ nguyên một đơn vị; điều dài tách theo khoản.
    """
    units: dict[str, str] = {}
    for a in articles:
        art = Article(
            doc_id=a["doc_id"], dieu=a["dieu"], title=a.get("title", ""),
            text=a.get("text", ""),
            khoan=[Khoan(khoan=k["khoan"], text=k["text"],
                         diem=[Diem(**d) for d in k.get("diem", [])])
                   for k in a.get("khoan", [])],
            bienbao=a.get("bienbao", []),
        )
        if len(art.text) <= max_chars or not art.khoan:
            units[art.unit_id] = art.retrieval_text()
        else:
            for uid, txt in art.khoan_units():
                units[uid] = txt
    return units


def corpus_stats(articles: list[dict]) -> dict:
    """Số liệu cho Bảng 1 của quyển báo cáo (mô tả kho văn bản)."""
    n_khoan = sum(len(a.get("khoan", [])) for a in articles)
    n_diem = sum(len(k.get("diem", [])) for a in articles for k in a.get("khoan", []))
    signs = {c for a in articles for c in a.get("bienbao", [])}
    return {
        "n_docs": len({a["doc_id"] for a in articles}),
        "n_dieu": len(articles),
        "n_khoan": n_khoan,
        "n_diem": n_diem,
        "n_bienbao": len(signs),
        "avg_chars_per_dieu": (
            round(sum(len(a["text"]) for a in articles) / len(articles), 1) if articles else 0
        ),
    }
