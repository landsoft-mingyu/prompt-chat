"""세션 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas.orchestrator import SlotFillingState


class SessionStore(ABC):
    """세션 저장소 추상 클래스. 세션 데이터(Redis 등) 관리 담당."""

    @abstractmethod
    async def set_session(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> None:
        """세션 저장."""
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """세션 조회. 없거나 만료되면 None 반환."""
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제. 성공 여부 반환."""
        ...

    @abstractmethod
    async def exists_session(self, session_id: str) -> bool:
        """세션 존재 여부 확인."""
        ...

    @abstractmethod
    async def get_slot_state(self, session_id: str) -> SlotFillingState | None:
        """진행 중인 슬롯 필링 상태 조회."""
        ...

    @abstractmethod
    async def save_slot_state(
        self,
        session_id: str,
        state: SlotFillingState,
        ttl: int = 1800,
    ) -> None:
        """슬롯 필링 상태 저장."""
        ...

    @abstractmethod
    async def delete_slot_state(self, session_id: str) -> None:
        """슬롯 필링 상태 삭제."""
        ...
