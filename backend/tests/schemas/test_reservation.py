from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.reservation import (
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationPart,
    ReservationQueryRequest,
    ReservationStatus,
)

MOBILE_VALID = "010-5066-4068"


class TestReservationPart:
    """ReservationPart 스키마 테스트."""

    def test_part_timestamp_conversion(self):
        """timestamp ms를 date 타입으로 변환하는지 확인."""
        timestamp_ms = 1778079600000  # 2026-05-06 UTC
        part = ReservationPart(
            pt_idx=115717,
            res_idx="202412120391",
            res_part=6,
            res_part_date=timestamp_ms,
            res_part_start_time="14:00",
            res_part_end_time="14:00",
            res_dl_yn="N",
            res_user_cnt=10,
            res_user_cnt_y=5,
            res_dl_yn_msg="예약 가능",
        )

        assert isinstance(part.res_part_date, date)
        assert part.res_part_date == date(2026, 5, 6)


class TestReservationQueryRequest:
    """ReservationQueryRequest 스키마 테스트."""

    def test_query_request_valid(self):
        """유효한 조회 요청."""
        req = ReservationQueryRequest(
            res_no="2645",
            res_mobile=MOBILE_VALID,
        )

        assert req.res_no == "2645"
        assert req.res_mobile == MOBILE_VALID

    def test_query_mobile_without_hyphen(self):
        """하이픈이 없는 휴대폰 번호는 실패."""
        with pytest.raises(ValidationError) as exc_info:
            ReservationQueryRequest(
                res_no="2645",
                res_mobile="01050664068",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("res_mobile",) for err in errors)

    def test_query_mobile_invalid_format(self):
        """잘못된 형식의 휴대폰 번호는 실패."""
        with pytest.raises(ValidationError) as exc_info:
            ReservationQueryRequest(
                res_no="2645",
                res_mobile="010-1234-56789",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("res_mobile",) for err in errors)


class TestReservationCreateRequest:
    """ReservationCreateRequest 스키마 테스트."""

    def test_create_request_valid(self):
        """유효한 예약 생성 요청 — 필수 필드 전부 포함."""
        tomorrow = date.today() + timedelta(days=1)
        req = ReservationCreateRequest(
            res_idx="202402270280",
            pt_idx="94660",
            group_code="ROYAL",
            res_gubun="Y",
            res_group_gubun="N",
            res_date=tomorrow,
            res_name="홍길동",
            res_mobile=MOBILE_VALID,
            res_user_cnt=5,
            res_pri_policy_yn="Y",
        )

        assert req.res_idx == "202402270280"
        assert req.pt_idx == "94660"
        assert req.res_name == "홍길동"
        assert req.res_mobile == MOBILE_VALID
        assert req.res_user_cnt == 5

    def test_create_request_past_date(self):
        """과거 날짜는 실패."""
        past_date = date.today() - timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            ReservationCreateRequest(
                res_idx="202402270280",
                pt_idx="94660",
                group_code="ROYAL",
                res_gubun="Y",
                res_group_gubun="N",
                res_date=past_date,
                res_name="홍길동",
                res_mobile=MOBILE_VALID,
                res_user_cnt=5,
                res_pri_policy_yn="Y",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("res_date",) for err in errors)

    def test_create_request_missing_required(self):
        """필수 필드 res_name 누락."""
        tomorrow = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            ReservationCreateRequest(
                res_idx="202402270280",
                pt_idx="94660",
                group_code="ROYAL",
                res_gubun="Y",
                res_group_gubun="N",
                res_date=tomorrow,
                # res_name 누락
                res_mobile=MOBILE_VALID,
                res_user_cnt=5,
                res_pri_policy_yn="Y",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("res_name",) for err in errors)

    def test_create_request_invalid_mobile(self):
        """잘못된 휴대폰 번호."""
        tomorrow = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            ReservationCreateRequest(
                res_idx="202402270280",
                pt_idx="94660",
                group_code="ROYAL",
                res_gubun="Y",
                res_group_gubun="N",
                res_date=tomorrow,
                res_name="홍길동",
                res_mobile="01050664068",  # 하이픈 없음
                res_user_cnt=5,
                res_pri_policy_yn="Y",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("res_mobile",) for err in errors)

    def test_create_request_extra_field_forbidden(self):
        """extra 필드 추가는 실패."""
        tomorrow = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            ReservationCreateRequest(
                res_idx="202402270280",
                pt_idx="94660",
                group_code="ROYAL",
                res_gubun="Y",
                res_group_gubun="N",
                res_date=tomorrow,
                res_name="홍길동",
                res_mobile=MOBILE_VALID,
                res_user_cnt=5,
                res_pri_policy_yn="Y",
                unknown_field="not_allowed",  # extra 필드
            )

        errors = exc_info.value.errors()
        assert any(err["type"] == "extra_forbidden" for err in errors)


class TestReservationCancelRequest:
    """ReservationCancelRequest 스키마 테스트."""

    def test_cancel_request_valid(self):
        """유효한 예약 취소 요청."""
        req = ReservationCancelRequest(
            res_no="10",
            res_mobile=MOBILE_VALID,
        )

        assert req.res_no == "10"
        assert req.res_mobile == MOBILE_VALID

    def test_cancel_mobile_without_hyphen(self):
        """하이픈이 없는 휴대폰 번호는 실패."""
        with pytest.raises(ValidationError) as exc_info:
            ReservationCancelRequest(
                res_no="10",
                res_mobile="01050664068",
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("res_mobile",) for err in errors)


class TestReservationStatus:
    """ReservationStatus Enum 테스트."""

    def test_all_status_values(self):
        """모든 상태 코드가 유효한지 확인."""
        assert ReservationStatus.CONFIRMED.value == "Y"
        assert ReservationStatus.WAITING.value == "W"
        assert ReservationStatus.PENDING.value == "N"
        assert ReservationStatus.CANCELLED.value == "X"
