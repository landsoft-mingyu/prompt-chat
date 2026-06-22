"""예약 흐름 처리 서비스."""

from typing import Any

from app.adapters.interfaces.reservation_api_client import IReservationApiClient
from app.repositories.interfaces.reservation_orchestrator import (
    IReservationOrchestrator,
)
from app.repositories.interfaces.session_store import SessionStore
from app.repositories.interfaces.slot_filling_service import ISlotFillingService
from app.schemas.orchestrator import (
    ChatIntent,
    OrchestratorResponse,
    SlotFillingState,
    SlotState,
)

_CONFIRM_KEYWORDS = {"네", "예", "응", "맞아요", "확인", "진행", "ok", "yes"}
_CANCEL_KEYWORDS = {"아니요", "취소", "no", "안 해"}


def _is_confirmed(normalized: str) -> bool:
    """확인 의사를 정확히 판별. 서브스트링 오발동 방지."""
    return normalized in _CONFIRM_KEYWORDS or normalized.startswith(
        ("네 ", "예 ", "ok ", "yes ")
    )


def _is_cancelled(normalized: str) -> bool:
    """취소 의사를 정확히 판별. '아니면...' 등 부정문 오발동 방지."""
    return normalized in _CANCEL_KEYWORDS or normalized.startswith(
        ("취소 ", "no ", "아니요 ")
    )


