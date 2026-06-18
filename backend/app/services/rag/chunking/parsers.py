"""테이블별 청킹 파서.

- CmsBoardChunkParser       : 게시판(스토리) — 평탄 산문 HTML
- CmsMenuContentsChunkParser: 메뉴 본문 — 탭/섹션/표 레이아웃
- RyInfoLocaChunkParser     : 위치/교통 — 평문 + 컬럼 메타
"""

from __future__ import annotations

import re

from app.services.rag.chunking.base import BaseChunkParser, Chunk
from app.services.rag.chunking.content_type import (
    classify_board,
    classify_menu,
    classify_ry,
)
from app.services.rag.chunking.html_layout import Block


def _leaf(menu_path: str | None) -> str:
    segs = [s for s in (menu_path or "").split(">") if s]
    return segs[-1] if segs else ""


# ──────────────────────────────────────────────
# cms_board
# ──────────────────────────────────────────────
class CmsBoardChunkParser(BaseChunkParser):
    """게시판(스토리). 전부 HTML(평탄 산문), 위계 거의 없음."""

    source_type = "article"

    def parse(self, record: dict) -> list[Chunk]:
        if record.get("_missing"):
            return []
        html = record.get("content_html") or ""
        blocks = self.layout.parse(html) if html.strip() else []
        if not blocks and (record.get("content_text") or "").strip():
            blocks = [Block("text", record["content_text"], [])]

        content_type = classify_board(record.get("db", {}).get("bc_id"))
        return self._emit_blocks(record, self._group_blocks(blocks), content_type)

    def _emit_blocks(self, record, blocks, content_type) -> list[Chunk]:
        chunks = []
        for i, b in enumerate(blocks, start=1):
            chunks.append(
                self._emit(
                    record=record,
                    index=i,
                    body=b.text,
                    content_type=content_type,
                    section_title=b.section_title,
                    header_path=b.header_path,
                    is_table=b.is_table,
                )
            )
        return chunks


# ──────────────────────────────────────────────
# cms_menu_contents
# ──────────────────────────────────────────────
class CmsMenuContentsChunkParser(BaseChunkParser):
    """메뉴 본문. 탭→섹션→표 레이아웃 분리."""

    source_type = "menu_page"

    def parse(self, record: dict) -> list[Chunk]:
        if record.get("_missing"):
            return []
        html = record.get("content_html") or ""

        tab_key = record.get("tab_key")
        if tab_key and html.strip():
            # 탭 분할분: 해당 탭(라벨=menu_path leaf)의 tab_con 서브트리만 파싱
            leaf = record.get("tab_label") or _leaf(record["metadata"].get("menu_path"))
            blocks = self.layout.parse_tab(html, leaf)
        else:
            blocks = self.layout.parse(html) if html.strip() else []

        if not blocks and (record.get("content_text") or "").strip():
            blocks = [Block("text", record["content_text"], [])]

        menu_path = record["metadata"].get("menu_path")
        chunks = []
        for i, b in enumerate(self._group_blocks(blocks), start=1):
            chunks.append(
                self._emit(
                    record=record,
                    index=i,
                    body=b.text,
                    content_type=classify_menu(menu_path, is_table=b.is_table),
                    section_title=b.section_title,
                    header_path=b.header_path,
                    is_table=b.is_table,
                )
            )
        return chunks


# ──────────────────────────────────────────────
# ry_info_loca
# ──────────────────────────────────────────────
_RY_LABELS = ("지하철", "버스", "도보", "자가용", "내비게이션", "주차", "주차장")
_LABEL_LINE = re.compile(
    r"^\s*(지하철|버스|도보|자가용|내비게이션|주차장\s*안내|주차)\b"
)


class RyInfoLocaChunkParser(BaseChunkParser):
    """위치/교통. 컬럼 메타로 개요 chunk 합성 + 본문 교통/주차 분리."""

    source_type = "location"

    def parse(self, record: dict) -> list[Chunk]:
        if record.get("_missing"):
            return []
        db = record.get("db", {})
        meta = record["metadata"]
        chunks: list[Chunk] = []
        idx = 1

        # 1) 위치 개요 chunk (항상 생성) — 컬럼 메타 합성
        overview = self._overview_body(db, meta)
        chunks.append(
            self._emit(
                record=record,
                index=idx,
                body=overview,
                content_type=classify_ry("__overview__"),
                section_title="위치 개요",
                extra_meta=self._loc_meta(db, meta),
            )
        )
        idx += 1

        # 2) 본문 교통/주차 섹션 분리
        for label, body in self._split_sections(record.get("content_text") or ""):
            chunks.append(
                self._emit(
                    record=record,
                    index=idx,
                    body=body,
                    content_type=classify_ry(label),
                    section_title=label,
                    extra_meta=self._loc_meta(db, meta),
                )
            )
            idx += 1
        return chunks

    def _overview_body(self, db: dict, meta: dict) -> str:
        title = db.get("title") or meta.get("title") or ""
        addr = db.get("addrs") or meta.get("address") or ""
        tel = db.get("tel_no") or meta.get("tel") or ""
        url = db.get("loca_url") or ""
        parts = [f"{title} 위치 안내"]
        if addr:
            parts.append(f"주소: {addr}")
        if tel:
            parts.append(f"문의: {tel}")
        if url:
            parts.append(f"지도: {url}")
        return "\n".join(parts)

    def _loc_meta(self, db: dict, meta: dict) -> dict:
        return {
            "address": db.get("addrs") or meta.get("address"),
            "tel": db.get("tel_no") or meta.get("tel"),
            "tel_fax": db.get("tel_fax"),
            "loca_url": db.get("loca_url"),
            "latitude": meta.get("latitude"),
            "longitude": meta.get("longitude"),
        }

    def _split_sections(self, content: str) -> list[tuple[str, str]]:
        """라벨 라인 기준으로 교통/주차 버킷 분리. 라벨 없으면 통짜 1개."""
        if not content.strip():
            return []
        lines = content.split("\n")
        buckets: list[tuple[str, list[str]]] = []
        cur_label = "교통"
        cur: list[str] = []
        for line in lines:
            m = _LABEL_LINE.match(line)
            if m:
                label = m.group(1).replace(" ", "")
                # 주차/자가용/내비 → 자가용, 그 외 → 교통
                bucket = (
                    "자가용"
                    if label in ("자가용", "내비게이션", "주차", "주차장안내")
                    else "지하철"
                )
                if bucket != cur_label and cur:
                    buckets.append((cur_label, cur))
                    cur = []
                cur_label = bucket
            cur.append(line)
        if cur:
            buckets.append((cur_label, cur))
        out: list[tuple[str, str]] = []
        for label, ls in buckets:
            body = "\n".join(s for s in ls if s.strip()).strip()
            if not body:
                continue
            # 너무 짧은 섹션(제목/라벨 조각)은 이전 섹션에 흡수, 없으면 다음으로 이월
            if len(body) < 15 and out:
                plabel, pbody = out[-1]
                out[-1] = (plabel, f"{pbody}\n{body}")
            else:
                out.append((label, body))
        # 선행 tiny 섹션은 다음 섹션에 흡수
        if len(out) >= 2 and len(out[0][1]) < 15:
            out[1] = (out[1][0], f"{out[0][1]}\n{out[1][1]}")
            out = out[1:]
        return out
