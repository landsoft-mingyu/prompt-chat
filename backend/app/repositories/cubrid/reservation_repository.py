"""예약 저장소 구현체 — ROYAL 시스템 DB 프록시."""

import asyncio
from datetime import date
from typing import TypedDict

import pycubrid

from app.core.config import Settings
from app.repositories.interfaces.reservation_repository import ReservationRepository

# 상수
_DEFAULT_PARTS_LIMIT = 100
_RESERVATION_STATUS_PENDING = "N"
_RESERVATION_STATUS_CANCELLED = "X"


class InvalidInputError(ValueError):
    """입력 데이터 검증 실패."""

    pass


class ProgramInfo(TypedDict):
    """프로그램 정보."""

    res_idx: str
    res_title: str


class PartInfo(TypedDict):
    """회차 정보."""

    pt_idx: int
    res_idx: str
    res_part: int
    res_part_date: str
    res_part_start_time: str | None
    res_part_end_time: str | None


class ReservationInfo(TypedDict):
    """예약 정보."""

    res_no: str
    res_idx: str
    pt_idx: int
    res_status: str
    res_name: str
    res_mobile: str
    res_user_cnt: int
    res_date: str | None


class RoyalReservationRepository(ReservationRepository):
    """ROYAL 시스템 데이터베이스에서 예약 정보를 조회/관리하는 저장소."""

    def __init__(self, settings: Settings):
        """ROYAL DB 연결 정보를 설정에서 주입받음."""
        self.host = settings.royal_host
        self.port = settings.royal_port
        self.db = settings.royal_db
        self.user = settings.royal_user
        self.password = settings.royal_password

    def _get_connection(self):
        """ROYAL DB 연결 획득."""
        return pycubrid.connect(
            host=self.host,
            port=self.port,
            database=self.db,
            user=self.user,
            password=self.password,
        )

    async def find_programs(
        self,
        site_code: str,
        filters: dict,
    ) -> list[ProgramInfo]:
        """예약 프로그램 목록 조회.

        TODO: ry_mng_reservation 테이블에 site_code 컬럼이 없어서 실제 필터링 미구현.
        site_code는 현재 무시되며, 필요 시 별도 테이블 조인이 필요.
        """

        def _execute():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT res_idx, res_title FROM ry_mng_reservation")
                    rows = cursor.fetchall()
                    if not rows:
                        return []
                    return [
                        ProgramInfo(res_idx=row[0], res_title=row[1]) for row in rows
                    ]
                finally:
                    cursor.close()
            finally:
                conn.close()

        return await asyncio.to_thread(_execute)

    async def find_available_parts(
        self,
        res_idx: str,
    ) -> list[PartInfo]:
        """특정 프로그램의 예약 가능 회차 목록 조회 (오늘 이후만).

        res_idx는 필수입니다. site_code 필터링은 미구현 상태입니다.
        """
        if not isinstance(res_idx, str) or not res_idx.strip():
            raise InvalidInputError("res_idx must be non-empty string")

        def _execute():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                try:
                    today = date.today()

                    cursor.execute(
                        """SELECT pt_idx, res_idx, res_part, res_part_date,
                                  res_part_start_time, res_part_end_time
                           FROM ry_mng_reservation_part
                           WHERE res_idx = ? AND res_part_date >= ?
                           ORDER BY res_part_date, res_part_start_time""",
                        (res_idx, today),
                    )

                    rows = cursor.fetchall()
                    if not rows:
                        return []

                    result = []
                    for row in rows:
                        pt_idx, _res_idx, res_part, dt, start_time, end_time = row
                        date_str = (
                            dt.strftime("%Y-%m-%d")
                            if hasattr(dt, "strftime")
                            else str(dt)
                        )
                        start_str = (
                            start_time.strftime("%H:%M")
                            if hasattr(start_time, "strftime")
                            else None
                        )
                        end_str = (
                            end_time.strftime("%H:%M")
                            if hasattr(end_time, "strftime")
                            else None
                        )

                        result.append(
                            PartInfo(
                                pt_idx=pt_idx,
                                res_idx=_res_idx,
                                res_part=res_part,
                                res_part_date=date_str,
                                res_part_start_time=start_str,
                                res_part_end_time=end_str,
                            )
                        )
                    return result
                finally:
                    cursor.close()
            finally:
                conn.close()

        return await asyncio.to_thread(_execute)

    async def count_reserved_users(self, pt_idx: int) -> int:
        """특정 회차의 예약 인원 조회."""
        if not isinstance(pt_idx, int) or pt_idx <= 0:
            raise InvalidInputError(f"pt_idx must be positive int, got {pt_idx}")

        def _execute():
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                try:
                    query = (
                        "SELECT COALESCE(SUM(res_user_cnt), 0) "
                        "FROM ry_reservation WHERE pt_idx = ?"
                    )
                    cursor.execute(query, (pt_idx,))
                    row = cursor.fetchone()
                    if not row:
                        raise RuntimeError("Unexpected: COUNT query returned no rows")
                    return row[0]
                finally:
                    cursor.close()
            finally:
                conn.close()

        return await asyncio.to_thread(_execute)
