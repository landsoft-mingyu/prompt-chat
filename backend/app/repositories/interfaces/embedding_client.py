"""임베딩 클라이언트 인터페이스."""

from abc import ABC, abstractmethod


class IEmbeddingClient(ABC):
    """임베딩 서비스 HTTP 클라이언트 추상 인터페이스."""

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        *,
        max_length: int = 8192,
        batch_size: int = 16,
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """텍스트 목록을 dense + sparse 벡터로 변환."""
        ...

    @abstractmethod
    async def rerank(self, query: str, texts: list[str]) -> list[float]:
        """쿼리와 텍스트 쌍의 관련도 점수 반환."""
        ...

    @abstractmethod
    async def health(self) -> dict:
        """임베딩 서비스 헬스 체크."""
        ...
