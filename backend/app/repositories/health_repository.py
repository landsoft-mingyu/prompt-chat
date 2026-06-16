from fastapi.concurrency import run_in_threadpool

from app.adapters.db.base import IDBClient
from app.interfaces.health_repository import IHealthRepository


class HealthRepository(IHealthRepository):
    def __init__(self, db_client: IDBClient):
        self.db_client = db_client

    async def select_one(self) -> int:
        return await run_in_threadpool(
            self.db_client.fetch_one_value, "SELECT 1 FROM db_root"
        )
