from fastapi import Depends, Request
from sqlalchemy import Engine

from app.adapters.db.base import IDBClient
from app.adapters.db.cubrid import CubridClient
from app.adapters.http.royal_api import RoyalApi
from app.core.config import Settings, get_settings
from app.interfaces.health_repository import IHealthRepository
from app.repositories.cubrid.reservation_repository import RoyalReservationRepository
from app.repositories.health_repository import HealthRepository
from app.services.health_service import HealthService


def get_app_settings() -> Settings:
    """설정 객체 반환 (get_settings()는 내부에서 @lru_cache 처리)."""
    return get_settings()


def get_db_engine(request: Request) -> Engine:
    """request.app.state에서 DB engine 반환."""
    return request.app.state.db_engine


def get_db_client(engine: Engine = Depends(get_db_engine)) -> IDBClient:
    """CubridClient 인스턴스 생성."""
    return CubridClient(engine)


def get_health_repository(
    client: IDBClient = Depends(get_db_client),
) -> IHealthRepository:
    """HealthRepository 인스턴스 생성."""
    return HealthRepository(client)


def get_health_service(
    repository: IHealthRepository = Depends(get_health_repository),
) -> HealthService:
    """HealthService 인스턴스 생성."""
    return HealthService(repository)


def get_reservation_repository(
    settings: Settings = Depends(get_app_settings),
) -> RoyalReservationRepository:
    """RoyalReservationRepository 인스턴스 생성."""
    return RoyalReservationRepository(settings)


def get_royal_api(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> RoyalApi:
    """RoyalApi 인스턴스 생성 (app.state의 싱글톤 httpx.AsyncClient 사용)."""
    client = request.app.state.royal_api_client
    return RoyalApi(client, settings)
