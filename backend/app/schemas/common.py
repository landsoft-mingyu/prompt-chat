from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ──────────────────────────────────────────────
# Enum 정의 (타입 안정성)
# ──────────────────────────────────────────────


class CardType(str, Enum):
    """프론트엔드 액션 카드 타입 — Enum으로 정의하여 타입 안정성 확보."""

    RESERVATION_SLOT = "reservation_slot"  # 예약 가능 회차
    RESERVATION_CONFIRM = "reservation_confirm"  # 예약 확인 요청
    CONTENT = "content"  # 콘텐츠 카드
    FILE = "file"  # 파일 다운로드
    CONFIRM = "confirm"  # 일반 확인 요청


# ──────────────────────────────────────────────
# ActionCard 클래스
# ──────────────────────────────────────────────


class ActionCard(BaseModel):
    """
    프론트엔드에 표시할 액션 카드.

    사용자가 클릭할 수 있는 버튼/카드를 정의한다.
    LLM 응답에 함께 반환되어 사용자가 다음 액션을 쉽게 선택할 수 있도록 돕는다.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "type": "reservation_slot",
                    "title": "한국어 단체 해설 10:00",
                    "description": "잔여 5석",
                    "payload": {"pt_idx": 1, "res_idx": "202412120391"},
                },
                {
                    "type": "content",
                    "title": "전시회 상세 보기",
                    "description": None,
                    "payload": {"doc_id": "ex_2024_001"},
                },
                {
                    "type": "confirm",
                    "title": "예약 진행",
                    "description": "예약을 완료하시겠습니까?",
                    "payload": {"action": "confirm_reservation"},
                },
            ]
        },
    )

    type: CardType = Field(description="카드 유형")
    title: str = Field(
        min_length=1,
        description="카드 제목 (버튼 텍스트 또는 카드 헤더)",
    )
    description: str | None = Field(
        default=None,
        description="카드 설명 (부가 정보, 선택사항)",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="카드 클릭 시 전달될 데이터 (action_type별로 구조가 다름)",
    )


__all__ = [
    "CardType",
    "ActionCard",
]
