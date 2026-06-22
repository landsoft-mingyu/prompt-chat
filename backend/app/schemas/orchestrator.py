"""ChatOrchestrator 전용 스키마."""

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatIntent(str, Enum):
    """사용자 의도 분류."""

    RAG_SEARCH = "rag_search"
    RESERVATION_LIST = "reservation_list"
    RESERVATION_PARTS = "reservation_parts"
    RESERVATION_CREATE = "reservation_create"
    RESERVATION_QUERY = "reservation_query"
    RESERVATION_CANCEL = "reservation_cancel"
    RESERVATION_CONTINUE = "reservation_continue"


class SlotState(str, Enum):
    """슬롯 수집 단계."""

    COLLECTING = "collecting"  # 슬롯 수집 중
    CONFIRMING = "confirming"  # 전체 슬롯 확인 대기
    DONE = "done"  # 처리 완료


class IntentRouterResult(BaseModel):
    """IIntentRouter.classify() 반환 타입."""

    model_config = ConfigDict(extra="forbid")

    intent: ChatIntent
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_slots: dict[str, Any] = Field(default_factory=dict)


class SlotFillingState(BaseModel):
    """Redis에 직렬화하여 저장하는 슬롯 필링 상태.

    세션 키: slot:{session_id}, TTL 30분
    """

    model_config = ConfigDict(extra="forbid")

    intent: ChatIntent
    slots: dict[str, Any] = Field(default_factory=dict)
    state: SlotState = SlotState.COLLECTING
    messages: list[dict[str, str]] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    """POST /api/v1/chat 응답."""

    model_config = ConfigDict(extra="forbid")

    session_id: Annotated[str, Field(description="세션 식별자")]
    message: Annotated[str, Field(description="AI 응답 텍스트")]
    intent: Annotated[str, Field(description="분류된 의도")]
    action_card: Annotated[
        dict[str, Any] | None,
        Field(default=None, description="예약 패널 표시용 카드"),
    ] = None
    slots_needed: Annotated[
        list[str] | None,
        Field(default=None, description="아직 필요한 슬롯 목록"),
    ] = None
    slots_filled: Annotated[
        dict[str, Any] | None,
        Field(default=None, description="현재까지 채워진 슬롯"),
    ] = None
    requires_confirmation: Annotated[
        bool,
        Field(default=False, description="사용자 최종 확인 필요 여부"),
    ] = False
    mode: Annotated[
        Literal["chat", "reservation", "rag"],
        Field(default="chat", description="응답 모드"),
    ] = "chat"
    sources: Annotated[
        list[dict] | None,
        Field(default=None, description="RAG 검색 청크 목록 (title, content, score)"),
    ] = None


__all__ = [
    "ChatIntent",
    "SlotState",
    "IntentRouterResult",
    "SlotFillingState",
    "OrchestratorResponse",
]
