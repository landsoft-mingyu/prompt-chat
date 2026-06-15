from abc import ABC, abstractmethod


class IDBClient(ABC):
    @abstractmethod
    def fetch_one_value(self, query: str) -> int: ...
