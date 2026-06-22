"""ChatOrchestrator — 전체 흐름 조율 최상위 서비스."""

from app.repositories.interfaces.chat_orchestrator import IChatOrchestrator
from app.repositories.interfaces.intent_router import IIntentRouter
from app.repositories.interfaces.llm_client import ILLMClient
from app.repositories.interfaces.rag_search_service import IRAGSearchService
from app.repositories.interfaces.reservation_orchestrator import (
    IReservationOrchestrator,
)
from app.repositories.interfaces.session_store import SessionStore
from app.schemas.chat import ChatRequest
from app.schemas.orchestrator import (
    ChatIntent,
    OrchestratorResponse,
    SlotFillingState,
    SlotState,
)

_RAG_ANSWER_SYSTEM = """당신은 궁능 예약 안내 챗봇입니다.
아래 검색 결과를 바탕으로 사용자 질문에 친절하게 답해주세요.
검색 결과에 없는 내용은 추측하지 말고 "정확한 정보를 찾지 못했습니다"라고 답하세요.

[검색 결과]
{context}"""


class ChatOrchestrator(IChatOrchestrator):
    """사용자 쿼리를 받아 의도 분류 → 흐름 처리 → 응답 반환.

    1. Redis에서 세션 컨텍스트 로드
    2. IntentRouter로 의도 분류
    3. 의도별 분기 처리
    4. Redis 세션 업데이트
    5. OrchestratorResponse 반환
    """

    def __init__(
        self,
        intent_router: IIntentRouter,
        rag_service: IRAGSearchService,
        reservation_orchestrator: IReservationOrchestrator,
        session_store: SessionStore,
        llm_client: ILLMClient,
    ) -> None:
        self._intent_router = intent_router
        self._rag = rag_service
        self._reservation = reservation_orchestrator
        self._store = session_store
        self._llm = llm_client

    async def handle(self, request: ChatRequest) -> OrchestratorResponse:
        """메인 처리 흐름."""
        session_id = request.session_id
        message = request.message
        site_code = request.site_code

        # 1. Redis에서 세션 및 슬롯 상태 로드
        session_ctx = await self._store.get_session(session_id) or {}
        slot_state = await self._store.get_slot_state(session_id)

        # 2. 의도 분류
        router_result = await self._intent_router.classify(
            message=message,
            session_context={
                "current_intent": session_ctx.get("current_intent"),
                "slots": slot_state.slots if slot_state else {},
            },
            site_code=site_code,
        )
        intent = router_result.intent

        # 3. 의도별 분기
        if intent == ChatIntent.RESERVATION_CONTINUE:
            response = await self._handle_continue(
                message, session_id, site_code, slot_state
            )
        elif intent == ChatIntent.RAG_SEARCH:
            response = await self._handle_rag(message, session_id, site_code)
        elif intent == ChatIntent.RESERVATION_LIST:
            group_code = router_result.extracted_slots.get("group_code")
            response = await self._reservation.list_programs(
                session_id, site_code, group_code
            )
        elif intent == ChatIntent.RESERVATION_PARTS:
            res_idx = router_result.extracted_slots.get("res_idx", "").strip()
            res_part_date = router_result.extracted_slots.get("res_date", "").strip()
            if not res_idx:
                response = OrchestratorResponse(
                    session_id=session_id,
                    message="어떤 프로그램의 회차를 조회하시겠어요? 프로그램 번호(res_idx)를 알려주세요.\n먼저 '예약 가능한 프로그램 보여줘'라고 하시면 목록을 안내해드릴게요.",
                    intent=intent.value,
                    mode="reservation",
                )
            elif not res_part_date:
                response = OrchestratorResponse(
                    session_id=session_id,
                    message="관람 희망 날짜를 알려주세요. (예: 2026-07-15)",
                    intent=intent.value,
                    mode="reservation",
                )
            else:
                response = await self._reservation.list_parts(
                    session_id, res_idx, res_part_date
                )
        elif intent in (
            ChatIntent.RESERVATION_CREATE,
            ChatIntent.RESERVATION_QUERY,
            ChatIntent.RESERVATION_CANCEL,
        ):
            # 신규 예약 흐름 시작 — 빈 슬롯 상태 생성, 추출된 슬롯 seed
            if slot_state is None or slot_state.intent != intent:
                slot_state = SlotFillingState(
                    intent=intent,
                    slots=router_result.extracted_slots,
                    state=SlotState.COLLECTING,
                )
                # Fix: 신규 상태를 즉시 Redis에 저장 (reservation.handle() 이전 crash 시 소실 방지)
                await self._store.save_slot_state(session_id, slot_state)
            else:
                # 기존 슬롯에 신규 추출 병합
                for k, v in router_result.extracted_slots.items():
                    if v and not slot_state.slots.get(k):
                        slot_state.slots[k] = v

            response = await self._reservation.handle(
                intent=intent,
                message=message,
                session_id=session_id,
                site_code=site_code,
                slot_state=slot_state,
            )
        else:
            response = OrchestratorResponse(
                session_id=session_id,
                message="무엇을 도와드릴까요?",
                intent=intent.value,
                mode="chat",
            )

        # 4. 세션 메타 업데이트
        # RESERVATION_CONTINUE 시 현재 진행 중인 실제 의도를 저장 (라우팅 의도가 아님)
        actual_intent = (
            slot_state.intent.value
            if intent == ChatIntent.RESERVATION_CONTINUE and slot_state is not None
            else intent.value
        )
        await self._store.set_session(
            session_id,
            {"current_intent": actual_intent},
        )

        return response

    async def _handle_rag(
        self,
        message: str,
        session_id: str,
        site_code: str,
    ) -> OrchestratorResponse:
        """RAG 검색 + LLM 답변 생성."""
        try:
            results = await self._rag.search(
                query=message,
                site_code=site_code,
            )
            answer = await self._generate_rag_answer(message, results)
        except Exception as exc:
            answer = f"검색 중 오류가 발생했습니다: {exc}"
            results = []

        sources = (
            [
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score"),
                }
                for r in results
            ]
            if results
            else None
        )

        return OrchestratorResponse(
            session_id=session_id,
            message=answer,
            intent=ChatIntent.RAG_SEARCH.value,
            mode="rag",
            sources=sources,
        )

    async def _handle_continue(
        self,
        message: str,
        session_id: str,
        site_code: str,
        slot_state: SlotFillingState | None,
    ) -> OrchestratorResponse:
        """진행 중인 예약 흐름 재진입.

        Redis에 SlotFillingState가 없으면 RAG 폴백.
        """
        if slot_state is None:
            return await self._handle_rag(message, session_id, site_code)

        return await self._reservation.handle(
            intent=slot_state.intent,
            message=message,
            session_id=session_id,
            site_code=site_code,
            slot_state=slot_state,
        )

    async def _generate_rag_answer(
        self,
        query: str,
        search_results: list[dict],
    ) -> str:
        """검색 결과를 컨텍스트로 LLM 답변 생성."""
        if not search_results:
            return "관련 정보를 찾지 못했습니다. 다른 방식으로 질문해 주시겠어요?"

        context_lines = []
        for r in search_results:
            title = r.get("title", "")
            content = r.get("content", "")
            context_lines.append(f"[{title}]\n{content}")
        context = "\n\n".join(context_lines)

        messages = [
            {
                "role": "system",
                "content": _RAG_ANSWER_SYSTEM.format(context=context),
            },
            {"role": "user", "content": query},
        ]
        return await self._llm.chat(messages, temperature=0.3, max_tokens=1024)
