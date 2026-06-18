"""ChunkValidator — 청킹 결과 검증 + 통계 (분석 문서 11장)."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

from app.services.rag.chunking.base import Chunk

MIN_TEXT_LEN = 10
SHORT_LEN = 50
LONG_LEN = 4000

_REQUIRED = (
    "chunk_id",
    "parent_id",
    "site_code",
    "source_table",
    "source_id",
    "source_type",
    "content_type",
    "chunk_text",
)


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(chunks: list[Chunk]) -> ValidationReport:
    rep = ValidationReport()
    seen_ids: set[str] = set()

    for c in chunks:
        d = c.model_dump()
        for f in _REQUIRED:
            if not d.get(f) or (isinstance(d[f], str) and not d[f].strip()):
                rep.errors.append(f"{c.chunk_id}: 필수 필드 비어있음 '{f}'")
        if c.chunk_id in seen_ids:
            rep.errors.append(f"chunk_id 중복: {c.chunk_id}")
        seen_ids.add(c.chunk_id)
        if len(c.chunk_text) < MIN_TEXT_LEN:
            rep.errors.append(
                f"{c.chunk_id}: chunk_text 너무 짧음({len(c.chunk_text)})"
            )
        if not c.text_hash:
            rep.errors.append(f"{c.chunk_id}: text_hash 없음")
        try:
            json.dumps(c.metadata, ensure_ascii=False)
        except (TypeError, ValueError):
            rep.errors.append(f"{c.chunk_id}: metadata 직렬화 불가")
        if len(c.chunk_text) > LONG_LEN:
            rep.warnings.append(f"{c.chunk_id}: chunk_text 김({len(c.chunk_text)})")

    lens = [len(c.chunk_text) for c in chunks]
    rep.stats = {
        "총_chunk": len(chunks),
        "chunk_id_고유": len(seen_ids),
        "source_table별": dict(Counter(c.source_table for c in chunks)),
        "content_type별": dict(Counter(c.content_type for c in chunks)),
        "표_chunk": sum(1 for c in chunks if c.is_table),
        "평균길이": round(sum(lens) / len(lens)) if lens else 0,
        "최대길이": max(lens) if lens else 0,
        "짧은chunk(<50)": sum(1 for n in lens if n < SHORT_LEN),
        "긴chunk(>4000)": sum(1 for n in lens if n > LONG_LEN),
    }
    return rep
