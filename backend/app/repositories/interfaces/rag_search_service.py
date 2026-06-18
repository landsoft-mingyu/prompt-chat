"""RAG 검색 서비스 인터페이스."""

from abc import ABC, abstractmethod

from app.schemas.document import SourceType


class IRAGSearchService(ABC):
    """RAG 검색 서비스 추상 인터페이스."""

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 10,
        source_types: list[SourceType] | None = None,
        site_code: str | None = None,
    ) -> list[dict]:
        """
        쿼리 검색.

        Args:
            query: 검색 쿼리
            top_k: 상위 K개 결과 반환
            source_types: 소스 타입 필터 (None이면 모든 타입)
            site_code: 사이트 코드 필터 (None이면 모든 사이트)

        Returns:
            검색 결과 리스트 [{"title": ..., "content": ..., "source_type": ..., ...}]
        """
        ...

    @abstractmethod
    async def health(self) -> dict:
        """헬스 체크."""
        ...
