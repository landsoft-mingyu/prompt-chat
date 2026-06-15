from fastapi import Depends, Request
from sqlalchemy import Engine

from app.adapters.db.base import IDBClient  # 추가
from app.adapters.db.cubrid import CubridClient
from app.interfaces.health_repository import IHealthRepository
from app.repositories.health_repository import HealthRepository
from app.services.health_service import HealthService


def get_db_engine(request: Request) -> Engine:
    return request.app.state.db_engine


def get_db_client(engine: Engine = Depends(get_db_engine)) -> IDBClient:  # 변경
    return CubridClient(engine)


def get_health_repository(
    client: IDBClient = Depends(get_db_client),  # 변경
) -> IHealthRepository:
    return HealthRepository(client)


def get_health_service(
    repository: IHealthRepository = Depends(get_health_repository),
) -> HealthService:
    return HealthService(repository)
