"""세션 저장소 인터페이스."""

from abc import ABC, abstractmethod
from typing import Any

# ──────────────────────────────────────────────
# SessionStore 인터페이스
# ──────────────────────────────────────────────


class SessionStore(ABC):
    """세션 저장소 추상 클래스. 세션 데이터(Redis 등) 관리 담당."""

    @abstractmethod
    async def set_session(
        self,
        session_id: str,  # 세션 식별자
        data: dict[str, Any],  # 세션 데이터
        ttl_seconds: int = 3600,  # 유효 시간 (초)
    ) -> None:
        """세션 저장."""
        ...

    @abstractmethod
    async def get_session(
        self,
        session_id: str,  # 세션 식별자
    ) -> dict[str, Any] | None:
        """세션 조회. 없거나 만료되면 None 반환."""
        ...

    @abstractmethod
    async def delete_session(
        self,
        session_id: str,  # 세션 식별자
    ) -> bool:
        """세션 삭제. 성공 여부 반환."""
        ...

    @abstractmethod
    async def exists_session(
        self,
        session_id: str,  # 세션 식별자
    ) -> bool:
        """세션 존재 여부 확인."""
        ...
