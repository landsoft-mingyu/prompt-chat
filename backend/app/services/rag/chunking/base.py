"""청킹 공통 모델 및 베이스 파서."""

from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256

from pydantic import BaseModel, Field

from app.services.rag.chunking.html_layout import Block, HtmlLayoutParser

# 청크 크기 기준 (글자 수) — 의미 분리 우선, 길이는 보조
TARGET_LEN = 1000
MAX_TEXT_LEN = 1500
# 이 길이 미만이면 헤더가 바뀌어도 인접 블록과 계속 병합 (과분할 방지)
MIN_MERGE_LEN = 200


def _common_prefix(paths: list[list[str]]) -> list[str]:
    """여러 header_path의 공통 상위 경로."""
    if not paths:
        return []
    cp = paths[0]
    for p in paths[1:]:
        i = 0
        while i < len(cp) and i < len(p) and cp[i] == p[i]:
            i += 1
        cp = cp[:i]
    return cp


class Chunk(BaseModel):
    """Milvus `site_chunks` 적재 단위 (분석 문서 6장)."""

    chunk_id: str
    parent_id: str
    site_code: str
    source_table: str
    source_id: str
    source_type: str
    content_type: str
    bc_id: str | None = None
    menu_code: str | None = None
    menu_path: str | None = None
    group_code: str | None = None
    title: str | None = None
    section_title: str | None = None
    header_path: str | None = None
    is_table: bool = False
    html_yn: str | None = None
    chunk_text: str
    text_hash: str = ""
    regdt: str | None = None
    upddt: str | None = None
    metadata: dict = Field(default_factory=dict)


def text_hash(s: str) -> str:
    return sha256(s.encode("utf-8")).hexdigest()


def make_parent_id(site_code: str, source_table: str, source_id: str) -> str:
    return f"{site_code}:{source_table}:{source_id}"


def make_chunk_id(parent_id: str, index: int) -> str:
    return f"{parent_id}:{index:04d}"


def build_chunk_text(*, body: str, **_ignored) -> str:
    """임베딩용 텍스트 = 순수 본문.

    site_code/menu_path/title/section_title/header_path는 모두 별도 scalar
    필드로 보존되므로(필터·재랭킹용) chunk_text에 중복 주입하지 않는다.
    """
    return body.strip()


class BaseChunkParser(ABC):
    """테이블별 파서의 공통 베이스."""

    source_type: str = "generic"

    def __init__(self) -> None:
        self.layout = HtmlLayoutParser()

    @abstractmethod
    def parse(self, record: dict) -> list[Chunk]:
        """보강된 소스 레코드 1건 → Chunk 리스트."""
        ...

    # ── 공통 헬퍼 ────────────────────────────────
    def _emit(
        self,
        *,
        record: dict,
        index: int,
        body: str,
        content_type: str,
        section_title: str | None = None,
        header_path: list[str] | None = None,
        is_table: bool = False,
        extra_meta: dict | None = None,
    ) -> Chunk:
        site = record.get("site_code", "ROYAL")
        table = record["source_table"]
        source_id = record["source_id"]
        meta = record.get("metadata", {})
        db = record.get("db", {})
        parent_id = make_parent_id(site, table, source_id)
        # 탭 분할분은 source_id에 탭키 포함
        if record.get("tab_key"):
            parent_id = make_parent_id(site, table, f"{source_id}_{record['tab_key']}")
        title = meta.get("title")
        menu_path = meta.get("menu_path")
        chunk_text = build_chunk_text(
            site_code=site,
            menu_path=menu_path,
            title=title,
            section_title=section_title,
            body=body,
        )
        hp = " > ".join(header_path) if header_path else None
        return Chunk(
            chunk_id=make_chunk_id(parent_id, index),
            parent_id=parent_id,
            site_code=site,
            source_table=table,
            source_id=source_id
            if not record.get("tab_key")
            else f"{source_id}_{record['tab_key']}",
            source_type=self.source_type,
            content_type=content_type,
            bc_id=db.get("bc_id"),
            menu_code=meta.get("menu_code") or db.get("menu_code"),
            menu_path=menu_path,
            group_code=db.get("group_code"),
            title=title,
            section_title=section_title,
            header_path=hp,
            is_table=is_table,
            html_yn=db.get("bd_htmlyn"),
            chunk_text=chunk_text,
            text_hash=text_hash(chunk_text),
            regdt=meta.get("regdt") or (db.get("regdt") if db else None),
            upddt=meta.get("upddt") or (db.get("upddt") if db else None),
            metadata=extra_meta or {},
        )

    def _group_blocks(self, blocks: list[Block]) -> list[Block]:
        """연속 text/list 블록을 의미 단위로 병합. 표는 단독 유지.

        - 헤더가 바뀌면 분리하되, 누적 버퍼가 MIN_MERGE_LEN 미만이면 계속 병합
          (시작하는 곳/소요시간/문의 같은 짧은 항목을 한 chunk로 묶음).
        - 병합 chunk의 header_path는 구성 블록들의 공통 상위 경로.
        """
        merged: list[Block] = []
        buf: list[str] = []
        buf_paths: list[list[str]] = []

        def cur_len() -> int:
            return sum(len(x) for x in buf) + 2 * max(0, len(buf) - 1)

        def flush() -> None:
            if buf:
                merged.append(
                    Block("text", "\n\n".join(buf), _common_prefix(buf_paths))
                )
                buf.clear()
                buf_paths.clear()

        for b in blocks:
            if b.is_table:
                flush()
                merged.append(b)
                continue
            if buf and cur_len() >= MIN_MERGE_LEN:
                header_changed = b.header_path != buf_paths[-1]
                # 버퍼가 이미 충분할 때만 분리 (작은 라벨/제목은 다음 블록과 병합)
                if header_changed or cur_len() + len(b.text) > TARGET_LEN:
                    flush()
            buf.append(b.text)
            buf_paths.append(b.header_path)
        flush()
        return merged