class ReservationOrchestrator(IReservationOrchestrator):
    """예약 흐름 처리 구현체.

    슬롯 수집(COLLECTING) → 확인 요청(CONFIRMING) → API 호출 순으로 진행한다.
    """

    def __init__(
        self,
        api_client: IReservationApiClient,
        slot_service: ISlotFillingService,
        session_store: SessionStore,
    ) -> None:
        self._api = api_client
        self._slots = slot_service
        self._store = session_store

    async def handle(
        self,
        intent: ChatIntent,
        message: str,
        session_id: str,
        site_code: str,
        slot_state: SlotFillingState,
    ) -> OrchestratorResponse:
        """의도별 예약 흐름 처리 진입점."""
        if intent == ChatIntent.RESERVATION_CREATE:
            return await self._handle_create(message, session_id, slot_state)
        if intent == ChatIntent.RESERVATION_QUERY:
            return await self._handle_query(message, session_id, slot_state)
        if intent == ChatIntent.RESERVATION_CANCEL:
            return await self._handle_cancel(message, session_id, slot_state)
        # 예상치 못한 의도
        return OrchestratorResponse(
            session_id=session_id,
            message="죄송합니다. 처리할 수 없는 요청입니다.",
            intent=intent.value,
            mode="reservation",
        )

    async def list_programs(
        self,
        session_id: str,
        site_code: str,
        group_code: str | None = None,
    ) -> OrchestratorResponse:
        """프로그램 목록 조회."""
        try:
            code = group_code or "gbg"
            result = await self._api.get_programs(code)
            # API 응답: {status, currentList, nextList, teenagerList}
            programs = result.get("currentList", result.get("data", []))
            if not isinstance(programs, list):
                programs = []
            message = self._format_programs(programs)
            return OrchestratorResponse(
                session_id=session_id,
                message=message,
                intent=ChatIntent.RESERVATION_LIST.value,
                action_card={"type": "program_list", "items": programs},
                mode="reservation",
            )
        except Exception as exc:
            return OrchestratorResponse(
                session_id=session_id,
                message=f"프로그램 목록을 불러오지 못했습니다: {exc}",
                intent=ChatIntent.RESERVATION_LIST.value,
                mode="reservation",
            )

    async def list_parts(
        self,
        session_id: str,
        res_idx: str,
        res_part_date: str,
    ) -> OrchestratorResponse:
        """회차 목록 조회."""
        try:
            result = await self._api.get_parts(res_idx, res_part_date)
            # API 응답: {status, parts} 또는 {status, message}
            if result.get("status") == "FAIL":
                return OrchestratorResponse(
                    session_id=session_id,
                    message=result.get("message", "회차 조회에 실패했습니다."),
                    intent=ChatIntent.RESERVATION_PARTS.value,
                    mode="reservation",
                )
            parts = result.get("parts", result.get("data", []))
            if not isinstance(parts, list):
                parts = []
            message = self._format_parts(parts)
            return OrchestratorResponse(
                session_id=session_id,
                message=message,
                intent=ChatIntent.RESERVATION_PARTS.value,
                action_card={"type": "parts_list", "items": parts},
                mode="reservation",
            )
        except Exception as exc:
            return OrchestratorResponse(
                session_id=session_id,
                message=f"회차 목록을 불러오지 못했습니다: {exc}",
                intent=ChatIntent.RESERVATION_PARTS.value,
                mode="reservation",
            )

    # ── 예약 생성 흐름 ────────────────────────────────────────

    async def _handle_create(
        self,
        message: str,
        session_id: str,
        slot_state: SlotFillingState,
    ) -> OrchestratorResponse:
        # CONFIRMING 상태에서 사용자 확인 응답 처리
        if slot_state.state == SlotState.CONFIRMING:
            return await self._process_confirmation(
                message, session_id, slot_state, ChatIntent.RESERVATION_CREATE
            )

        # 슬롯 추출
        updated_slots = await self._slots.extract_slots(
            message, ChatIntent.RESERVATION_CREATE, slot_state.slots
        )
        is_valid, err = self._slots.validate_slots(
            ChatIntent.RESERVATION_CREATE, updated_slots
        )
        if not is_valid:
            slot_state.slots = updated_slots
            await self._store.save_slot_state(session_id, slot_state)
            return OrchestratorResponse(
                session_id=session_id,
                message=f"{err} 다시 입력해주세요.",
                intent=ChatIntent.RESERVATION_CREATE.value,
                slots_filled=updated_slots,
                mode="reservation",
            )

        missing = self._slots.get_missing_slots(
            ChatIntent.RESERVATION_CREATE, updated_slots
        )
        slot_state.slots = updated_slots

        if missing:
            slot_state.state = SlotState.COLLECTING
            await self._store.save_slot_state(session_id, slot_state)
            prompt = self._slots.build_prompt_for_missing_slot(
                missing, ChatIntent.RESERVATION_CREATE
            )
            return OrchestratorResponse(
                session_id=session_id,
                message=prompt,
                intent=ChatIntent.RESERVATION_CREATE.value,
                slots_needed=missing,
                slots_filled=updated_slots,
                mode="reservation",
            )

        # 모든 슬롯 완료 → 확인 요청
        slot_state.state = SlotState.CONFIRMING
        await self._store.save_slot_state(session_id, slot_state)
        confirm_msg = self._slots.build_confirmation_message(
            ChatIntent.RESERVATION_CREATE, updated_slots
        )
        return OrchestratorResponse(
            session_id=session_id,
            message=confirm_msg,
            intent=ChatIntent.RESERVATION_CREATE.value,
            slots_filled=updated_slots,
            requires_confirmation=True,
            mode="reservation",
        )

    # ── 예약 조회 흐름 ────────────────────────────────────────

    async def _handle_query(
        self,
        message: str,
        session_id: str,
        slot_state: SlotFillingState,
    ) -> OrchestratorResponse:
        if slot_state.state == SlotState.CONFIRMING:
            return await self._process_confirmation(
                message, session_id, slot_state, ChatIntent.RESERVATION_QUERY
            )

        updated_slots = await self._slots.extract_slots(
            message, ChatIntent.RESERVATION_QUERY, slot_state.slots
        )
        missing = self._slots.get_missing_slots(
            ChatIntent.RESERVATION_QUERY, updated_slots
        )
        slot_state.slots = updated_slots

        if missing:
            slot_state.state = SlotState.COLLECTING
            await self._store.save_slot_state(session_id, slot_state)
            prompt = self._slots.build_prompt_for_missing_slot(
                missing, ChatIntent.RESERVATION_QUERY
            )
            return OrchestratorResponse(
                session_id=session_id,
                message=prompt,
                intent=ChatIntent.RESERVATION_QUERY.value,
                slots_needed=missing,
                slots_filled=updated_slots,
                mode="reservation",
            )

        # 슬롯 완료 → 바로 조회 실행 (확인 불필요)
        return await self._execute_query(session_id, updated_slots)

    # ── 예약 취소 흐름 ────────────────────────────────────────

    async def _handle_cancel(
        self,
        message: str,
        session_id: str,
        slot_state: SlotFillingState,
    ) -> OrchestratorResponse:
        if slot_state.state == SlotState.CONFIRMING:
            return await self._process_confirmation(
                message, session_id, slot_state, ChatIntent.RESERVATION_CANCEL
            )

        updated_slots = await self._slots.extract_slots(
            message, ChatIntent.RESERVATION_CANCEL, slot_state.slots
        )
        missing = self._slots.get_missing_slots(
            ChatIntent.RESERVATION_CANCEL, updated_slots
        )
        slot_state.slots = updated_slots

        if missing:
            slot_state.state = SlotState.COLLECTING
            await self._store.save_slot_state(session_id, slot_state)
            prompt = self._slots.build_prompt_for_missing_slot(
                missing, ChatIntent.RESERVATION_CANCEL
            )
            return OrchestratorResponse(
                session_id=session_id,
                message=prompt,
                intent=ChatIntent.RESERVATION_CANCEL.value,
                slots_needed=missing,
                slots_filled=updated_slots,
                mode="reservation",
            )

        # 취소는 확인 필요
        slot_state.state = SlotState.CONFIRMING
        await self._store.save_slot_state(session_id, slot_state)
        confirm_msg = self._slots.build_confirmation_message(
            ChatIntent.RESERVATION_CANCEL, updated_slots
        )
        return OrchestratorResponse(
            session_id=session_id,
            message=confirm_msg,
            intent=ChatIntent.RESERVATION_CANCEL.value,
            slots_filled=updated_slots,
            requires_confirmation=True,
            mode="reservation",
        )

    # ── 확인 응답 처리 ────────────────────────────────────────

    async def _process_confirmation(
        self,
        message: str,
        session_id: str,
        slot_state: SlotFillingState,
        intent: ChatIntent,
    ) -> OrchestratorResponse:
        """CONFIRMING 상태에서 사용자 응답 처리."""
        normalized = message.strip().lower()

        if _is_cancelled(normalized):
            await self._store.delete_slot_state(session_id)
            return OrchestratorResponse(
                session_id=session_id,
                message="예약을 취소했습니다. 다른 도움이 필요하신가요?",
                intent=intent.value,
                mode="reservation",
            )

        if _is_confirmed(normalized):
            return await self._execute_confirmed_action(session_id, slot_state)

        # 모호한 응답 → 재확인
        return OrchestratorResponse(
            session_id=session_id,
            message="'네' 또는 '아니오'로 답해주세요.",
            intent=intent.value,
            slots_filled=slot_state.slots,
            requires_confirmation=True,
            mode="reservation",
        )

    async def _execute_confirmed_action(
        self,
        session_id: str,
        slot_state: SlotFillingState,
    ) -> OrchestratorResponse:
        """확인 완료 후 실제 API 호출."""
        intent = slot_state.intent
        slots = slot_state.slots

        try:
            if intent == ChatIntent.RESERVATION_CREATE:
                payload = self._build_create_payload(slots)
                result = await self._api.create_reservation(payload)
                await self._store.delete_slot_state(session_id)
                res_no = result.get("resNo", "")
                msg = (
                    f"예약이 완료되었습니다. 예약 번호: {res_no}"
                    if res_no
                    else "예약이 완료되었습니다."
                )
                return OrchestratorResponse(
                    session_id=session_id,
                    message=msg,
                    intent=intent.value,
                    action_card={
                        "type": "reservation_created",
                        "res_no": res_no,
                        **result,
                    },
                    mode="reservation",
                )

            if intent == ChatIntent.RESERVATION_CANCEL:
                result = await self._api.cancel_reservation(
                    slots["res_no"], slots["res_mobile"]
                )
                await self._store.delete_slot_state(session_id)
                return OrchestratorResponse(
                    session_id=session_id,
                    message="예약이 취소되었습니다.",
                    intent=intent.value,
                    action_card={"type": "reservation_cancelled", **result},
                    mode="reservation",
                )

        except Exception as exc:
            # API 실패 시 CONFIRMING → COLLECTING으로 리셋해 재시도 가능하게 함
            slot_state.state = SlotState.COLLECTING
            await self._store.save_slot_state(session_id, slot_state)
            return OrchestratorResponse(
                session_id=session_id,
                message=f"처리 중 오류가 발생했습니다: {exc}\n다시 시도하시겠어요?",
                intent=intent.value,
                slots_filled=slots,
                mode="reservation",
            )

        return OrchestratorResponse(
            session_id=session_id,
            message="처리가 완료되었습니다.",
            intent=intent.value,
            mode="reservation",
        )

    async def _execute_query(
        self,
        session_id: str,
        slots: dict[str, Any],
    ) -> OrchestratorResponse:
        """예약 조회 실행."""
        try:
            result = await self._api.get_reservation(
                slots["res_no"], slots["res_mobile"]
            )
            await self._store.delete_slot_state(session_id)
            msg = self._format_reservation(result)
            return OrchestratorResponse(
                session_id=session_id,
                message=msg,
                intent=ChatIntent.RESERVATION_QUERY.value,
                action_card={"type": "reservation_detail", "data": result},
                mode="reservation",
            )
        except Exception as exc:
            return OrchestratorResponse(
                session_id=session_id,
                message=f"예약 조회 중 오류가 발생했습니다: {exc}",
                intent=ChatIntent.RESERVATION_QUERY.value,
                mode="reservation",
            )

    # ── 포매터 ───────────────────────────────────────────────

    @staticmethod
    def _build_create_payload(slots: dict[str, Any]) -> dict[str, Any]:
        return {
            "res_idx": slots.get("res_idx"),
            "pt_idx": str(slots.get("pt_idx", "")),
            "group_code": slots.get("group_code"),
            "res_gubun": "Y",
            "res_group_gubun": "N",
            "res_date": str(slots.get("res_date", "")),
            "res_name": slots.get("res_name"),
            "res_mobile": slots.get("res_mobile"),
            "res_user_cnt": int(slots.get("res_user_cnt", 1)),
            "res_pri_policy_yn": "Y",
        }

    @staticmethod
    def _format_programs(programs: Any) -> str:
        if not isinstance(programs, list) or not programs:
            return "현재 예약 가능한 프로그램이 없습니다."
        lines = ["예약 가능한 프로그램 목록입니다:\n"]
        for p in programs[:10]:
            idx = p.get("res_idx") or p.get("resIdx", "")
            title = p.get("res_title") or p.get("resTitle", "")
            lines.append(f"  • [{idx}] {title}")
        return "\n".join(lines)

    @staticmethod
    def _format_parts(parts: Any) -> str:
        if not isinstance(parts, list) or not parts:
            return "해당 날짜에 예약 가능한 회차가 없습니다."
        lines = ["예약 가능한 회차 목록입니다:\n"]
        for p in parts[:20]:
            pt_idx = p.get("pt_idx") or p.get("ptIdx", "")
            start = p.get("res_part_start_time") or p.get("resPartStartTime", "")
            end = p.get("res_part_end_time") or p.get("resPartEndTime", "")
            dl = p.get("res_dl_yn") or p.get("resDlYn", "N")
            status = "마감" if dl == "Y" else "예약 가능"
            lines.append(f"  • 회차 {pt_idx}: {start}~{end} ({status})")
        return "\n".join(lines)

    @staticmethod
    def _format_reservation(data: Any) -> str:
        if not data:
            return "예약 내역을 찾을 수 없습니다."
        if isinstance(data, dict):
            title = data.get("res_title") or data.get("resTitle", "")
            name = data.get("res_name") or data.get("resName", "")
            date = data.get("res_part_date") or data.get("resPartDate", "")
            status = data.get("res_status") or data.get("resStatus", "")
            return (
                f"예약 내역입니다:\n"
                f"  • 프로그램: {title}\n"
                f"  • 예약자: {name}\n"
                f"  • 날짜: {date}\n"
                f"  • 상태: {status}"
            )
        return str(data)
