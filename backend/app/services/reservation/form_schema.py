"""예약 폼 스키마 생성 서비스.

외부 예약 API의 상세/회차 응답을 프론트 ReservationForm이 소비하는
공통 FormSchema 딕셔너리로 정규화한다.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.adapters.interfaces.reservation_api_client import IReservationApiClient
from app.repositories.interfaces.reservation_form_service import IReservationFormService

_MAX_DATE_OPTIONS = 60
_MAX_PART_OPTIONS = 500
_KST = timezone(timedelta(hours=9))


class ReservationFormService(IReservationFormService):
    """예약 상세/회차 응답을 폼 스키마로 조립한다."""

    def __init__(self, api_client: IReservationApiClient) -> None:
        self._api = api_client

    async def build_form_schema(self, res_idx: str) -> dict[str, Any] | None:
        """예약 프로그램 ID로 폼 스키마 생성."""
        detail_response = await self._api.get_program_detail(res_idx)
        detail = _unwrap_detail(detail_response)
        if not detail:
            return None

        date_options = _extract_available_dates(detail_response, detail)
        if not date_options:
            date_options = _fallback_date_options(detail)

        part_options = await self._fetch_part_options(res_idx, date_options)
        if part_options:
            date_options = sorted(
                {
                    part_date
                    for part in part_options
                    if (part_date := _part_date_iso(part))
                }
            )

        fields = _base_fields(detail)
        if _get(detail, "resGroupGubun", "res_group_gubun") == "Y":
            fields.extend(_group_fields())

        schema: dict[str, Any] = {
            "res_idx": res_idx,
            "fields": fields,
            "address_required": _get(detail, "addressUseYn", "address_use_yn") == "Y",
            "id_verifi_required": _get(detail, "idVerifiYn", "id_verifi_yn") == "Y",
            "date_options": date_options[:_MAX_DATE_OPTIONS],
            "part_options": part_options[:_MAX_PART_OPTIONS],
        }

        _add_extra_fields(schema, detail)
        return schema

    async def _fetch_part_options(
        self,
        res_idx: str,
        date_options: list[str],
    ) -> list[dict[str, Any]]:
        """날짜별 회차를 조회해 폼 옵션으로 정규화."""
        if not date_options:
            return []

        tasks = [
            self._safe_get_parts(res_idx, target_date)
            for target_date in date_options[:_MAX_DATE_OPTIONS]
        ]
        responses = await asyncio.gather(*tasks)

        parts: list[dict[str, Any]] = []
        for response in responses:
            for part in _unwrap_parts(response):
                normalized = _normalize_part(part)
                if normalized:
                    parts.append(normalized)

        parts.sort(
            key=lambda p: (
                str(p.get("res_part_date") or ""),
                int(p.get("res_part") or 0),
                str(p.get("res_part_start_time") or ""),
            )
        )
        return parts

    async def _safe_get_parts(self, res_idx: str, target_date: str) -> dict[str, Any]:
        try:
            return await self._api.get_parts(res_idx, target_date)
        except Exception:
            return {"parts": []}


def _unwrap_detail(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data", response)
    return data if isinstance(data, dict) else {}


def _unwrap_parts(response: dict[str, Any]) -> list[dict[str, Any]]:
    raw = response.get("parts", response.get("data", []))
    return raw if isinstance(raw, list) else []


def _get(source: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        return (
            datetime.fromtimestamp(value / 1000, tz=timezone.utc)
            .astimezone(_KST)
            .date()
        )
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _extract_available_dates(
    response: dict[str, Any],
    detail: dict[str, Any],
) -> list[str]:
    today = date.today()
    raw_dates = response.get("availableDates") or detail.get("availableDates") or []
    if not isinstance(raw_dates, list):
        return []

    dates = []
    for raw in raw_dates:
        parsed = _to_date(raw)
        if parsed and parsed >= today:
            dates.append(parsed.isoformat())
    return sorted(set(dates))


def _fallback_date_options(detail: dict[str, Any]) -> list[str]:
    today = date.today()
    start = _to_date(_get(detail, "resStartDt", "res_start_dt")) or today
    end = _to_date(_get(detail, "resEndDt", "res_end_dt")) or (
        today + timedelta(days=90)
    )
    start = max(start, today)
    end = min(end, today + timedelta(days=90))

    day_gubun = _get(detail, "resDayGubun", "res_day_gubun", default="D")
    dates: list[str] = []
    current = start
    while current <= end and len(dates) < _MAX_DATE_OPTIONS:
        if day_gubun == "W" and current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates


def _base_fields(detail: dict[str, Any]) -> list[dict[str, Any]]:
    min_count = _to_int(_get(detail, "resUserMinCnt", "res_user_min_cnt"), 1)
    max_count = _to_int(_get(detail, "resUserMaxCnt", "res_user_max_cnt"), min_count)
    return [
        {"name": "name", "label": "대표자 이름", "type": "text", "required": True},
        {"name": "mobile", "label": "휴대전화", "type": "tel", "required": True},
        {"name": "email", "label": "이메일", "type": "email", "required": False},
        {
            "name": "user_count",
            "label": "인원",
            "type": "number",
            "required": True,
            "min": min_count,
            "max": max(max_count, min_count),
        },
    ]


def _group_fields() -> list[dict[str, Any]]:
    return [
        {
            "name": "group_name",
            "label": "학교(단체)명",
            "type": "text",
            "required": True,
        },
        {
            "name": "leader_name",
            "label": "인솔자 성명",
            "type": "text",
            "required": True,
        },
        {
            "name": "leader_phone",
            "label": "인솔자 연락처",
            "type": "tel",
            "required": True,
        },
    ]


def _add_extra_fields(schema: dict[str, Any], detail: dict[str, Any]) -> None:
    raw = _get(detail, "resFieldInfo", "res_field_info")
    if not raw:
        return
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        schema["extra_fields_raw"] = str(raw)[:1000]
        return

    if isinstance(parsed, list):
        schema["extra_fields"] = parsed
    elif isinstance(parsed, dict) and isinstance(parsed.get("fields"), list):
        schema["extra_fields"] = parsed["fields"]


def _normalize_part(part: dict[str, Any]) -> dict[str, Any] | None:
    pt_idx = _get(part, "ptIdx", "pt_idx")
    part_date = _part_date_iso(part)
    if not pt_idx or not part_date:
        return None

    return {
        **part,
        "pt_idx": pt_idx,
        "res_idx": _get(part, "resIdx", "res_idx"),
        "res_part": _get(part, "resPart", "res_part"),
        "res_part_date": part_date,
        "res_part_start_time": _get(part, "resPartStartTime", "res_part_start_time"),
        "res_part_end_time": _get(part, "resPartEndTime", "res_part_end_time"),
        "res_dl_yn": _get(part, "resDlYn", "res_dl_yn"),
        "res_dl_yn_msg": _get(part, "resDlYnMsg", "res_dl_yn_msg"),
    }


def _part_date_iso(part: dict[str, Any]) -> str | None:
    parsed = _to_date(_get(part, "resPartDate", "res_part_date"))
    return parsed.isoformat() if parsed else None
