"""FastAPI 애플리케이션 생성 및 설정."""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from app.api.routes.health import router as health_router
from app.api.routes.reservation import router as reservation_router
from app.core.config import get_settings
from app.core.exceptions import (
    DatabaseException,
    PromptChatException,
    ValidationException,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 리소스 관리."""
    settings = get_settings()

    # 시작: DB engine 생성
    app.state.db_engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    # 시작: ROYAL API HTTP 클라이언트 생성
    app.state.royal_api_client = httpx.AsyncClient(
        base_url=settings.royal_api_base_url,
        timeout=httpx.Timeout(settings.royal_api_timeout_sec),
        verify=False,
    )

    yield

    # 종료: DB engine 정리
    app.state.db_engine.dispose()

    # 종료: HTTP 클라이언트 정리
    await app.state.royal_api_client.aclose()


# FastAPI 앱 생성
app = FastAPI(
    title="Prompt Homepage API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 미들웨어
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 예외 처리
@app.exception_handler(DatabaseException)
async def database_exception_handler(_request, exc: DatabaseException):
    """DatabaseException 처리 (503 Service Unavailable)."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=503,
        content={"detail": exc.message, "error_code": exc.error_code},
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(_request, exc: ValidationException):
    """ValidationException 처리 (400 Bad Request)."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "error_code": exc.error_code},
    )


@app.exception_handler(PromptChatException)
async def prompt_chat_exception_handler(_request, exc: PromptChatException):
    """PromptChatException 처리 (500 Internal Server Error, fallback)."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content={"detail": exc.message, "error_code": exc.error_code},
    )


# 라우터 등록
app.include_router(health_router)
app.include_router(reservation_router)
