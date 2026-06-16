"""Tests for Chat schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    ActionCard,
    ChatRequest,
    ChatResponse,
    Source,
)


class TestChatRequest:
    """ChatRequest 스키마 테스트."""

    def test_chat_request_valid(self):
        """ChatRequest 정상 생성."""
        req = ChatRequest(
            session_id="sess_123",
            site_code="ROYAL",
            message="예약하고 싶어요",
            user_id="user_456",
        )
        assert req.session_id == "sess_123"
        assert req.site_code == "ROYAL"
        assert req.message == "예약하고 싶어요"
        assert req.user_id == "user_456"

    def test_chat_request_defaults(self):
        """ChatRequest 기본값 확인."""
        req = ChatRequest(
            session_id="sess_789",
            site_code="ROYAL",
            message="안녕하세요",
        )
        assert req.user_id is None

    def test_chat_request_missing_site_code(self):
        """site_code 누락 → ValidationError."""
        with pytest.raises(ValidationError):
            ChatRequest(
                session_id="sess_123",
                message="test",
            )

    def test_chat_request_empty_session_id(self):
        """session_id 빈 문자열 → ValidationError."""
        with pytest.raises(ValidationError):
            ChatRequest(session_id="", message="test")

    def test_chat_request_empty_message(self):
        """message 빈 문자열 → ValidationError."""
        with pytest.raises(ValidationError):
            ChatRequest(session_id="sess_123", message="")

    def test_chat_request_message_too_long(self):
        """message 최대 길이 초과 → ValidationError."""
        with pytest.raises(ValidationError):
            ChatRequest(
                session_id="sess_123",
                message="x" * 2001,
            )

    def test_chat_request_extra_field_forbidden(self):
        """추가 필드 → ValidationError."""
        with pytest.raises(ValidationError):
            ChatRequest(
                session_id="sess_123",
                message="test",
                extra_field="not allowed",  # type: ignore
            )


class TestSource:
    """Source 스키마 테스트."""

    def test_source_valid(self):
        """Source 정상 생성."""
        source = Source(
            source_id="doc_123",
            source_type="notice",
            title="공지사항",
            url="https://example.com/notice/123",
        )
        assert source.source_id == "doc_123"
        assert source.source_type == "notice"
        assert source.title == "공지사항"
        assert source.url == "https://example.com/notice/123"

    def test_source_minimal(self):
        """Source 최소 필드."""
        source = Source(
            source_id="doc_456",
            source_type="page_content",
        )
        assert source.title is None
        assert source.url is None

    def test_source_invalid_source_type(self):
        """잘못된 source_type → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Source(
                source_id="doc_789",
                source_type="invalid_type",
            )
        assert "source_type" in str(exc_info.value)

    def test_source_extra_field_forbidden(self):
        """추가 필드 → ValidationError."""
        with pytest.raises(ValidationError):
            Source(
                source_id="doc_789",
                source_type="notice",
                extra_field="not allowed",  # type: ignore
            )


class TestActionCard:
    """ActionCard 스키마 테스트."""

    def test_action_card_valid(self):
        """ActionCard 정상 생성."""
        card = ActionCard(
            type="reservation_slot",
            title="예약 가능 시간",
            description="10시 - 12시",
            payload={"time": "10:00", "count": 5},
        )
        assert card.type == "reservation_slot"
        assert card.title == "예약 가능 시간"
        assert card.description == "10시 - 12시"
        assert card.payload["time"] == "10:00"

    def test_action_card_defaults(self):
        """ActionCard 기본값."""
        card = ActionCard(
            type="content",
            title="콘텐츠",
        )
        assert card.description is None
        assert card.payload == {}

    def test_action_card_empty_payload(self):
        """ActionCard 빈 payload."""
        card = ActionCard(
            type="confirm",
            title="확인",
            payload={},
        )
        assert card.payload == {}

    def test_action_card_extra_field_forbidden(self):
        """추가 필드 → ValidationError."""
        with pytest.raises(ValidationError):
            ActionCard(
                type="content",
                title="test",
                extra_field="not allowed",  # type: ignore
            )


class TestChatResponse:
    """ChatResponse 스키마 테스트."""

    def test_chat_response_valid(self):
        """ChatResponse 정상 생성."""
        response = ChatResponse(
            answer="예약 가능한 시간대입니다.",
            mode="rag",
            sources=[
                Source(
                    source_id="doc_123",
                    source_type="notice",
                    title="공지사항",
                )
            ],
            cards=[
                ActionCard(
                    type="reservation_slot",
                    title="예약 시간",
                    payload={"time": "10:00"},
                )
            ],
            required_slots=["date"],
        )
        assert response.answer == "예약 가능한 시간대입니다."
        assert response.mode == "rag"
        assert len(response.sources) == 1
        assert len(response.cards) == 1
        assert response.required_slots == ["date"]

    def test_chat_response_minimal(self):
        """ChatResponse 최소 필드."""
        response = ChatResponse(
            answer="안녕하세요",
            mode="general",
        )
        assert response.sources == []
        assert response.cards == []
        assert response.required_slots == []

    def test_chat_response_all_modes(self):
        """모든 ResponseMode 값 테스트."""
        modes = ["rag", "action", "clarification", "general"]
        for mode in modes:
            response = ChatResponse(
                answer="test",
                mode=mode,  # type: ignore
            )
            assert response.mode == mode

    def test_chat_response_extra_field_forbidden(self):
        """추가 필드 → ValidationError."""
        with pytest.raises(ValidationError):
            ChatResponse(
                answer="test",
                mode="general",
                extra_field="not allowed",  # type: ignore
            )


class TestChatResponseIntegration:
    """ChatResponse 통합 테스트."""

    def test_rag_response_with_sources(self):
        """RAG 모드: 출처 포함."""
        response = ChatResponse(
            answer="검색 결과입니다.",
            mode="rag",
            sources=[
                Source(
                    source_id="doc_1",
                    source_type="notice",
                    title="공지",
                    url="http://example.com/1",
                ),
                Source(
                    source_id="doc_2",
                    source_type="page_content",
                    title="페이지",
                    url="http://example.com/2",
                ),
            ],
        )
        assert response.mode == "rag"
        assert len(response.sources) == 2

    def test_action_response_with_cards(self):
        """Action 모드: 액션 카드 포함."""
        response = ChatResponse(
            answer="다음 중 선택하세요.",
            mode="action",
            cards=[
                ActionCard(
                    type="reservation_slot",
                    title="10:00 - 12:00",
                    payload={"slot": "morning"},
                ),
                ActionCard(
                    type="reservation_slot",
                    title="14:00 - 16:00",
                    payload={"slot": "afternoon"},
                ),
            ],
        )
        assert response.mode == "action"
        assert len(response.cards) == 2

    def test_clarification_response_with_slots(self):
        """Clarification 모드: 추가 정보 필요."""
        response = ChatResponse(
            answer="예약일을 알려주세요.",
            mode="clarification",
            required_slots=["date", "time", "party_size"],
        )
        assert response.mode == "clarification"
        assert len(response.required_slots) == 3
