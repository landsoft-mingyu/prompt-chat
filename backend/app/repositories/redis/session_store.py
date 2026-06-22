"""Redis 세션 저장소 구현체."""

import json
from typing import Any

import redis.asyncio as aioredis

from app.repositories.interfaces.session_store import SessionStore
from app.schemas.orchestrator import SlotFillingState

_SLOT_TTL = 1800  # 슬롯 필링 상태: 30분
_SESSION_TTL = 3600  # 세션 메타: 1시간


class RedisSessionStore(SessionStore):
    """Redis 기반 세션 저장소.

    키 설계:
      session:{session_id}  — 세션 메타 (current_intent, last_active)  TTL 1시간
      slot:{session_id}     — SlotFillingState JSON                     TTL 30분
    """

    def __init__(self, redis_url: str) -> None:
        self._redis: aioredis.Redis = aioredis.from_url(
            redis_url, encoding="utf-8", decode_responses=True
        )

    # ── SessionStore 인터페이스 ────────────────────────────────

    async def set_session(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl_seconds: int = _SESSION_TTL,
    ) -> None:
        key = f"session:{session_id}"
        await self._redis.set(key, json.dumps(data, ensure_ascii=False), ex=ttl_seconds)

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        key = f"session:{session_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def delete_session(self, session_id: str) -> bool:
        key = f"session:{session_id}"
        return bool(await self._redis.delete(key))

    async def exists_session(self, session_id: str) -> bool:
        key = f"session:{session_id}"
        return bool(await self._redis.exists(key))

    # ── 슬롯 필링 전용 헬퍼 ───────────────────────────────────

    async def get_slot_state(self, session_id: str) -> SlotFillingState | None:
        """진행 중인 슬롯 필링 상태 조회."""
        key = f"slot:{session_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return SlotFillingState.model_validate_json(raw)

    async def save_slot_state(
        self,
        session_id: str,
        state: SlotFillingState,
        ttl: int = _SLOT_TTL,
    ) -> None:
        """슬롯 필링 상태 저장."""
        key = f"slot:{session_id}"
        await self._redis.set(
            key,
            state.model_dump_json(),
            ex=ttl,
        )

    async def delete_slot_state(self, session_id: str) -> None:
        """슬롯 필링 상태 삭제 (예약 완료/취소 후 호출)."""
        key = f"slot:{session_id}"
        await self._redis.delete(key)

    async def close(self) -> None:
        """연결 정리."""
        await self._redis.aclose()
