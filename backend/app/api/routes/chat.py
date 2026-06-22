"""통합 챗봇 엔드포인트."""

from fastapi import APIRouter, Depends

from app.dependencies import get_chat_orchestrator
from app.schemas.chat import ChatRequest
from app.schemas.orchestrator import OrchestratorResponse
from app.services.chat.chat_orchestrator import ChatOrchestrator

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post(
    "/chat",
    response_model=OrchestratorResponse,
    summary="통합 챗봇",
    description="사용자 자연어 입력을 받아 의도 분류 → RAG 검색 또는 예약 흐름을 처리합니다.",
)
async def chat(
    request: ChatRequest,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
) -> OrchestratorResponse:
    """POST /api/v1/chat — 메인 챗봇 엔드포인트."""
    return await orchestrator.handle(request)
