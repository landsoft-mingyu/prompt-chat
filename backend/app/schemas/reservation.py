import re
from datetime import date, datetime, timezone
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ──────────────────────────────────────────────
# Enum 정의
# ──────────────────────────────────────────────


class ReservationStatus(str, Enum):
    """예약 상태 코드."""

    CONFIRMED = "Y"  # 예약 확정
    WAITING = "W"  # 대기
    PENDING = "N"  # 미처리
    CANCELLED = "X"  # 취소됨


class ReservationGubun(str, Enum):
    """예약 유형 구분."""

    INDIVIDUAL = "Y"  # 일반예약
    GROUP = "N"  # 선착순
    LOTTERY = "C"  # 추첨제


class ReservationGroupGubun(str, Enum):
    """단체 구분 코드."""

    YOUTH = "Y"  # 청소년 단체
    GENERAL = "N"  # 일반 단체


# ──────────────────────────────────────────────
# Mixin 클래스
# ──────────────────────────────────────────────


class MobileValidatorMixin(BaseModel):
    """휴대폰 번호 검증 mixin."""

    res_mobile: Annotated[
        str,
        Field(description="휴대폰 번호 (하이픈 필수, 010-xxxx-xxxx 형식)"),
    ]

    @field_validator("res_mobile", mode="before")
    @classmethod
    def validate_res_mobile(cls, v: Any) -> str:
        """휴대폰 번호 형식 검증 — 하이픈 포함 010-xxxx-xxxx."""
        if isinstance(v, str):
            if not re.match(r"^\d{3}-\d{3,4}-\d{4}$", v):
                raise ValueError(f"res_mobile must match 010-xxxx-xxxx, got {v!r}")
            return v
        raise TypeError(f"res_mobile must be str, got {type(v).__name__}")


# ──────────────────────────────────────────────
# ReservationPart 클래스
# ──────────────────────────────────────────────


class ReservationPart(BaseModel):
    """
    예약 프로그램 회차 정보.

    외부 API 응답 기준 — /ROYAL/api/v1/res/programs 응답의 회차별 데이터.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "pt_idx": 115717,
                    "res_idx": "202412120391",
                    "res_part": 6,
                    "res_part_date": 1739414400000,
                    "res_part_start_time": "14:00",
                    "res_part_end_time": "14:00",
                    "res_dl_yn": "N",
                    "res_user_cnt": 10,
                    "res_user_cnt_y": 5,
                    "res_dl_yn_msg": "예약 가능",
                }
            ]
        },
    )

    pt_idx: int  # 회차 ID
    res_idx: str  # 예약 프로그램 ID
    res_part: int  # 회차 번호
    res_part_date: date  # 예약 날짜 (timestamp ms → date 변환)
    res_part_start_time: str  # 시작 시간 "HH:MM"
    res_part_end_time: str  # 종료 시간 "HH:MM"
    res_dl_yn: str  # 마감 여부 "Y"/"N"
    res_user_cnt: int  # 예약 가능 인원
    res_user_cnt_y: int  # 확정 인원
    res_dl_yn_msg: str  # 마감 메시지

    @field_validator("res_part_date", mode="before")
    @classmethod
    def validate_res_part_date(cls, v: Any) -> date:
        """timestamp ms 또는 yyyy-MM-dd 문자열을 date로 변환."""
        if isinstance(v, date):
            return v
        if isinstance(v, int | float):
            return datetime.fromtimestamp(v / 1000, tz=timezone.utc).date()
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError(f"res_part_date must be yyyy-MM-dd format, got {v!r}")
        msg = f"res_part_date must be date/int/str, got {type(v).__name__}"
        raise ValueError(msg)


# ──────────────────────────────────────────────
# ReservationDetail 클래스
# ──────────────────────────────────────────────


class ReservationDetail(BaseModel):
    """
    예약 상세 정보.

    외부 API 응답 기준 — /ROYAL/api/v1/res/myReservation 응답의 개별 예약 데이터.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "res_no": "202403265572",
                    "res_idx": "202402270280",
                    "res_status": "Y",
                    "res_title": "경복궁 한국어 해설 프로그램",
                    "res_name": "홍길동",
                    "res_mobile": "010-5066-4068",
                    "res_user_cnt": 59,
                    "res_part_date": "2025-02-13",
                    "res_part_start_time": "10:00",
                    "res_part_end_time": "11:00",
                    "res_part": 1,
                    "vw_title": "경복궁 관람",
                    "res_talk_address": "경복궁",
                }
            ]
        },
    )

    res_no: str  # 예약 번호
    res_idx: str  # 예약 프로그램 ID
    res_status: ReservationStatus  # 예약 상태
    res_title: str  # 프로그램 제목
    res_name: str  # 예약자 이름
    res_mobile: str  # 예약자 휴대폰 번호
    res_user_cnt: int  # 예약 인원
    res_part_date: str  # 예약 날짜 "YYYY-MM-DD"
    res_part_start_time: str  # 시작 시간
    res_part_end_time: str  # 종료 시간
    res_part: int  # 회차 번호
    vw_title: str  # 관람 프로그램 제목
    res_talk_address: str  # 알림톡 주소 (궁 이름)


# ──────────────────────────────────────────────
# ReservationQueryRequest 클래스
# ──────────────────────────────────────────────


