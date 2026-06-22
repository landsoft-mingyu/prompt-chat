"""예약 폼 스키마 생성 서비스 인터페이스."""

from abc import ABC, abstractmethod
from typing import Any


class IReservationFormService(ABC):
    """예약 상세/회차 데이터를 프론트 폼 스키마로 변환한다."""

    @abstractmethod
    async def build_form_schema(self, res_idx: str) -> dict[str, Any] | None:
        """예약 프로그램 ID로 폼 스키마를 생성한다."""
        ...
