"""Tests for Action schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.action import (
    ActionRequest,
    ActionResult,
    ActionType,
    Intent,
)
from app.schemas.chat import ActionCard


class TestActionRequest:
    """ActionRequest 스키마 테스트."""

    def test_action_request_valid(self):
        """ActionRequest 정상 생성."""
        session_id = uuid4()
        req = ActionRequest(
            site_code="ROYAL",
            action_type="search",
            intent="reservation.search_available_slots",
            slots={"date": "2026-06-20", "facility": "exhibition"},
            session_id=session_id,
            user_id="user_456",
            requires_confirmation=False,
        )
        assert req.site_code == "ROYAL"
        assert req.action_type == ActionType.SEARCH
        assert req.intent == Intent.RESERVATION_SEARCH_AVAILABLE_SLOTS
        assert req.slots["date"] == "2026-06-20"
        assert req.requires_confirmation is False

    def test_action_request_minimal(self):
        """ActionRequest 최소 필드."""
        req = ActionRequest(
            site_code="ROYAL",
            action_type="search",
            intent="content.search",
            session_id=uuid4(),
        )
        assert req.slots == {}
        assert req.user_id is None
        assert req.requires_confirmation is False

    def test_action_request_invalid_intent(self):
        """잘못된 intent → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ActionRequest(
                site_code="ROYAL",
                action_type="search",
                intent="invalid.intent",
                session_id=uuid4(),
            )
        assert "intent" in str(exc_info.value)

    def test_action_request_with_confirmation(self):
        """예약 생성 시 확인 필요."""
        req = ActionRequest(
            site_code="ROYAL",
            action_type="reserve",
            intent="reservation.create",
            slots={"date": "2026-06-20", "time": "10:00"},
            session_id=uuid4(),
            requires_confirmation=True,
        )
        assert req.requires_confirmation is True

    def test_action_request_empty_session_id(self):
        """session_id 빈 UUID가 아닌 값 → ValidationError."""
        with pytest.raises(ValidationError):
            ActionRequest(
                site_code="ROYAL",
                action_type="search",
                intent="content.search",
                session_id="not-a-uuid",
            )

    def test_action_request_all_action_types(self):
        """모든 ActionType 값 테스트."""
        action_types = [at.value for at in ActionType]
        for action_type_str in action_types:
            req = ActionRequest(
                site_code="ROYAL",
                action_type=action_type_str,
                intent="content.search",
                session_id=uuid4(),
            )
            assert req.action_type.value == action_type_str

    def test_action_request_all_valid_intents(self):
        """모든 Intent 값 테스트."""
        for intent in Intent:
            req = ActionRequest(
                site_code="ROYAL",
                action_type="search",
                intent=intent.value,
                session_id=uuid4(),
            )
            assert req.intent == intent

    def test_action_request_extra_field_forbidden(self):
        """추가 필드 → ValidationError."""
        with pytest.raises(ValidationError):
            ActionRequest(
                site_code="ROYAL",
                action_type="search",
                intent="content.search",
                session_id=uuid4(),
                extra_field="not allowed",  # type: ignore
            )


class TestActionResult:
    """ActionResult 스키마 테스트."""

    def test_action_result_success(self):
        """ActionResult 성공 케이스."""
        result = ActionResult(
            success=True,
            message="예약 가능한 시간대입니다.",
            data={"slots": ["10:00", "11:00", "12:00"]},
            cards=[
                {
                    "type": "reservation_slot",
                    "title": "10:00",
                    "payload": {"time": "10:00"},
                }
            ],
        )
        assert result.success is True
        assert result.message == "예약 가능한 시간대입니다."
        assert len(result.data["slots"]) == 3
        assert len(result.cards) == 1

    def test_action_result_failure(self):
        """ActionResult 실패 케이스."""
        result = ActionResult(
            success=False,
            message="예약에 실패했습니다.",
        )
        assert result.success is False
        assert result.message == "예약에 실패했습니다."
        assert result.data == {}
        assert result.cards == []

    def test_action_result_minimal(self):
        """ActionResult 최소 필드."""
        result = ActionResult(
            success=True,
            message="완료되었습니다.",
        )
        assert result.success is True
        assert result.message == "완료되었습니다."
        assert result.data == {}
        assert result.cards == []

    def test_action_result_with_cards(self):
        """액션 결과와 카드 함께."""
        cards = [
            ActionCard(type="content", title="검색 결과"),
            ActionCard(type="confirm", title="진행하시겠습니까?"),
        ]
        result = ActionResult(
            success=True,
            message="검색 결과입니다.",
            cards=cards,
        )
        assert len(result.cards) == 2
        assert result.cards[0].type == "content"
        assert result.cards[1].type == "confirm"

    def test_action_result_extra_field_forbidden(self):
        """추가 필드 → ValidationError."""
        with pytest.raises(ValidationError):
            ActionResult(
                success=True,
                message="test",
                extra_field="not allowed",  # type: ignore
            )


class TestActionIntegration:
    """ActionRequest/Result 통합 테스트."""

    def test_search_action_workflow(self):
        """검색 액션 워크플로우."""
        request = ActionRequest(
            site_code="ROYAL",
            action_type="search",
            intent="content.search",
            slots={"keyword": "미술전시"},
            session_id=uuid4(),
        )
        assert request.action_type == ActionType.SEARCH

        result = ActionResult(
            success=True,
            message="2개의 전시를 찾았습니다.",
            data={"count": 2, "items": [{"id": "ex_1"}, {"id": "ex_2"}]},
            cards=[
                ActionCard(type="content", title="전시 1"),
                ActionCard(type="content", title="전시 2"),
            ],
        )
        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.cards) == 2

    def test_reservation_action_workflow(self):
        """예약 액션 워크플로우."""
        request = ActionRequest(
            site_code="ROYAL",
            action_type="reserve",
            intent="reservation.create",
            slots={
                "date": "2026-06-20",
                "time": "10:00",
                "facility": "exhibition",
            },
            session_id=uuid4(),
            user_id="user_456",
            requires_confirmation=True,
        )
        assert request.action_type == ActionType.RESERVE
        assert request.requires_confirmation is True

        result = ActionResult(
            success=True,
            message="예약이 확정되었습니다.",
            data={
                "reservation_id": "res_789",
                "date": "2026-06-20",
                "time": "10:00",
            },
        )
        assert result.success is True
        assert result.data["reservation_id"] == "res_789"

    def test_cancel_action_workflow(self):
        """취소 액션 워크플로우."""
        request = ActionRequest(
            site_code="ROYAL",
            action_type="cancel",
            intent="reservation.cancel",
            slots={"reservation_id": "res_789"},
            session_id=uuid4(),
            requires_confirmation=True,
        )
        assert request.action_type == ActionType.CANCEL

        result = ActionResult(
            success=True,
            message="예약이 취소되었습니다.",
            data={"cancelled_id": "res_789"},
        )
        assert result.success is True
