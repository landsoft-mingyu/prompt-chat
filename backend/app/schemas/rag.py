"""RAG 검색 API 스키마."""

from typing import Any

from pydantic import BaseModel, Field


class RAGSearchRequest(BaseModel):
    """RAG 검색 요청."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="검색 쿼리",
        example="경복궁 관람 시간은?",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="상위 K개 결과 반환",
    )
    source_types: list[str] | None = Field(
        default=None,
        description="소스 타입 필터 (예: 'notice', 'page_content', 'location')",
        example=["notice", "page_content"],
    )
    site_code: str | None = Field(
        default=None,
        description="사이트 코드 필터 (예: 'ROYAL')",
    )


class RAGSearchResult(BaseModel):
    """RAG 검색 결과 항목."""

    id: str | int = Field(description="벡터 ID")
    title: str = Field(description="문서 제목")
    content: str = Field(description="문서 내용 (청크)")
    source_type: str = Field(description="출처 타입")
    source_table: str = Field(description="원본 테이블명")
    site_code: str = Field(description="사이트 코드")
    score: float = Field(description="유사도 점수")
    url: str | None = Field(default=None, description="원본 링크")
    metadata: dict[str, Any] = Field(default_factory=dict, description="부가정보")


class RAGSearchResponse(BaseModel):
    """RAG 검색 응답."""

    results: list[RAGSearchResult] = Field(description="검색 결과")
    total_count: int = Field(description="반환된 결과 개수")
    query: str = Field(description="검색에 사용된 쿼리")


class RAGHealthResponse(BaseModel):
    """RAG 헬스 체크 응답."""

    status: str = Field(description="상태 ('healthy' 또는 'unhealthy')")
    embedding_service: dict[str, Any] = Field(description="임베딩 서비스 상태")
