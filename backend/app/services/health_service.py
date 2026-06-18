from app.repositories.interfaces.health_repository import IHealthRepository
from app.schemas.health import DBHealthResponse, HealthResponse


class HealthService:
    def __init__(self, repository: IHealthRepository):
        self.repository = repository

    async def check_api(self) -> HealthResponse:
        return HealthResponse(status="ok", service="prompt-homepage-api")

    async def check_db(self) -> DBHealthResponse:
        db_value = await self.repository.select_one()
        return DBHealthResponse(status="ok", db=db_value)
