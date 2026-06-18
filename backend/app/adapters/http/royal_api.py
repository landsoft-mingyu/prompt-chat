"""ROYAL 예약 시스템 HTTP API 클라이언트."""

import httpx

from app.core.config import Settings
from app.core.exceptions import (
    DatabaseException,
    ValidationException,
)
from app.repositories.interfaces.reservation_api_client import (
    IReservationApiClient,
)


class RoyalApi(IReservationApiClient):
    """ROYAL 시스템 HTTP API 호출 어댑터."""

    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        """
        Args:
            client: 싱글톤 httpx.AsyncClient (main.py에서 생성)
            settings: 애플리케이션 설정 (base_url, timeout 등)
        """
        self.client = client
        self.settings = settings

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """공통 HTTP 요청 처리."""
        try:
            response = await self.client.request(
                method,
                path,
                timeout=self.settings.royal_api_timeout_sec,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise DatabaseException(
                f"ROYAL API 타임아웃 (>= {self.settings.royal_api_timeout_sec}초)",
                error_code="ROYAL_API_TIMEOUT",
            ) from e
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                raise ValidationException(
                    f"요청 오류: {e.response.text}",
                    error_code="ROYAL_API_VALIDATION_ERROR",
                ) from e
            raise DatabaseException(
                f"ROYAL 서버 오류: {e.response.text}",
                error_code="ROYAL_API_SERVER_ERROR",
            ) from e
        except httpx.RequestError as e:
            raise DatabaseException(
                f"네트워크 오류: {str(e)}",
                error_code="ROYAL_API_NETWORK_ERROR",
            ) from e

    async def get_programs(self, group_code: str) -> dict:
        """프로그램 목록 조회.

        GET {royal_api_base_url}/ROYAL/api/v1/res/list?groupCode=...
        """
        return await self._request(
            "GET",
            "/ROYAL/api/v1/res/list",
            params={"groupCode": group_code},
        )

    async def get_program_detail(self, res_idx: str) -> dict:
        """프로그램 상세 조회.

        GET {royal_api_base_url}/ROYAL/api/v1/res/view?resIdx=...
        """
        return await self._request(
            "GET",
            "/ROYAL/api/v1/res/view",
            params={"resIdx": res_idx},
        )

    async def get_parts(self, res_idx: str, res_part_date: str) -> dict:
        """회차 목록 조회.

        GET {royal_api_base_url}/ROYAL/api/v1/res/parts?resIdx=...&resPartDate=...
        """
        return await self._request(
            "GET",
            "/ROYAL/api/v1/res/parts",
            params={"resIdx": res_idx, "resPartDate": res_part_date},
        )

    async def get_reservation(self, res_no: str, res_mobile: str) -> dict:
        """예약 단건 조회.

        GET {royal_api_base_url}/ROYAL/api/v1/res/myReservation?resNo=...&resMobile=...
        """
        return await self._request(
            "GET",
            "/ROYAL/api/v1/res/myReservation",
            params={"resNo": res_no, "resMobile": res_mobile},
        )

    async def create_reservation(self, payload: dict) -> dict:
        """예약 생성.

        POST {royal_api_base_url}/ROYAL/api/v1/res/insert
        """
        # snake_case → camelCase 변환
        api_payload = {
            "resIdx": payload.get("res_idx"),
            "ptIdx": payload.get("pt_idx"),
            "groupCode": payload.get("group_code"),
            "resGubun": payload.get("res_gubun"),
            "resGroupGubun": payload.get("res_group_gubun"),
            "resDate": str(payload.get("res_date"))
            if payload.get("res_date")
            else None,
            "resName": payload.get("res_name"),
            "resMobile": payload.get("res_mobile"),
            "resUserCnt": str(payload.get("res_user_cnt"))
            if payload.get("res_user_cnt")
            else None,
            "resPriPolicyYn": payload.get("res_pri_policy_yn"),
            "resEml": payload.get("res_eml"),
            "resGroupNm": payload.get("res_group_nm"),
            "resFilmYn": payload.get("res_film_yn"),
            "resLeaderName": payload.get("res_leader_name"),
            "resLeaderMobile1": payload.get("res_leader_mobile1"),
            "resLeaderMobile2": payload.get("res_leader_mobile2"),
            "resLeaderMobile3": payload.get("res_leader_mobile3"),
        }
        # None 값 제외
        api_payload = {k: v for k, v in api_payload.items() if v is not None}

        return await self._request(
            "POST",
            "/ROYAL/api/v1/res/insert",
            json=api_payload,
        )

    async def cancel_reservation(
        self, res_no: str, res_mobile: str, reason: str | None = None
    ) -> dict:
        """예약 취소.

        POST {royal_api_base_url}/ROYAL/api/v1/res/cancel
        """
        # snake_case → camelCase 변환
        api_payload = {
            "resNo": res_no,
            "resMobile": res_mobile,
        }
        if reason:
            api_payload["reason"] = reason

        return await self._request(
            "POST",
            "/ROYAL/api/v1/res/cancel",
            json=api_payload,
        )
