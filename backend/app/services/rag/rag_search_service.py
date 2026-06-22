"""RAG 검색 서비스 구현."""

from app.repositories.interfaces.embedding_client import IEmbeddingClient
from app.repositories.interfaces.rag_search_service import IRAGSearchService
from app.repositories.interfaces.vector_repository import VectorRepository
from app.schemas.document import SourceType


class RAGSearchService(IRAGSearchService):
    """RAG 검색 서비스."""

    def __init__(
        self,
        vector_repo: VectorRepository,
        embedding_client: IEmbeddingClient,
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

    _FETCH_K = 15  # 리랭커에 넘길 후보 수
    _RETURN_K = 5  # 리랭킹 후 최종 반환 수

    async def search(
        self,
        query: str,
        top_k: int = _RETURN_K,
        source_types: list[SourceType] | None = None,
        site_code: str | None = None,
    ) -> list[dict]:
        """dense ANN top_k=15 → rerank → 상위 5개 반환."""
        try:
            dense, _ = await self.embedding_client.embed([query])
            query_vector = dense[0]

            filters = {}
            if source_types:
                filters["source_type"] = [st.value for st in source_types]
            if site_code:
                filters["site_code"] = site_code

            # 후보 15개 검색
            raw = await self.vector_repo.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_vector,
                top_k=self._FETCH_K,
                filters=filters if filters else None,
            )

            if not raw:
                return []

            # 리랭킹
            texts = [r.get("content") or "" for r in raw]
            scores = await self.embedding_client.rerank(query, texts)

            # 점수로 재정렬 → 상위 RETURN_K 반환
            ranked = sorted(
                zip(scores, raw),
                key=lambda x: x[0],
                reverse=True,
            )[: self._RETURN_K]

            return [
                {
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "content": r.get("content"),
                    "source_type": r.get("source_type"),
                    "source_table": r.get("source_table"),
                    "site_code": r.get("site_code"),
                    "url": r.get("url"),
                    "score": float(score),
                    "metadata": r.get("metadata", {}),
                }
                for score, r in ranked
            ]

        except Exception as e:
            raise RuntimeError(f"RAG 검색 실패: {str(e)}") from e

    async def health(self) -> dict:
        """헬스 체크."""
        try:
            # 임베딩 서비스 헬스 체크
            embedding_health = await self.embedding_client.health()

            return {
                "status": "healthy",
                "embedding_service": embedding_health,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
