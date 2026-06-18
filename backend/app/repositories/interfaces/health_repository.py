from abc import ABC, abstractmethod


class IHealthRepository(ABC):
    @abstractmethod
    async def select_one(self) -> int: ...
