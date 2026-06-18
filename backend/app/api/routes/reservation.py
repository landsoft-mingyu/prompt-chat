"""예약 관련 API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_royal_api
from app.repositories.interfaces.reservation_api_client import (
    IReservationApiClient,
)
from app.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCancelResponse,
    ReservationCreateRequest,
    ReservationCreateResponse,
)

router = APIRouter(prefix="/api/v1/reservations", tags=["reservations"])


@router.get("/programs")
async def list_programs(
    group_code: str = Query(
        ...,
        description="궁능 코드 (gbg/cdg/cgg/jms/dsg/rtm)",
    ),
    api_client: IReservationApiClient = Depends(get_royal_api),
) -> dict:
    """예약 가능한 프로그램 목록 조회 (ROYAL API 경유)."""
    return await api_client.get_programs(group_code)


@router.get("/parts")
async def list_parts(
    res_idx: str = Query(..., description="예약 프로그램 ID"),
    res_part_date: str = Query(..., description="날짜 YYYY-MM-DD"),
    api_client: IReservationApiClient = Depends(get_royal_api),
) -> dict:
    """특정 프로그램의 예약 가능 회차 목록 조회 (ROYAL API 경유)."""
    return await api_client.get_parts(res_idx, res_part_date)


@router.get("/my-reservation")
async def get_my_reservation(
    res_no: str = Query(..., description="예약 번호"),
    res_mobile: str = Query(..., description="휴대폰 번호"),
    api_client: IReservationApiClient = Depends(get_royal_api),
) -> dict:
    """예약 조회 (ROYAL API 경유)."""
    reservation = await api_client.get_reservation(res_no, res_mobile)
    if not reservation:
        raise HTTPException(status_code=404, detail="예약을 찾을 수 없습니다")
    return reservation


@router.post("/create", response_model=ReservationCreateResponse)
async def create_reservation(
    req: ReservationCreateRequest,
    api_client: IReservationApiClient = Depends(get_royal_api),
) -> ReservationCreateResponse:
    """예약 생성 (ROYAL API 경유)."""
    result = await api_client.create_reservation(req.model_dump())
    return ReservationCreateResponse(**result)


@router.post("/cancel", response_model=ReservationCancelResponse)
async def cancel_reservation(
    req: ReservationCancelRequest,
    api_client: IReservationApiClient = Depends(get_royal_api),
) -> ReservationCancelResponse:
    """예약 취소 (본인 확인: res_no + res_mobile, ROYAL API 경유)."""
    result = await api_client.cancel_reservation(req.res_no, req.res_mobile)
    return ReservationCancelResponse(**result)
