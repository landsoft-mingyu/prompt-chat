"""콘텐츠 저장소 인터페이스."""

from abc import ABC, abstractmethod

from app.schemas.document import Document, IndexStatus

# ──────────────────────────────────────────────
# ContentRepository 인터페이스
# ──────────────────────────────────────────────


class ContentRepository(ABC):
    """콘텐츠 저장소 추상 클래스."""

    @abstractmethod
    async def find_documents(
        self,
        site_code: str,  # 사이트 코드
        source_type: str | None = None,  # 출처 유형 — None이면 전체 조회
    ) -> list[Document]:
        """RAG 임베딩 대상 Document 목록 조회."""
        ...

    @abstractmethod
    async def find_document_by_id(
        self,
        source_id: str,  # 원본 테이블 PK
        source_table: str,  # 원본 테이블명
    ) -> Document | None:
        """source_id + source_table로 단일 Document 조회. 없으면 None 반환."""
        ...

    @abstractmethod
    async def find_documents_by_status(
        self,
        site_code: str,  # 사이트 코드
        index_status: IndexStatus,  # 색인 상태 (pending/indexed/failed)
    ) -> list[Document]:
        """색인 상태별 Document 조회. 증분 색인/재시도용."""
        ...
