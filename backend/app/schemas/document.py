"""RAG 파이프라인 공통 스키마."""

from datetime import UTC, datetime
from enum import StrEnum
from hashlib import md5
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ──────────────────────────────────────────────
# Enum 정의
# ──────────────────────────────────────────────


class SourceType(StrEnum):
    """출처 타입."""

    NOTICE = "notice"  # cms_board
    PAGE_CONTENT = "page_content"  # cms_menu_contents
    CULTURAL_EVENT = "cultural_event"  # ry_cultural_event
    EXHIBITION = "exhibition"  # ry_exhibition
    VIEW_COURSE = "view_course"  # ry_view_course
    LOCATION = "location"  # ry_info_loca
    FAQ = "faq"  # tcb_entity


class IndexStatus(StrEnum):
    """색인 상태."""

    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


# ──────────────────────────────────────────────
# 상수 및 매핑
# ──────────────────────────────────────────────

VALID_SOURCE_TYPES: frozenset[str] = frozenset(st.value for st in SourceType)

SOURCE_TYPE_LABEL: dict[str, str] = {
    SourceType.NOTICE.value: "공지/게시물",
    SourceType.PAGE_CONTENT.value: "메뉴 페이지",
    SourceType.CULTURAL_EVENT.value: "문화행사",
    SourceType.EXHIBITION.value: "전시",
    SourceType.VIEW_COURSE.value: "관람코스",
    SourceType.LOCATION.value: "위치/연락처",
    SourceType.FAQ.value: "FAQ",
}


# ──────────────────────────────────────────────
# Mixin 클래스
# ──────────────────────────────────────────────


class ContentHashMixin(BaseModel):
    """content_hash 자동 생성 Mixin."""

    content: str = Field(
        min_length=1,
        description="임베딩 대상 텍스트",
    )
    content_hash: str | None = Field(
        default=None,
        description="MD5 기반 변경 감지용 해시",
    )

    @model_validator(mode="after")
    def set_content_hash(self) -> "ContentHashMixin":
        """content 기반 MD5 해시 자동 생성."""
        if self.content_hash is None:
            self.content_hash = md5(self.content.encode("utf-8")).hexdigest()
        return self


# ──────────────────────────────────────────────
# Document 클래스
# ──────────────────────────────────────────────


class Document(ContentHashMixin):
    """
    RAG 파이프라인 공통 문서 스키마.

    원본 DB 데이터를 RAG 색인용 형태로 정규화한 단위다.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "source_id": "550e8400-e29b-41d4-a716-446655440000",
                    "source_type": "notice",
                    "source_table": "cms_board",
                    "site_code": "ROYAL",
                    "title": "경복궁 관람 안내",
                    "content": "관람 시간은 오전 9시부터 오후 6시까지입니다.",
                    "created_at": "2026-06-15T10:30:00",
                    "url": "https://royal.go.kr/notice/1",
                    "index_status": "pending",
                }
            ]
        },
    )

    source_id: Annotated[
        UUID, Field(description="원본 테이블 PK (id 예약어 충돌 방지)")
    ]
    source_type: SourceType = Field(description="출처 타입")
    source_table: str = Field(description="원본 테이블명")
    site_code: str = Field(description="사이트 구분 코드")
    title: str = Field(
        min_length=1,
        description="검색/표시용 제목",
    )
    created_at: datetime | None = Field(
        default=None,
        description="원본 등록일",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="부가정보",
    )
    url: str | None = Field(
        default=None,
        description="원본 링크",
    )
    index_status: IndexStatus = Field(
        default=IndexStatus.PENDING,
        description="색인 상태",
    )


# ──────────────────────────────────────────────
# Chunk 클래스
# ──────────────────────────────────────────────


class Chunk(ContentHashMixin):
    """
    RAG 임베딩 대상 텍스트 조각.

    Document를 분할하여 벡터 DB에 저장하는 단위다.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "chunk_id": "550e8400-e29b-41d4-a716-446655440001",
                    "source_id": "550e8400-e29b-41d4-a716-446655440000",
                    "source_table": "cms_board",
                    "source_type": "notice",
                    "site_code": "ROYAL",
                    "title": "경복궁 관람 안내",
                    "content": "관람 시간은 오전 9시부터 오후 6시까지입니다.",
                    "chunk_index": 0,
                    "url": "https://royal.go.kr/notice/1",
                    "index_status": "indexed",
                    "indexed_at": "2026-06-15T10:35:00+00:00",
                }
            ]
        },
    )

    chunk_id: Annotated[UUID, Field(description="Milvus PK")]
    source_id: Annotated[UUID, Field(description="원본 Document의 source_id")]
    source_table: str = Field(description="원본 테이블명")
    source_type: SourceType = Field(description="출처 타입")
    site_code: str = Field(description="사이트 구분 코드")
    title: str = Field(description="원본 Document 제목")
    chunk_index: int = Field(
        ge=0,
        description="Document 내 조각 순번",
    )
    url: str | None = Field(
        default=None,
        description="원본 링크",
    )
    index_status: IndexStatus = Field(
        default=IndexStatus.PENDING,
        description="청크 단위 색인 상태",
    )
    indexed_at: datetime | None = Field(
        default=None,
        description="색인 완료 시각",
    )

    @field_validator("indexed_at", mode="before")
    @classmethod
    def validate_indexed_at(cls, v: Any) -> datetime | None:
        """indexed_at이 naive datetime이면 UTC로 보정."""
        if v is None:
            return None
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=UTC)
            return v
        return v


__all__ = [
    "SourceType",
    "IndexStatus",
    "VALID_SOURCE_TYPES",
    "SOURCE_TYPE_LABEL",
    "ContentHashMixin",
    "Document",
    "Chunk",
]
