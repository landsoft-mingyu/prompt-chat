"""Chat orchestration endpoint used by the published static frontend."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.config import Settings
from app.dependencies import (
    get_app_settings,
    get_reservation_repository,
)
from app.repositories.interfaces.reservation_repository import ReservationRepository
from app.repositories.milvus.vector_repository import MilvusVectorRepository
from app.services.rag.embedding_client import EmbeddingClient
from app.services.rag.rag_search_service import RAGSearchService

router = APIRouter(prefix="/api/v1/chatbot", tags=["chatbot"])


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _is_reservation_intent(message: str, branch: str | None) -> bool:
    if branch == "reservation":
        return True
    keywords = ("예약", "통합예약", "회차", "신청", "취소", "예약번호", "프로그램")
    return any(keyword in message for keyword in keywords)


def _program_title(item: dict[str, Any]) -> str:
    return str(
        item.get("res_title")
        or item.get("resTitle")
        or item.get("vw_title")
        or item.get("vwTitle")
        or "예약 프로그램"
    )


def _program_id(item: dict[str, Any]) -> str:
    return str(item.get("res_idx") or item.get("resIdx") or "")


def _reservation_payload(items: list[dict[str, Any]], message: str) -> dict[str, Any]:
    lines = ["예약 가능한 프로그램 목록입니다:", ""]
    for item in items[:8]:
        lines.append(f"• [{_program_id(item)}] {_program_title(item)}")

    return {
        "reply": "\n".join(lines)
        if items
        else "현재 예약 가능한 프로그램을 찾지 못했습니다.",
        "branch": "reservation",
        "next_action": "ANSWER",
        "candidates": [],
        "sources": [],
        "images": [],
        "placeholder": "원하시는 예약 업무를 질문해 주세요.",
        "panel": {"step": "list", "items": items},
        "structured": {
            "mode": "reservation_list",
            "query": message,
            "count": len(items),
        },
    }


def _rag_payload(message: str, results: list[Any]) -> dict[str, Any]:
    if not results:
        reply = "관련 내용을 찾지 못했습니다. 궁능, 관람, 예약과 관련된 질문을 조금 더 구체적으로 입력해 주세요."
        sources = []
    else:
        top = results[:3]
        lines = ["의미 검색 결과를 기준으로 안내드립니다:", ""]
        sources = []
        for index, result in enumerate(top, start=1):
            title = (
                result.get("title")
                if isinstance(result, dict)
                else getattr(result, "title", None)
            ) or "자료"
            content = (
                result.get("content")
                if isinstance(result, dict)
                else getattr(result, "content", None)
            ) or ""
            lines.append(f"{index}. {title}")
            if content:
                lines.append(str(content)[:220])
            sources.append(
                {
                    "title": title,
                    "content_type": (
                        result.get("source_type")
                        if isinstance(result, dict)
                        else getattr(result, "source_type", "")
                    ),
                    "score": (
                        result.get("score")
                        if isinstance(result, dict)
                        else getattr(result, "score", 0)
                    ),
                }
            )
        reply = "\n".join(lines)

    return {
        "reply": reply,
        "branch": "palace_intro",
        "next_action": "ANSWER",
        "candidates": [],
        "sources": sources,
        "images": [],
        "placeholder": "궁능 안내 챗봇에게 물어보기",
        "panel": None,
        "structured": {"mode": "rag_search", "query": message, "count": len(results)},
    }


@router.post("/chat/stream")
async def chat_stream(
    request: dict[str, Any],
    settings: Settings = Depends(get_app_settings),
    reservation_repo: ReservationRepository = Depends(get_reservation_repository),
) -> StreamingResponse:
    """Route chat requests to reservation lookup or semantic RAG search."""

    async def event_stream():
        message = str(request.get("message") or "").strip()
        branch = request.get("branch")

        try:
            if not message:
                payload = {
                    "reply": "질문을 입력해 주세요.",
                    "branch": branch,
                    "next_action": "ANSWER",
                    "candidates": [],
                    "sources": [],
                    "images": [],
                    "placeholder": "질문을 입력해주세요.",
                    "panel": None,
                    "structured": None,
                }
            elif _is_reservation_intent(message, branch):
                programs = await reservation_repo.find_programs(settings.site_code, {})
                payload = _reservation_payload(
                    [dict(item) for item in programs], message
                )
            else:
                rag_service = RAGSearchService(
                    vector_repo=MilvusVectorRepository(uri=settings.milvus_uri),
                    embedding_client=EmbeddingClient(base_url=settings.embedding_url),
                )
                results = await rag_service.search(
                    query=message,
                    top_k=5,
                    source_types=None,
                    site_code=settings.site_code,
                )
                payload = _rag_payload(message, results)

            yield _sse({"type": "done", "payload": payload})
        except Exception as exc:
            yield _sse(
                {"type": "error", "message": f"처리 중 오류가 발생했습니다: {exc}"}
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
