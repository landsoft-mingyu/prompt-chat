"""LLM 클라이언트 인터페이스."""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class ILLMClient(ABC):
    """LLM 호출 추상 인터페이스.

    vLLM, OpenAI, 기타 OpenAI-compatible 엔드포인트를 추상화한다.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        """메시지 목록을 받아 텍스트 응답 반환.

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
            temperature: 샘플링 온도 (0=결정론적)
            max_tokens: 최대 생성 토큰 수

        Returns:
            LLM이 생성한 텍스트 응답
        """
        ...

    @abstractmethod
    async def chat_json(
        self,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        """JSON 구조화 응답 반환.

        Args:
            messages: 대화 메시지 목록
            response_schema: 파싱할 Pydantic 모델 타입
            temperature: 샘플링 온도

        Returns:
            response_schema 타입으로 파싱된 응답 객체
        """
        ...
