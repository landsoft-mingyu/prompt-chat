"""예약 관련 API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.http.royal_api import RoyalApi
from app.dependencies import get_reservation_form_service, get_royal_api
from app.repositories.interfaces.reservation_form_service import IReservationFormService
from app.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCancelResponse,
    ReservationCreateRequest,
)

router = APIRouter(prefix="/api/v1/reservations", tags=["reservations"])


@router.get("/programs")
async def list_programs(
    group_code: str = Query(
        ...,
        description="궁능 코드 (gbg/cdg/cgg/jms/dsg/rtm)",
    ),
    royal_api: RoyalApi = Depends(get_royal_api),
) -> dict:
    """예약 가능한 프로그램 목록 조회 (ROYAL API 경유)."""
    return await royal_api.get_programs(group_code)


@router.get("/parts")
async def list_parts(
    res_idx: str = Query(..., description="예약 프로그램 ID"),
    res_part_date: str = Query(..., description="날짜 YYYY-MM-DD"),
    royal_api: RoyalApi = Depends(get_royal_api),
) -> dict:
    """특정 프로그램의 예약 가능 회차 목록 조회 (ROYAL API 경유)."""
    return await royal_api.get_parts(res_idx, res_part_date)


@router.get("/{res_idx}/form")
async def get_form_schema(
    res_idx: str,
    form_service: IReservationFormService = Depends(get_reservation_form_service),
) -> dict:
    """예약 신청 폼 스키마 조회."""
    schema = await form_service.build_form_schema(res_idx)
    if schema is None:
        raise HTTPException(status_code=404, detail="예약 프로그램을 찾을 수 없습니다")
    return schema


@router.get("/my-reservation")
async def get_my_reservation(
    res_no: str = Query(..., description="예약 번호"),
    res_mobile: str = Query(..., description="휴대폰 번호"),
    royal_api: RoyalApi = Depends(get_royal_api),
) -> dict:
    """예약 조회 (ROYAL API 경유)."""
    try:
        reservation = await royal_api.get_reservation(res_no, res_mobile)
        if not reservation:
            raise HTTPException(status_code=404, detail="예약을 찾을 수 없습니다")
        return reservation
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="예약 조회 서비스 일시적 오류")


@router.post("/create")
async def create_reservation(
    req: ReservationCreateRequest,
    royal_api: RoyalApi = Depends(get_royal_api),
):
    """예약 생성 (ROYAL API 경유)."""
    try:
        result = await royal_api.create_reservation(req.model_dump())
        # 응답에 예약 정보 포함
        return {
            **result,
            "data": {
                "resName": req.res_name,
                "resMobile": req.res_mobile,
                "resIdx": req.res_idx,
                "resDate": str(req.res_date),
                "note": "위의 정보로 /my-reservation에서 예약번호를 조회하세요",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/cancel")
async def cancel_reservation(
    req: ReservationCancelRequest,
    royal_api: RoyalApi = Depends(get_royal_api),
) -> ReservationCancelResponse:
    """예약 취소 (본인 확인: res_no + res_mobile, ROYAL API 경유)."""
    try:
        result = await royal_api.cancel_reservation(req.res_no, req.res_mobile)
        return ReservationCancelResponse(**result)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="예약 취소 서비스 일시적 오류")
