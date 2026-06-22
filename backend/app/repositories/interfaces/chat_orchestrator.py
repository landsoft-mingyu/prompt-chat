"""ChatOrchestrator 인터페이스."""

from abc import ABC, abstractmethod

from app.schemas.chat import ChatRequest
from app.schemas.orchestrator import OrchestratorResponse


class IChatOrchestrator(ABC):
    """통합 챗봇 오케스트레이터 추상 인터페이스."""

    @abstractmethod
    async def handle(self, request: ChatRequest) -> OrchestratorResponse:
        """사용자 요청을 처리하고 응답을 반환."""
        ...
