"""예약 흐름 처리 인터페이스."""

from abc import ABC, abstractmethod

from app.schemas.orchestrator import ChatIntent, OrchestratorResponse, SlotFillingState


class IReservationOrchestrator(ABC):
    """예약 흐름 처리 추상 인터페이스.

    슬롯 수집 → 확인 → API 호출 흐름을 담당한다.
    """

    @abstractmethod
    async def handle(
        self,
        intent: ChatIntent,
        message: str,
        session_id: str,
        site_code: str,
        slot_state: SlotFillingState,
    ) -> OrchestratorResponse:
        """의도에 맞는 예약 흐름 처리.

        슬롯이 부족하면 질문 생성, 모두 채워졌으면 확인 요청,
        확인 완료(CONFIRMING + 긍정 응답)시 API 호출.
        """
        ...

    @abstractmethod
    async def list_programs(
        self,
        session_id: str,
        site_code: str,
        group_code: str | None = None,
    ) -> OrchestratorResponse:
        """예약 가능한 프로그램 목록 조회."""
        ...

    @abstractmethod
    async def list_parts(
        self,
        session_id: str,
        res_idx: str,
        res_part_date: str,
    ) -> OrchestratorResponse:
        """특정 프로그램의 예약 가능 회차 목록 조회."""
        ...