class ReservationQueryRequest(MobileValidatorMixin):
    """
    예약 조회 요청.

    GET /ROYAL/api/v1/res/myReservation 요청 스키마.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "res_no": "202403265572",
                    "res_mobile": "010-5066-4068",
                }
            ]
        },
    )

    res_no: Annotated[
        str,
        Field(
            min_length=1,
            description="예약 번호",
        ),
    ]


# ──────────────────────────────────────────────
# ReservationCreateRequest 클래스
# ──────────────────────────────────────────────


class ReservationCreateRequest(MobileValidatorMixin):
    """
    예약 생성 요청.

    POST /ROYAL/api/v1/res/insert 요청 스키마.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "res_idx": "202402270280",
                    "pt_idx": "94660",
                    "group_code": "ROYAL",
                    "res_gubun": "Y",
                    "res_group_gubun": "N",
                    "res_date": "2026-06-17",
                    "res_name": "홍길동",
                    "res_mobile": "010-5066-4068",
                    "res_user_cnt": 59,
                    "res_pri_policy_yn": "Y",
                    "res_group_nm": "서울중마초등학교",
                    "res_film_yn": "Y",
                }
            ]
        },
    )

    res_idx: Annotated[
        str,
        Field(
            min_length=1,
            description="예약 프로그램 ID",
        ),
    ]
    pt_idx: Annotated[
        str,
        Field(
            min_length=1,
            description="회차 ID",
        ),
    ]
    group_code: Annotated[
        str,
        Field(
            min_length=1,
            description="기관 그룹 코드",
        ),
    ]
    res_gubun: Annotated[
        ReservationGubun,
        Field(description="예약 유형 (Y=개인, N=단체)"),
    ]
    res_group_gubun: Annotated[
        ReservationGroupGubun,
        Field(description="단체 구분 (Y=청소년, N=일반)"),
    ]
    res_date: Annotated[
        date,
        Field(description="예약 날짜"),
    ]
    res_name: Annotated[
        str,
        Field(
            min_length=1,
            description="예약자 이름",
        ),
    ]
    res_user_cnt: Annotated[
        int,
        Field(
            gt=0,
            description="예약 인원",
        ),
    ]
    res_pri_policy_yn: Annotated[
        str,
        Field(description="개인정보 동의 여부 (Y/N)"),
    ]
    res_eml: Annotated[
        str | None,
        Field(
            default=None,
            description="이메일 주소",
        ),
    ] = None
    res_group_nm: Annotated[
        str | None,
        Field(
            default=None,
            description="단체명",
        ),
    ] = None
    res_film_yn: Annotated[
        str | None,
        Field(
            default=None,
            description="촬영 동의 여부 (Y/N)",
        ),
    ] = None
    res_leader_name: Annotated[
        str | None,
        Field(
            default=None,
            description="인솔자 이름",
        ),
    ] = None
    res_leader_mobile1: Annotated[
        str | None,
        Field(
            default=None,
            description="인솔자 전화 앞자리",
        ),
    ] = None
    res_leader_mobile2: Annotated[
        str | None,
        Field(
            default=None,
            description="인솔자 전화 중간자리",
        ),
    ] = None
    res_leader_mobile3: Annotated[
        str | None,
        Field(
            default=None,
            description="인솔자 전화 끝자리",
        ),
    ] = None

    @field_validator("res_date", mode="before")
    @classmethod
    def validate_res_date(cls, v: Any) -> date:
        """예약 날짜는 오늘 이후여야 함."""
        if isinstance(v, date):
            today = date.today()
            if v < today:
                raise ValueError("예약 날짜는 오늘 이후여야 합니다")
            return v
        if isinstance(v, str):
            try:
                parsed_date = date.fromisoformat(v)
            except ValueError:
                raise ValueError(f"예약 날짜 형식이 잘못되었습니다: {v}")
            today = date.today()
            if parsed_date < today:
                raise ValueError("예약 날짜는 오늘 이후여야 합니다")
            return parsed_date
        raise TypeError(f"res_date must be date or string, got {type(v).__name__}")


# ──────────────────────────────────────────────
# ReservationCreateResponse 클래스
# ──────────────────────────────────────────────


class ReservationCreateResponse(BaseModel):
    """
    예약 생성 응답.

    POST /ROYAL/api/v1/res/insert 응답 스키마.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    status: str = Field(alias="resReqStatus")
    message: str | None = Field(default=None, alias="resReqMsg")
    res_no: str | None = Field(default=None, alias="resNo")
    vw_title: str | None = Field(default=None, alias="vwTitle")


# ──────────────────────────────────────────────
# ReservationCancelRequest 클래스
# ──────────────────────────────────────────────


class ReservationCancelRequest(MobileValidatorMixin):
    """
    예약 취소 요청.

    POST /ROYAL/api/v1/res/cancel 요청 스키마.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "res_no": "202403265572",
                    "res_mobile": "010-5066-4068",
                }
            ]
        },
    )

    res_no: Annotated[
        str,
        Field(
            min_length=1,
            description="예약 번호",
        ),
    ]


# ──────────────────────────────────────────────
# ReservationCancelResponse 클래스
# ──────────────────────────────────────────────


class ReservationCancelResponse(BaseModel):
    """
    예약 취소 응답.

    POST /ROYAL/api/v1/res/cancel 응답 스키마.
    """

    model_config = ConfigDict(
        extra="ignore",
    )

    status: str = Field(default="")
    message: str = Field(default="")


# ──────────────────────────────────────────────
# Re-export
# ──────────────────────────────────────────────

__all__ = [
    "ReservationStatus",
    "ReservationGubun",
    "ReservationGroupGubun",
    "ReservationPart",
    "ReservationDetail",
    "ReservationQueryRequest",
    "ReservationCreateRequest",
    "ReservationCreateResponse",
    "ReservationCancelRequest",
    "ReservationCancelResponse",
]
