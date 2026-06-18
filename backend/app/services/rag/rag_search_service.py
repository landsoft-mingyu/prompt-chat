"""RAG 검색 서비스 구현."""

from app.repositories.interfaces.rag_search_service import IRAGSearchService
from app.repositories.interfaces.vector_repository import VectorRepository
from app.schemas.document import SourceType
from app.services.rag.embedding_client import EmbeddingClient


class RAGSearchService(IRAGSearchService):
    """RAG 검색 서비스."""

    def __init__(
        self,
        vector_repo: VectorRepository,
        embedding_client: EmbeddingClient,
        collection_name: str = "chunks",
    ):
        """
        Args:
            vector_repo: 벡터 저장소 (의존성 주입)
            embedding_client: 임베딩 서비스 클라이언트
            collection_name: Milvus 컬렉션명 (default: "chunks")
        """
        self.vector_repo = vector_repo
        self.embedding_client = embedding_client
        self.collection_name = collection_name

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
            source_types: 소스 타입 필터
            site_code: 사이트 코드 필터

        Returns:
            검색 결과 리스트
        """
        try:
            # 쿼리 임베딩
            dense, sparse = self.embedding_client.embed([query])
            query_vector = dense[0]

            # 필터 조건 구성
            filters = {}
            if source_types:
                filters["source_type"] = [st.value for st in source_types]
            if site_code:
                filters["site_code"] = site_code

            # 벡터 검색
            results = await self.vector_repo.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_vector,
                top_k=top_k,
                filters=filters if filters else None,
            )

            # 결과 포매팅
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "id": result.get("id"),
                        "title": result.get("title"),
                        "content": result.get("content"),
                        "source_type": result.get("source_type"),
                        "source_table": result.get("source_table"),
                        "site_code": result.get("site_code"),
                        "url": result.get("url"),
                        "score": result.get("distance"),  # 유사도 점수
                        "metadata": result.get("metadata", {}),
                    }
                )

            return formatted_results

        except Exception as e:
            raise RuntimeError(f"RAG 검색 실패: {str(e)}") from e

    async def health(self) -> dict:
        """헬스 체크."""
        try:
            # 임베딩 서비스 헬스 체크
            embedding_health = self.embedding_client.health()

            return {
                "status": "healthy",
                "embedding_service": embedding_health,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
