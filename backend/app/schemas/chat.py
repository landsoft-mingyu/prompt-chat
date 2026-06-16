from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import ActionCard
from app.schemas.document import VALID_SOURCE_TYPES

# ──────────────────────────────────────────────
# Enum 정의 (타입 안정성)
# ──────────────────────────────────────────────


class ResponseMode(StrEnum):
    """AI 응답 모드 — Enum으로 정의하여 타입 안정성 확보."""

    RAG = "rag"  # 벡터 검색 기반 응답
    ACTION = "action"  # 액션 제시 기반 응답
    CLARIFICATION = "clarification"  # 추가 정보 필요
    GENERAL = "general"  # 일반 대화형 응답


# ──────────────────────────────────────────────
# 타입 에일리어스 (하위 호환성)
# ──────────────────────────────────────────────

ResponseModeAlias = ResponseMode

# ──────────────────────────────────────────────
# ChatRequest 클래스
# ──────────────────────────────────────────────


class ChatRequest(BaseModel):
    """
    사용자 메시지 요청.

    프론트엔드에서 사용자의 자연어 프롬프트를 백엔드로 전송할 때 사용된다.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "session_id": "sess_abc123def456",
                    "site_code": "ROYAL",
                    "message": "내일 경복궁 예약 가능한 회차 있어?",
                    "user_id": "user_789",
                }
            ]
        },
    )

    session_id: Annotated[
        str,
        Field(
            min_length=1,
            description="세션 식별자 (Redis 등에서 발급)",
        ),
    ]
    site_code: Annotated[
        str,
        Field(description="사이트 구분 코드 (필수, 프론트에서 항상 명시)"),
    ]
    message: Annotated[
        str,
        Field(
            min_length=1,
            max_length=2000,
            description="사용자 입력 메시지 (자연어)",
        ),
    ]
    user_id: Annotated[
        str | None,
        Field(
            default=None,
            description="사용자 식별자 (선택, 비회원 허용)",
        ),
    ] = None


# ──────────────────────────────────────────────
# Source 클래스
# ──────────────────────────────────────────────


class Source(BaseModel):
    """
    검색 결과 출처 정보.

    RAG 모드 응답에서 참조한 문서의 메타데이터를 전달한다.
    클라이언트는 이를 통해 답변의 근거를 확인할 수 있다.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "source_id": "doc_550e8400-e29b-41d4-a716-446655440000",
                    "source_type": "notice",
                    "title": "경복궁 관람 안내",
                    "url": "https://royal.go.kr/notice/1",
                }
            ]
        },
    )

    source_id: Annotated[
        str,
        Field(description="원본 Document의 source_id"),
    ]
    source_type: Annotated[
        str,
        Field(description="출처 타입 (VALID_SOURCE_TYPES 참조)"),
    ]
    title: Annotated[
        str | None,
        Field(
            default=None,
            description="출처 제목 (검색 결과 표시용)",
        ),
    ] = None
    url: Annotated[
        str | None,
        Field(
            default=None,
            description="원본 링크 (클릭 추적용)",
        ),
    ] = None

    @field_validator("source_type", mode="before")
    @classmethod
    def validate_source_type(cls, v: Any) -> str:
        """source_type 검증. 문자열만 지원."""
        if isinstance(v, str):
            if v not in VALID_SOURCE_TYPES:
                types_str = ", ".join(sorted(VALID_SOURCE_TYPES))
                raise ValueError(f"source_type must be one of {types_str}, got {v!r}")
            return v
        raise TypeError(f"source_type must be str, got {type(v).__name__}")


# ──────────────────────────────────────────────
# ChatResponse 클래스
# ──────────────────────────────────────────────


class ChatResponse(BaseModel):
    """
    AI 응답.

    사용자 메시지를 처리한 결과를 클라이언트로 반환한다.
    응답 모드(RAG/Action/Clarification/General)에 따라 구성이 달라진다.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "answer": "경복궁 한국어 단체 해설 10시 회차 5자리 남음",
                    "mode": "action",
                    "sources": [
                        {
                            "source_id": "doc_123",
                            "source_type": "notice",
                            "title": "경복궁 관람 안내",
                        }
                    ],
                    "cards": [
                        {
                            "type": "reservation_slot",
                            "title": "10시 (남은 자리: 5)",
                            "payload": {"time": "10:00", "available": 5},
                        }
                    ],
                    "required_slots": [],
                }
            ]
        },
    )

    answer: Annotated[
        str,
        Field(
            min_length=1,
            description="AI 응답 텍스트 (자연어)",
        ),
    ]
    mode: Annotated[
        str,
        Field(description="응답 모드 (rag/action/clarification/general)"),
    ]
    sources: Annotated[
        list[Source],
        Field(
            default_factory=list,
            description="참조 출처 목록 (RAG 모드에서 주로 포함)",
        ),
    ] = Field(default_factory=list)
    cards: Annotated[
        list[ActionCard],
        Field(
            default_factory=list,
            description="액션 카드 목록 (Action 모드에서 주로 포함)",
        ),
    ] = Field(default_factory=list)
    required_slots: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="추가 필요 정보 목록 (Clarification 모드에서 주로 포함)",
        ),
    ] = Field(default_factory=list)

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: Any) -> str:
        """mode 검증. Enum 및 문자열 모두 지원."""
        if isinstance(v, ResponseMode):
            return v.value
        if isinstance(v, str):
            valid_modes = {rm.value for rm in ResponseMode}
            if v not in valid_modes:
                raise ValueError(
                    f"mode must be one of {sorted(valid_modes)}, got {v!r}"
                )
            return v
        raise TypeError(f"mode must be str or ResponseMode, got {type(v).__name__}")


# ──────────────────────────────────────────────
# Re-export (하위 호환성 및 편의성)
# ──────────────────────────────────────────────

__all__ = [
    "ResponseMode",
    "ResponseModeAlias",
    "ChatRequest",
    "Source",
    "ChatResponse",
    "ActionCard",
]
