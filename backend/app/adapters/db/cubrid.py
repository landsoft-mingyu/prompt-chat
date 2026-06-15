from sqlalchemy import text
from sqlalchemy import Engine

from app.adapters.db.base import IDBClient


class CubridClient(IDBClient):
    def __init__(self, engine: Engine):
        self.engine = engine

    def fetch_one_value(self, query: str) -> int:
        with self.engine.connect() as connection:
            result = connection.execute(text(query))
            return result.scalar_one()
