"""슬롯 수집 서비스."""

import re
from typing import Any

from app.repositories.interfaces.llm_client import ILLMClient
from app.repositories.interfaces.slot_filling_service import ISlotFillingService
from app.schemas.orchestrator import ChatIntent

# ── 슬롯 정의 ──────────────────────────────────────────────────

CREATE_SLOTS: list[str] = [
    "group_code",
    "res_idx",
    "pt_idx",
    "res_date",
    "res_name",
    "res_mobile",
    "res_user_cnt",
]

QUERY_CANCEL_SLOTS: list[str] = [
    "res_no",
    "res_mobile",
]

SLOT_PROMPTS: dict[str, str] = {
    "group_code": "경복궁(gbg), 창덕궁(cdg), 창경궁(cgg), 종묘(jms), 덕수궁(dsg), 경희궁(rtm) 중 어디로 예약하시겠어요?",
    "res_idx": "어떤 프로그램으로 예약하시겠어요? 프로그램 ID를 알려주세요.",
    "pt_idx": "몇 번 회차로 예약하시겠어요? 회차 번호를 알려주세요.",
    "res_date": "방문 날짜를 알려주세요. (예: 2026-07-15)",
    "res_name": "예약자 성함이 어떻게 되세요?",
    "res_mobile": "휴대폰 번호를 알려주세요. (예: 010-1234-5678)",
    "res_user_cnt": "몇 명이 방문하시나요?",
    "res_no": "예약 번호가 어떻게 되세요?",
}

# 슬롯 추출용 LLM 시스템 프롬프트
_EXTRACT_SYSTEM = """사용자 메시지에서 예약 관련 정보를 추출하세요.
추출할 슬롯: {slots_to_extract}
반드시 JSON만 응답하세요. 추출하지 못한 슬롯은 null로 표시하세요.
예시: {{"group_code": "gbg", "res_date": "2026-07-15", "res_name": null}}"""

# 전화번호 패턴
_MOBILE_RE = re.compile(r"^\d{3}-\d{3,4}-\d{4}$")


class SlotFillingService(ISlotFillingService):
    """슬롯 수집 서비스.

    LLM 기반 추출과 규칙 기반 검증을 혼합하여 슬롯을 관리한다.
    """

    def __init__(self, llm_client: ILLMClient) -> None:
        self._llm = llm_client

    def get_missing_slots(
        self,
        intent: ChatIntent,
        slots: dict[str, Any],
    ) -> list[str]:
        """필수 슬롯 중 아직 채워지지 않은 목록 반환."""
        required = self._required_slots(intent)
        return [s for s in required if not slots.get(s)]

    def build_prompt_for_missing_slot(
        self,
        missing_slots: list[str],
        intent: ChatIntent,
    ) -> str:
        """다음으로 물어볼 슬롯 안내 문구 생성.

        첫 번째 미입력 슬롯에 대한 질문을 반환한다.
        """
        if not missing_slots:
            return "모든 정보가 입력되었습니다."
        first = missing_slots[0]
        return SLOT_PROMPTS.get(first, f"{first} 값을 입력해주세요.")

    def validate_slots(
        self,
        intent: ChatIntent,
        slots: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """슬롯 값 형식 검증.

        Returns:
            (is_valid, error_message)
        """
        mobile = slots.get("res_mobile")
        if mobile and not _MOBILE_RE.match(str(mobile)):
            return False, f"휴대폰 번호 형식이 올바르지 않습니다: {mobile}"

        res_date = slots.get("res_date")
        if res_date:
            try:
                from datetime import date

                parsed = date.fromisoformat(str(res_date))
                if parsed < date.today():
                    return False, "예약 날짜는 오늘 이후여야 합니다."
            except ValueError:
                return False, f"날짜 형식이 올바르지 않습니다: {res_date} (YYYY-MM-DD)"

        res_user_cnt = slots.get("res_user_cnt")
        if res_user_cnt is not None:
            try:
                cnt = int(res_user_cnt)
                if cnt <= 0:
                    return False, "방문 인원은 1명 이상이어야 합니다."
            except (ValueError, TypeError):
                return False, f"방문 인원은 숫자여야 합니다: {res_user_cnt}"

        return True, None

    async def extract_slots(
        self,
        message: str,
        intent: ChatIntent,
        current_slots: dict[str, Any],
    ) -> dict[str, Any]:
        """메시지에서 슬롯 값을 LLM으로 추출하고 기존 slots에 병합.

        이미 채워진 슬롯은 덮어쓰지 않는다.
        """
        required = self._required_slots(intent)
        missing = [s for s in required if not current_slots.get(s)]
        if not missing:
            return current_slots

        system_prompt = _EXTRACT_SYSTEM.format(slots_to_extract=", ".join(missing))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        try:
            raw = await self._llm.chat(messages, temperature=0.0, max_tokens=256)
            extracted = self._parse_json_slots(raw)
        except Exception:
            return current_slots

        merged = dict(current_slots)
        for slot, value in extracted.items():
            if value is not None and slot in missing:
                merged[slot] = value

        return merged

    def build_confirmation_message(
        self,
        intent: ChatIntent,
        slots: dict[str, Any],
    ) -> str:
        """슬롯 내용 요약 + 확인 요청 메시지 생성."""
        lines = ["입력하신 내용을 확인해주세요:\n"]
        labels = {
            "group_code": "궁능",
            "res_idx": "프로그램 ID",
            "pt_idx": "회차 ID",
            "res_date": "방문 날짜",
            "res_name": "예약자",
            "res_mobile": "휴대폰",
            "res_user_cnt": "방문 인원",
            "res_no": "예약 번호",
        }
        for slot in self._required_slots(intent):
            label = labels.get(slot, slot)
            value = slots.get(slot, "(미입력)")
            lines.append(f"  • {label}: {value}")
        lines.append("\n진행하시겠습니까? (네/아니오)")
        return "\n".join(lines)

    # ── 내부 헬퍼 ─────────────────────────────────────────────

    @staticmethod
    def _required_slots(intent: ChatIntent) -> list[str]:
        if intent == ChatIntent.RESERVATION_CREATE:
            return CREATE_SLOTS
        if intent in (ChatIntent.RESERVATION_QUERY, ChatIntent.RESERVATION_CANCEL):
            return QUERY_CANCEL_SLOTS
        return []

    @staticmethod
    def _parse_json_slots(text: str) -> dict[str, Any]:
        """LLM 응답에서 JSON 딕셔너리 추출."""
        import json

        text = text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return {}
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            return {}
