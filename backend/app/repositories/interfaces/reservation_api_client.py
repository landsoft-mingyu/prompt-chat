"""예약 외부 API 클라이언트 인터페이스."""

from abc import ABC, abstractmethod


class IReservationApiClient(ABC):
    """예약 외부 API 클라이언트 인터페이스.

    어떤 사이트 API가 와도 이 인터페이스를 구현하면 routes가 동작한다.
    """

    @abstractmethod
    async def get_programs(self, group_code: str) -> dict:
        """예약 프로그램 목록 조회."""
        ...

    @abstractmethod
    async def get_program_detail(self, res_idx: str) -> dict:
        """예약 프로그램 상세 조회."""
        ...

    @abstractmethod
    async def get_parts(
        self,
        res_idx: str,
        res_part_date: str,
    ) -> dict:
        """예약 가능 회차 목록 조회."""
        ...

    @abstractmethod
    async def get_reservation(
        self,
        res_no: str,
        res_mobile: str,
    ) -> dict:
        """예약 단건 조회."""
        ...

    @abstractmethod
    async def create_reservation(self, payload: dict) -> dict:
        """예약 생성."""
        ...

    @abstractmethod
    async def cancel_reservation(
        self,
        res_no: str,
        res_mobile: str,
        reason: str | None = None,
    ) -> dict:
        """예약 취소."""
        ...
