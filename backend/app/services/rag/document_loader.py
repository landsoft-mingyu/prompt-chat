"""RAG JSON 파일 → Document 변환 로더."""

import json
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid5

from app.schemas.document import Document, IndexStatus, SourceType
from app.services.rag.preprocessor import clean_content

# 원본 테이블명 → SourceType 매핑
_SOURCE_TYPE_MAP: dict[str, SourceType] = {
    "cms_menu_contents": SourceType.PAGE_CONTENT,
    "cms_board": SourceType.NOTICE,
    "ry_info_loca": SourceType.LOCATION,
}

# UUID5 네임스페이스 (프로젝트 고정값)
_UUID_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # NAMESPACE_DNS


def _make_source_id(source_table: str, original_id: str) -> UUID:
    """원본 테이블명 + 원본 PK → 결정론적 UUID5."""
    return uuid5(_UUID_NAMESPACE, f"{source_table}:{original_id}")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _extract_title(record: dict) -> str:
    meta = record.get("metadata", {})
    return (
        meta.get("title")
        or meta.get("menu_name")
        or meta.get("menu_path", "").split(">")[-1]
        or "제목 없음"
    )


def _extract_created_at(record: dict) -> datetime | None:
    meta = record.get("metadata", {})
    return _parse_dt(meta.get("regdt") or meta.get("last_updated"))


def load_documents_from_file(json_path: Path) -> list[Document]:
    """JSON 파일 1개를 읽어 Document 리스트로 변환."""
    with open(json_path, encoding="utf-8") as f:
        records: list[dict] = json.load(f)

    documents: list[Document] = []
    for record in records:
        original_id: str = record["id"]
        source_table: str = record["source_table"]
        source_type = _SOURCE_TYPE_MAP.get(source_table)

        if source_type is None:
            continue

        raw_content: str = record.get("content") or ""
        cleaned = clean_content(raw_content)
        if not cleaned:
            continue

        meta: dict = record.get("metadata", {})
        site_code: str = meta.get("site_code") or "ROYAL"

        doc = Document(
            source_id=_make_source_id(source_table, original_id),
            source_type=source_type,
            source_table=source_table,
            site_code=site_code,
            title=_extract_title(record),
            content=cleaned,
            created_at=_extract_created_at(record),
            metadata={
                "original_id": original_id,
                **meta,
            },
            index_status=IndexStatus.PENDING,
        )
        documents.append(doc)

    return documents


def load_all_documents(rag_dir: Path) -> list[Document]:
    """rag/ 폴더 내 모든 JSON 파일을 읽어 Document 리스트로 반환."""
    all_docs: list[Document] = []
    for json_file in sorted(rag_dir.glob("*.json")):
        docs = load_documents_from_file(json_file)
        all_docs.extend(docs)
    return all_docs
