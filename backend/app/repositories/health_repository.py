from fastapi.concurrency import run_in_threadpool

from app.adapters.db.base import IDBClient
from app.interfaces.health_repository import IHealthRepository


class HealthRepository(IHealthRepository):
    def __init__(self, db_client: IDBClient):
        self.db_client = db_client

    async def select_one(self) -> int:
        # pycubrid는 sync 드라이버이므로 threadpool에서 실행
        return await run_in_threadpool(
            self.db_client.fetch_one_value, "SELECT 1 FROM db_root"
        )
