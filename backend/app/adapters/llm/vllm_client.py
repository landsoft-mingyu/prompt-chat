"""vLLM(OpenAI-compatible) HTTP 클라이언트 구현체."""

import json
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.exceptions import DatabaseException, ValidationException
from app.repositories.interfaces.llm_client import ILLMClient


class VLLMClient(ILLMClient):
    """vLLM 서버 HTTP 클라이언트.

    OpenAI /v1/chat/completions 엔드포인트를 사용한다.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        model: str,
        timeout_sec: int = 30,
    ) -> None:
        """
        Args:
            client: 싱글톤 httpx.AsyncClient (main.py에서 생성)
            model: 사용할 모델명 (예: gemma-3-12b)
            timeout_sec: 요청 타임아웃 (초)
        """
        self._client = client
        self._model = model
        self._timeout = timeout_sec

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        """텍스트 응답 반환."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = await self._post(payload)
        return data["choices"][0]["message"]["content"]

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        """JSON 구조화 응답 반환.

        시스템 프롬프트에 JSON 스키마를 삽입하고, 응답을 Pydantic으로 파싱한다.
        파싱 실패 시 ValidationException 발생.
        """
        schema_hint = json.dumps(
            response_schema.model_json_schema(), ensure_ascii=False
        )
        injected = list(messages)
        # 마지막 user 메시지 앞에 JSON 스키마 안내 추가
        injected.append(
            {
                "role": "user",
                "content": (
                    f"반드시 다음 JSON 스키마 형식으로만 응답하세요:\n{schema_hint}"
                ),
            }
        )

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": injected,
            "temperature": temperature,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
        }
        data = await self._post(payload)
        raw_text = data["choices"][0]["message"]["content"]

        try:
            return response_schema.model_validate_json(raw_text)
        except Exception as exc:
            raise ValidationException(
                f"LLM JSON 파싱 실패: {exc}",
                error_code="LLM_JSON_PARSE_ERROR",
            ) from exc

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """공통 HTTP 호출. 타임아웃·에러 처리 포함."""
        try:
            response = await self._client.post(
                "/chat/completions",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise DatabaseException(
                f"LLM 요청 타임아웃 (>= {self._timeout}초)",
                error_code="LLM_TIMEOUT",
            ) from exc
        except httpx.HTTPStatusError as exc:
            if 400 <= exc.response.status_code < 500:
                raise ValidationException(
                    f"LLM 요청 오류: {exc.response.text}",
                    error_code="LLM_REQUEST_ERROR",
                ) from exc
            raise DatabaseException(
                f"LLM 서버 오류: {exc.response.text}",
                error_code="LLM_SERVER_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise DatabaseException(
                f"LLM 네트워크 오류: {exc}",
                error_code="LLM_NETWORK_ERROR",
            ) from exc
