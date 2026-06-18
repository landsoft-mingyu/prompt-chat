"""HtmlLayoutParser — 레이아웃 인지 HTML 청킹 엔진.

ROYAL CMS의 HTML은 시맨틱 헤딩(`<h1~h6>`)을 쓰지 않고 **CSS 클래스**로
헤더/뎁스를 인코딩한다(분석 문서 3.2절). 이 파서는 클래스→레벨 매핑으로
의미 위계를 복원하면서 HTML을 레이아웃 블록 리스트로 분해한다.

블록 종류:
- text   : 문단/일반 텍스트
- table  : `<table>` → Markdown 표
- list   : `<ul>/<ol>` → 항목 묶음

각 블록은 현재 헤더 경로(`header_path = [탭, L1, L2]`)를 함께 갖는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

# ──────────────────────────────────────────────
# 클래스 → 역할 매핑 (분석 문서 3.2절 실측 기반, 외부화 가능)
# ──────────────────────────────────────────────
L1_TITLE_CLASSES = {
    "txt_section_tit",
    "page_privacy_tit",
    "history_con_tit",
    "gallery_tit",
}
L2_TITLE_CLASSES = {
    "info_tit",
    "img_info_tit",
    "plan_list_tit",
    "tit",
}
DROP_CLASSES = {
    "sr_only",
    "hidden",
    "swiper-button-prev",
    "swiper-button-next",
    "swiper-pagination",
}
TAB_MENU_CLASS = "tab_menu"
TAB_CON_CLASS = "tab_con"
TAB_LINK_CLASS = "tab_link"
# 탭 네비게이션(클릭 라벨)만 본문에서 제외. tab_menu 컨테이너는 콘텐츠를
# 함께 품기도 하므로 통째로 skip하지 않는다.
NAV_CLASSES = {"tab_link", "swiper-wrapper"}

_WS = re.compile(r"[ \t ]+")
_MULTINL = re.compile(r"\n{3,}")


@dataclass
class Block:
    """레이아웃 블록."""

    kind: str  # 'text' | 'table' | 'list'
    text: str
    header_path: list[str] = field(default_factory=list)

    @property
    def is_table(self) -> bool:
        return self.kind == "table"

    @property
    def section_title(self) -> str | None:
        return self.header_path[-1] if self.header_path else None


def _classes(tag: Tag) -> set[str]:
    c = tag.get("class")
    if not c:
        return set()
    return set(c) if isinstance(c, list) else set(str(c).split())


def _norm_text(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _WS.sub(" ", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    s = _MULTINL.sub("\n\n", s)
    return s.strip()


# 본문 내 장식 머리표(시맨틱 제목 클래스가 아닌, 굵은 ▷/◇ 등으로 표기된 섹션 제목)
_HEADING_MARKERS = "▷▶◇◆○●■□♦◈"


def _marker_heading(txt: str) -> str | None:
    """'▷ 건원릉 이야기'처럼 머리표로 시작하는 짧은 줄 → 섹션 제목(머리표 제거)."""
    t = txt.strip()
    if 0 < len(t) <= 50 and t[0] in _HEADING_MARKERS and "\n" not in t:
        return t.lstrip(_HEADING_MARKERS).strip()
    return None


class HtmlLayoutParser:
    """HTML → Block 리스트."""

    def __init__(
        self,
        l1_classes: set[str] | None = None,
        l2_classes: set[str] | None = None,
        drop_classes: set[str] | None = None,
    ):
        self.l1 = l1_classes or L1_TITLE_CLASSES
        self.l2 = l2_classes or L2_TITLE_CLASSES
        self.drop = drop_classes or DROP_CLASSES

    # ── public ──────────────────────────────────
    def parse(self, html: str) -> list[Block]:
        soup = BeautifulSoup(html or "", "lxml")
        self._strip_noise(soup)
        return self._parse_node(soup, soup.body or soup)

    def parse_tab(self, html: str, tab_label: str) -> list[Block]:
        """특정 탭(라벨)에 해당하는 tab_con 서브트리만 파싱.

        탭이 중첩된 문서(_tNN 분할분)에서 해당 페이지 콘텐츠만 정확히 추출.
        라벨에 맞는 탭을 못 찾으면 전체 파싱으로 fallback.
        """
        soup = BeautifulSoup(html or "", "lxml")
        self._strip_noise(soup)
        con = self._find_tab_con(soup, tab_label)
        if con is None:
            return self.parse(html)
        return self._parse_node(soup, con)

    def _parse_node(self, soup: BeautifulSoup, root: Tag) -> list[Block]:
        tab_labels = self._tab_label_map(soup)
        blocks: list[Block] = []
        stack: dict[int, str] = {}  # level(0=탭,1=L1,2=L2) → 제목
        self._walk(root, blocks, stack, tab_labels)
        return [b for b in blocks if b.text.strip()]

    def _find_tab_con(self, soup: BeautifulSoup, label: str):
        """탭 라벨 → 해당 tab_con 요소. data-tab(속성) 또는 class 토큰으로 연결."""
        data_tab = None
        for link in soup.find_all(
            lambda t: isinstance(t, Tag) and TAB_LINK_CLASS in _classes(t)
        ):
            if _norm_text(link.get_text()) == label:
                data_tab = link.get("data-tab")
                break
        if not data_tab:
            return None
        return soup.find(
            lambda t: (
                isinstance(t, Tag)
                and TAB_CON_CLASS in _classes(t)
                and (t.get("data-tab") == data_tab or data_tab in _classes(t))
            )
        )

    # ── cleaning ────────────────────────────────
    def _strip_noise(self, soup: BeautifulSoup) -> None:
        for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
            c.extract()
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        # <img> → alt 텍스트 보존 후 제거
        for img in soup.find_all("img"):
            alt = (img.get("alt") or "").strip()
            img.replace_with(alt) if alt else img.decompose()
        # 드롭 클래스 요소 제거 (접근성/장식).
        # 단, 표 내부 sr_only는 셀의 실제 데이터(예: 시간표의 해설자명)를
        # 담는 경우가 있어 보존한다.
        for tag in soup.find_all(True):
            if isinstance(tag, Tag) and _classes(tag) & self.drop:
                if tag.find_parent("table") is not None:
                    continue
                tag.decompose()

    # ── tab labels ──────────────────────────────
    def _tab_label_map(self, root: Tag) -> dict[str, str]:
        labels: dict[str, str] = {}
        for link in root.find_all(
            lambda t: isinstance(t, Tag) and TAB_LINK_CLASS in _classes(t)
        ):
            dt = link.get("data-tab")
            if dt:
                labels[dt] = _norm_text(link.get_text())
        return labels

    # ── recursive walk ──────────────────────────
    def _title_level(self, tag: Tag) -> int | None:
        cls = _classes(tag)
        if cls & self.l1:
            return 1
        if cls & self.l2:
            return 2
        return None

    def _set_header(self, stack: dict[int, str], level: int, text: str) -> None:
        stack[level] = text
        for deeper in [k for k in stack if k > level]:
            del stack[deeper]

    def _header_path(self, stack: dict[int, str]) -> list[str]:
        return [stack[k] for k in sorted(stack) if stack[k]]

    def _walk(
        self,
        node: Tag,
        blocks: list[Block],
        stack: dict[int, str],
        tab_labels: dict[str, str],
    ) -> None:
        for child in node.children:
            # 태그로 감싸지 않은 맨 텍스트(컨테이너 직속 text node)도 본문이다.
            if isinstance(child, NavigableString):
                if isinstance(child, Comment):
                    continue
                self._push_text(_norm_text(str(child)), blocks, stack)
                continue
            if not isinstance(child, Tag):
                continue
            cls = _classes(child)
            name = child.name.lower()

            # 탭 네비게이션 라벨/슬라이더는 본문 아님 → skip
            if cls & NAV_CLASSES:
                continue

            # 탭 콘텐츠 → 탭 라벨을 level 0 헤더로
            # 탭 id는 data-tab 속성 또는 class 토큰(tab01 등)으로 식별
            if TAB_CON_CLASS in cls:
                dt = child.get("data-tab")
                tab_id = (
                    dt
                    if dt in tab_labels
                    else next((c for c in cls if c in tab_labels), None)
                )
                if tab_id:
                    self._set_header(stack, 0, tab_labels[tab_id])
                self._walk(child, blocks, stack, tab_labels)
                continue

            # 제목 요소 → 헤더 스택 갱신 (본문으로 emit 안 함)
            lvl = self._title_level(child)
            if lvl is not None:
                title = _norm_text(child.get_text())
                if title:
                    self._set_header(stack, lvl, title)
                continue

            # 표
            if name == "table":
                md = _table_to_markdown(child)
                if md:
                    blocks.append(Block("table", md, self._header_path(stack)))
                continue

            # 목록
            if name in ("ul", "ol"):
                txt = _list_to_text(child)
                if txt:
                    blocks.append(Block("list", txt, self._header_path(stack)))
                continue

            # 표/목록/제목/탭을 자식으로 가진 컨테이너 → 재귀
            if child.find(["table", "ul", "ol"]) or self._has_title_descendant(child):
                self._walk(child, blocks, stack, tab_labels)
                continue

            # 말단 텍스트 블록
            self._push_text(_norm_text(child.get_text()), blocks, stack)

    def _push_text(self, txt: str, blocks: list[Block], stack: dict[int, str]) -> None:
        """텍스트 블록 추가. 단, ▷/◇ 머리표 줄은 섹션 헤더로 승격(본문 emit 안 함)."""
        if not txt:
            return
        heading = _marker_heading(txt)
        if heading:
            self._set_header(stack, 1, heading)
            return
        blocks.append(Block("text", txt, self._header_path(stack)))

    def _has_title_descendant(self, tag: Tag) -> bool:
        for d in tag.find_all(True):
            if isinstance(d, Tag) and (
                self._title_level(d) is not None or TAB_CON_CLASS in _classes(d)
            ):
                return True
        return False


# ──────────────────────────────────────────────
# 표 / 목록 변환
# ──────────────────────────────────────────────
def _table_to_markdown(table: Tag) -> str:
    # <caption> (표 설명/제목)은 행이 아니어서 별도 보존
    cap_tag = table.find("caption")
    caption = _norm_text(cap_tag.get_text(" ")) if cap_tag else ""
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        # 표 셀은 다중 값(시간/항목)이 span으로 나열되므로 공백 구분자로 분리
        cells = [_norm_text(td.get_text(" ")) for td in tr.find_all(["th", "td"])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return caption  # 행은 없고 캡션만 있는 경우라도 내용 보존
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    table_md = "\n".join(lines)
    return f"{caption}\n{table_md}" if caption else table_md


def _list_to_text(lst: Tag) -> str:
    items = []
    for li in lst.find_all("li", recursive=False):
        t = _norm_text(li.get_text())
        if t:
            items.append(f"- {t}")
    if not items:  # 중첩 등으로 직속 li가 없으면 전체 텍스트
        return _norm_text(lst.get_text())
    return "\n".join(items)
