"""RAG 검색 API 라우트."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_rag_search_service
from app.repositories.interfaces.rag_search_service import IRAGSearchService
from app.schemas.document import SourceType
from app.schemas.rag import RAGHealthResponse, RAGSearchRequest, RAGSearchResponse

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post(
    "/search",
    response_model=RAGSearchResponse,
    summary="RAG 검색",
    description="벡터 유사도 기반 검색",
)
async def search_rag(
    request: RAGSearchRequest,
    rag_service: IRAGSearchService = Depends(get_rag_search_service),
) -> RAGSearchResponse:
    """
    RAG 검색 엔드포인트.

    쿼리를 임베딩하고 벡터 DB에서 유사한 문서를 검색합니다.
    """
    try:
        # source_types 필터 검증 및 변환
        source_types = None
        if request.source_types:
            try:
                source_types = [SourceType(st) for st in request.source_types]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid source_type: {str(e)}",
                ) from e

        # 검색 실행
        results = await rag_service.search(
            query=request.query,
            top_k=request.top_k,
            source_types=source_types,
            site_code=request.site_code,
        )

        # 응답 구성
        return RAGSearchResponse(
            results=results,
            total_count=len(results),
            query=request.query,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 실패: {str(e)}",
        ) from e


@router.get(
    "/health",
    response_model=RAGHealthResponse,
    summary="RAG 헬스 체크",
    description="RAG 서비스의 상태를 확인합니다",
)
async def health_check(
    rag_service: IRAGSearchService = Depends(get_rag_search_service),
) -> RAGHealthResponse:
    """RAG 서비스 헬스 체크."""
    health = await rag_service.health()
    return RAGHealthResponse(**health)
