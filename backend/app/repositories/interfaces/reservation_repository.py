"""예약 저장소 인터페이스."""

from abc import ABC, abstractmethod
from typing import Any

# ──────────────────────────────────────────────
# ReservationRepository 인터페이스
# ──────────────────────────────────────────────


class ReservationRepository(ABC):
    """예약 저장소 추상 클래스. 예약 조회/생성/취소 담당. SQL은 모름 — 구현체만 앎."""

    @abstractmethod
    async def find_programs(
        self,
        site_code: str,  # 사이트 구분
        filters: dict[str, Any],  # 필터 조건 — keyword, group_code 등
    ) -> list[dict[str, Any]]:
        """예약 프로그램 목록 조회. ry_mng_reservation 테이블 기준."""
        ...

    @abstractmethod
    async def find_available_parts(
        self,
        res_idx: str,  # 예약 프로그램 ID (필수)
    ) -> list[dict[str, Any]]:
        """특정 프로그램의 예약 가능 회차 목록 조회 (오늘 이후만)."""
        ...

    @abstractmethod
    async def count_reserved_users(
        self,
        pt_idx: int,  # 회차 고유 식별자
    ) -> int:
        """특정 회차의 현재 예약 인원 수 조회. ry_reservation 기준."""
        ...
