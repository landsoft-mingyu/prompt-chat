"""슬롯 수집 서비스 인터페이스."""

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.orchestrator import ChatIntent


class ISlotFillingService(ABC):
    """슬롯 수집 서비스 추상 인터페이스."""

    @abstractmethod
    def get_missing_slots(self, intent: ChatIntent, slots: dict[str, Any]) -> list[str]:
        """필수 슬롯 중 아직 채워지지 않은 목록 반환."""
        ...

    @abstractmethod
    def build_prompt_for_missing_slot(
        self, missing_slots: list[str], intent: ChatIntent
    ) -> str:
        """다음으로 물어볼 슬롯 안내 문구 생성."""
        ...

    @abstractmethod
    def validate_slots(
        self, intent: ChatIntent, slots: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """슬롯 값 형식 검증. (is_valid, error_message) 반환."""
        ...

    @abstractmethod
    async def extract_slots(
        self, message: str, intent: ChatIntent, current_slots: dict[str, Any]
    ) -> dict[str, Any]:
        """메시지에서 슬롯 값을 LLM으로 추출하고 기존 slots에 병합."""
        ...

    @abstractmethod
    def build_confirmation_message(
        self, intent: ChatIntent, slots: dict[str, Any]
    ) -> str:
        """슬롯 내용 요약 + 확인 요청 메시지 생성."""
        ...
