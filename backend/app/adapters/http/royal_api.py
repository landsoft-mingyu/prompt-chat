"""ROYAL 예약 시스템 HTTP API 클라이언트."""

import httpx

from app.adapters.interfaces.reservation_api_client import (
    IReservationApiClient,
)
from app.core.config import Settings
from app.core.exceptions import (
    DatabaseException,
    ValidationException,
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
        # base_url 뒤에 슬래시 없이 정규화
        self._base = settings.royal_api_base_url.rstrip("/")

    def _url(self, suffix: str) -> str:
        """suffix를 base에 이어 붙여 완전한 URL 반환."""
        return f"{self._base}/{suffix.lstrip('/')}"

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        """공통 HTTP 요청 처리. url은 완전한 절대 URL."""
        try:
            response = await self.client.request(
                method,
                url,
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
            ct = e.response.headers.get("content-type", "")
            body = e.response.text if "json" in ct else f"HTTP {e.response.status_code}"
            if 400 <= e.response.status_code < 500:
                raise ValidationException(
                    f"요청 오류: {body}",
                    error_code="ROYAL_API_VALIDATION_ERROR",
                ) from e
            raise DatabaseException(
                f"ROYAL 서버 오류: {body}",
                error_code="ROYAL_API_SERVER_ERROR",
            ) from e
        except httpx.RequestError as e:
            raise DatabaseException(
                f"네트워크 오류: {str(e)}",
                error_code="ROYAL_API_NETWORK_ERROR",
            ) from e

    async def get_programs(self, group_code: str) -> dict:
        return await self._request(
            "GET", self._url("list"), params={"groupCode": group_code}
        )

    async def get_program_detail(self, res_idx: str) -> dict:
        return await self._request("GET", self._url("view"), params={"resIdx": res_idx})

    async def get_parts(self, res_idx: str, res_part_date: str) -> dict:
        return await self._request(
            "GET",
            self._url("parts"),
            params={"resIdx": res_idx, "resPartDate": res_part_date},
        )

    async def get_reservation(self, res_no: str, res_mobile: str) -> dict:
        return await self._request(
            "GET",
            self._url("myReservation"),
            params={"resNo": res_no, "resMobile": res_mobile},
        )

    async def create_reservation(self, payload: dict) -> dict:
        """예약 생성."""
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
            if payload.get("res_user_cnt") is not None
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

        # 필수 파라미터 검증
        required = [
            "resIdx",
            "ptIdx",
            "groupCode",
            "resGubun",
            "resGroupGubun",
            "resDate",
            "resName",
            "resMobile",
            "resUserCnt",
            "resPriPolicyYn",
        ]
        missing = [k for k in required if k not in api_payload]
        if missing:
            raise DatabaseException(
                f"필수 파라미터 누락: {', '.join(missing)}",
                error_code="ROYAL_API_INVALID_PARAMS",
            )

        return await self._request("POST", self._url("insert"), json=api_payload)

    async def cancel_reservation(
        self, res_no: str, res_mobile: str, reason: str | None = None
    ) -> dict:
        """예약 취소."""
        api_payload: dict = {"resNo": res_no, "resMobile": res_mobile}
        if reason:
            api_payload["reason"] = reason
        return await self._request("POST", self._url("cancel"), json=api_payload)
