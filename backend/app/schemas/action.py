"""액션 실행 스키마."""

from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import ActionCard

# ──────────────────────────────────────────────
# Enum 정의 (타입 안정성)
# ──────────────────────────────────────────────


class ActionType(StrEnum):
    """액션 유형 — Enum으로 정의하여 타입 안정성 확보."""

    SEARCH = "search"  # 조회
    DETAIL = "detail"  # 상세 조회
    RESERVE = "reserve"  # 예약 생성
    CANCEL = "cancel"  # 예약 취소
    DOWNLOAD = "download"  # 파일 다운로드
    SUBMIT_FORM = "submit_form"  # 문의 제출


class Intent(StrEnum):
    """사용자 의도 — Enum으로 정의."""

    RESERVATION_SEARCH_AVAILABLE_SLOTS = "reservation.search_available_slots"
    RESERVATION_CREATE = "reservation.create"
    RESERVATION_CANCEL = "reservation.cancel"
    CONTENT_SEARCH = "content.search"
    CONTENT_DETAIL = "content.detail"
    FILE_DOWNLOAD = "file.download"
    CHATBOT_FAQ = "chatbot.faq"


# ──────────────────────────────────────────────
# ActionRequest 클래스
# ──────────────────────────────────────────────


class ActionRequest(BaseModel):
    """
    LLM이 생성하거나 프론트 카드 버튼 클릭 시 생성되는 액션 요청.

    사용자의 의도를 파악한 후, 실제 기능 실행을 위한 구조화된 요청이다.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "site_code": "ROYAL",
                    "action_type": "search",
                    "intent": "reservation.search_available_slots",
                    "slots": {"date": "2026-06-16", "facility": "exhibition"},
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "user_789",
                    "requires_confirmation": False,
                }
            ]
        },
    )

    site_code: Annotated[
        str,
        Field(description="사이트 구분 코드 (필수)"),
    ]
    action_type: Annotated[
        ActionType,
        Field(description="액션 유형"),
    ]
    intent: Annotated[
        Intent,
        Field(description="세부 의도"),
    ]
    slots: Annotated[
        dict[str, Any],
        Field(
            default_factory=dict,
            description="액션 실행에 필요한 파라미터 (date, facility, time 등)",
        ),
    ] = Field(default_factory=dict)
    session_id: Annotated[
        UUID,
        Field(description="세션 식별자 (UUID 형식)"),
    ]
    user_id: Annotated[
        str | None,
        Field(
            default=None,
            description="사용자 식별자 (선택, 비회원 허용)",
        ),
    ] = None
    requires_confirmation: Annotated[
        bool,
        Field(
            default=False,
            description="실행 전 사용자 확인 필요 여부 (예약 생성/취소는 True)",
        ),
    ] = False

    @field_validator("action_type", mode="before")
    @classmethod
    def validate_action_type(cls, v: Any) -> ActionType:
        """action_type 검증. Enum 및 문자열 모두 지원."""
        if isinstance(v, ActionType):
            return v
        if isinstance(v, str):
            try:
                return ActionType(v)
            except ValueError:
                raise ValueError(
                    f"action_type must be one of "
                    f"{[at.value for at in ActionType]}, got {v!r}"
                )
        raise TypeError(
            f"action_type must be str or ActionType, got {type(v).__name__}"
        )

    @field_validator("intent", mode="before")
    @classmethod
    def validate_intent(cls, v: Any) -> Intent:
        """intent 검증. Enum 및 문자열 모두 지원."""
        if isinstance(v, Intent):
            return v
        if isinstance(v, str):
            try:
                return Intent(v)
            except ValueError:
                raise ValueError(
                    f"intent must be one of {[i.value for i in Intent]}, got {v!r}"
                )
        raise TypeError(f"intent must be str or Intent, got {type(v).__name__}")


# ──────────────────────────────────────────────
# ActionResult 클래스
# ──────────────────────────────────────────────


class ActionResult(BaseModel):
    """
    액션 실행 결과.

    ActionRequest를 실행한 후, 그 결과를 클라이언트에 반환한다.
    성공/실패 여부, 메시지, 데이터, 그리고 다음 액션을 위한 카드를 포함한다.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "message": "예약 가능한 회차를 조회했습니다.",
                    "data": {
                        "slots": [
                            {"time": "10:00", "available": 5},
                            {"time": "11:00", "available": 3},
                        ]
                    },
                    "cards": [
                        {
                            "type": "reservation_slot",
                            "title": "10:00 (남은 자리: 5)",
                            "payload": {"time": "10:00"},
                        }
                    ],
                }
            ]
        },
    )

    success: Annotated[
        bool,
        Field(description="실행 성공 여부"),
    ]
    message: Annotated[
        str,
        Field(
            min_length=1,
            description="사용자에게 보여줄 결과 메시지",
        ),
    ]
    data: Annotated[
        dict[str, Any],
        Field(
            default_factory=dict,
            description="실행 결과 데이터 (API 응답값 등)",
        ),
    ] = Field(default_factory=dict)
    cards: Annotated[
        list[ActionCard],
        Field(
            default_factory=list,
            description="프론트엔드에 표시할 액션 카드 목록",
        ),
    ] = Field(default_factory=list)


__all__ = [
    "ActionType",
    "Intent",
    "ActionRequest",
    "ActionResult",
]
