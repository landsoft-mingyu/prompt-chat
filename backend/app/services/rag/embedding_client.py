"""BGE-M3 임베딩 서비스 HTTP 클라이언트.

적재 스크립트와 검색 API가 공통으로 사용. dense + sparse 반환.
"""

from __future__ import annotations

import os

import httpx


class EmbeddingClient:
    def __init__(self, base_url: str | None = None, timeout: float = 300.0):
        self.base_url = (
            base_url or os.getenv("EMBEDDING_URL", "http://127.0.0.1:18086")
        ).rstrip("/")
        self.timeout = timeout

    def embed(
        self, texts: list[str], *, max_length: int = 8192, batch_size: int = 16
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """texts → (dense[N][1024], sparse[N]{token_id: weight})."""
        resp = httpx.post(
            f"{self.base_url}/embed",
            json={"texts": texts, "max_length": max_length, "batch_size": batch_size},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        # JSON 키는 문자열로 직렬화되므로 sparse 키를 int로 복원
        sparse = [{int(k): float(v) for k, v in d.items()} for d in data["sparse"]]
        return data["dense"], sparse

    def health(self) -> dict:
        resp = httpx.get(f"{self.base_url}/health", timeout=30)
        resp.raise_for_status()
        return resp.json()
