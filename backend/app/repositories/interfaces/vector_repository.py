"""벡터 저장소 인터페이스."""

from abc import ABC, abstractmethod
from typing import Any

# ──────────────────────────────────────────────
# VectorRepository 인터페이스
# ──────────────────────────────────────────────


class VectorRepository(ABC):
    """벡터 저장소 추상 클래스. 벡터 DB(Milvus 등) 관리 담당."""

    @abstractmethod
    async def insert_vectors(
        self,
        collection_name: str,  # 컬렉션명 — "documents", "chunks" 등
        vectors: list[dict[str, Any]],  # 벡터 + 메타데이터
    ) -> list[str]:
        """벡터 삽입. 삽입된 ID 목록 반환."""
        ...

    @abstractmethod
    async def upsert_vectors(
        self,
        collection_name: str,  # 컬렉션명
        vectors: list[dict[str, Any]],  # 벡터 + 메타데이터
    ) -> int:
        """벡터 upsert. ID 있으면 덮어쓰기, 없으면 삽입. 처리된 개수 반환."""
        ...

    @abstractmethod
    async def search_vectors(
        self,
        collection_name: str,  # 컬렉션명
        query_vector: list[float],  # 쿼리 벡터 (임베딩)
        top_k: int = 10,  # 상위 K개 반환
        filters: dict[str, Any] | None = None,  # 필터 조건 — site_code, source_type 등
    ) -> list[dict[str, Any]]:
        """유사도 기반 벡터 검색. 유사도 스코어 + 메타데이터 반환."""
        ...

    @abstractmethod
    async def delete_vectors(
        self,
        collection_name: str,  # 컬렉션명
        ids: list[str],  # 삭제할 벡터 ID 목록
    ) -> int:
        """벡터 삭제. 삭제된 개수 반환."""
        ...
