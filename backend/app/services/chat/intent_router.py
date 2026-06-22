"""의도 분류기 서비스."""

from app.repositories.interfaces.intent_router import IIntentRouter
from app.repositories.interfaces.llm_client import ILLMClient
from app.schemas.orchestrator import ChatIntent, IntentRouterResult

# ── 시스템 프롬프트 ────────────────────────────────────────────

_SYSTEM_TEMPLATE = """당신은 궁능 예약 챗봇의 의도 분류기입니다.
사용자 메시지를 분석하여 아래 의도 중 하나로 분류하고 JSON으로 응답하세요.

[사이트: {site_code}]
[현재 세션 상태]
- 진행 중인 의도: {current_intent}
- 수집된 슬롯: {current_slots}

[의도 목록]
- rag_search: 일반 정보 검색 (관람 시간, 입장료, 위치 등)
- reservation_list: 예약 가능한 프로그램 목록 조회
- reservation_parts: 특정 프로그램의 회차 목록 조회
- reservation_create: 예약 생성 요청
- reservation_query: 예약 조회 요청
- reservation_cancel: 예약 취소 요청
- reservation_continue: 현재 진행 중인 예약 흐름 유지 (예약 진행 중 슬롯 답변)

[중요 규칙]
- 예약이 진행 중(current_intent가 reservation_create/query/cancel)이고
  사용자가 슬롯 정보를 입력하거나 예약 흐름에 관련된 답변을 하면 reservation_continue 반환
- 예약이 진행 중이더라도 명확히 다른 의도(정보 검색 등)를 표현하면 해당 의도 반환

[응답 형식]
{{
  "intent": "<의도 문자열>",
  "confidence": <0.0~1.0>,
  "extracted_slots": {{<추출된 슬롯 키-값, 없으면 빈 객체>}}
}}"""


class LLMIntentRouter(IIntentRouter):
    """LLM 기반 의도 분류기."""

    def __init__(self, llm_client: ILLMClient) -> None:
        self._llm = llm_client

    async def classify(
        self,
        message: str,
        session_context: dict,
        site_code: str,
    ) -> IntentRouterResult:
        """사용자 메시지를 의도로 분류."""
        system_prompt = _SYSTEM_TEMPLATE.format(
            site_code=site_code,
            current_intent=session_context.get("current_intent", "없음"),
            current_slots=session_context.get("slots", {}),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        try:
            result = await self._llm.chat_json(
                messages,
                response_schema=IntentRouterResult,
                temperature=0.0,
            )
            return result  # type: ignore[return-value]
        except Exception:
            # 파싱 실패 시 기본값으로 rag_search 반환
            return IntentRouterResult(
                intent=ChatIntent.RAG_SEARCH,
                confidence=0.5,
                extracted_slots={},
            )
