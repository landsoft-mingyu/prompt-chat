"""Health check 엔드포인트."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import get_health_service
from app.schemas.health import DBHealthResponse, HealthResponse
from app.services.health_service import HealthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check(service: HealthService = Depends(get_health_service)):
    """API 서버 상태 확인."""
    return await service.check_api()


@router.get(
    "/db",
    response_model=DBHealthResponse,
    responses={503: {"description": "DB unavailable"}},
)
async def db_health_check(service: HealthService = Depends(get_health_service)):
    """데이터베이스 연결 확인."""
    try:
        return await service.check_db()
    except SQLAlchemyError as e:
        logger.warning("DB connection failed", exc_info=True)
        raise HTTPException(status_code=503, detail="DB unavailable") from e
    except Exception as e:
        logger.exception("Unexpected error in db_health_check")
        raise HTTPException(status_code=500, detail="Internal server error") from e
