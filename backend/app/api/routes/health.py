from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_health_service
from app.schemas.health import DBHealthResponse, HealthResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check(service: HealthService = Depends(get_health_service)):
    return await service.check_api()


@router.get(
    "/db",
    response_model=DBHealthResponse,
    responses={503: {"description": "DB unavailable"}},
)
async def db_health_check(service: HealthService = Depends(get_health_service)):
    try:
        return await service.check_db()
    except Exception:
        raise HTTPException(status_code=503, detail="DB unavailable")
