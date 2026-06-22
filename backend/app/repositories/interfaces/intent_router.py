"""의도 분류기 인터페이스."""

from abc import ABC, abstractmethod

from app.schemas.orchestrator import IntentRouterResult


class IIntentRouter(ABC):
    """의도 분류기 추상 인터페이스.

    사용자 메시지와 세션 컨텍스트를 받아 ChatIntent로 분류한다.
    """

    @abstractmethod
    async def classify(
        self,
        message: str,
        session_context: dict,
        site_code: str,
    ) -> IntentRouterResult:
        """사용자 메시지를 의도로 분류하고 슬롯을 추출한다.

        Args:
            message: 사용자 입력 메시지
            session_context: 현재 세션 상태 (current_intent, slots 등)
            site_code: 사이트 구분 코드

        Returns:
            IntentRouterResult (intent, confidence, extracted_slots)
        """
        ...
