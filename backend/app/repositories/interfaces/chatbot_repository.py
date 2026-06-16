"""챗봇 저장소 인터페이스."""

from abc import ABC, abstractmethod
from typing import Any

# ──────────────────────────────────────────────
# ChatbotRepository 인터페이스
# ──────────────────────────────────────────────


class ChatbotRepository(ABC):
    """챗봇 저장소 추상 클래스.

    기존 챗봇 지식(tcb_*) 조회 담당. LLM IntentRouter 보조 지식 소스로 사용.
    """

    @abstractmethod
    async def search_intents(
        self,
        message: str,  # 사용자 입력 메시지
    ) -> list[dict[str, Any]]:
        """유사 의도 후보 검색 (IntentRouter 보조용)."""
        ...

    @abstractmethod
    async def find_entity_by_id(
        self,
        entity_id: str,  # 엔티티 고유 식별자
    ) -> dict[str, Any] | None:
        """단일 엔티티 조회. tcb_entity 기준. 없으면 None 반환."""
        ...

    @abstractmethod
    async def find_synonyms(
        self,
        keyword: str,  # 검색 키워드
    ) -> list[str]:
        """동의어 목록 반환 (쿼리 확장용)."""
        ...

    @abstractmethod
    async def find_faq_documents(
        self,
        site_code: str,  # 사이트 구분
    ) -> list[dict[str, Any]]:
        """FAQ 전체 조회. tcb_entity 기준. RAG 임베딩 소스용."""
        ...
