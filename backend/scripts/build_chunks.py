"""3단계 청킹 실행 (검증용 러너).

rag/extracted/{table}.jsonl → 청킹 → rag/chunks/{table}.jsonl + 통계.

실행:
    PYTHONPATH=backend python3 backend/scripts/build_chunks.py [table]
    (table 미지정 시 cms_board)
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from app.services.rag.chunking.parsers import (
    CmsBoardChunkParser,
    CmsMenuContentsChunkParser,
    RyInfoLocaChunkParser,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IN_DIR = _REPO_ROOT / "rag" / "extracted"
_OUT_DIR = _REPO_ROOT / "rag" / "chunks"

_PARSERS = {
    "cms_board": CmsBoardChunkParser,
    "cms_menu_contents": CmsMenuContentsChunkParser,
    "ry_info_loca": RyInfoLocaChunkParser,
}


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def run_table(table: str) -> None:
    parser = _PARSERS[table]()
    records = _read_jsonl(_IN_DIR / f"{table}.jsonl")

    all_chunks = []
    doc_chunk_counts = []
    for rec in records:
        chunks = parser.parse(rec)
        doc_chunk_counts.append(len(chunks))
        all_chunks.extend(chunks)

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = _OUT_DIR / f"{table}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(c.model_dump_json() + "\n")

    # 통계
    lens = [len(c.chunk_text) for c in all_chunks]
    tables = sum(1 for c in all_chunks if c.is_table)
    ids = [c.chunk_id for c in all_chunks]
    dup = len(ids) - len(set(ids))
    zero_doc = sum(1 for n in doc_chunk_counts if n == 0)
    from collections import Counter

    ct = Counter(c.content_type for c in all_chunks)

    dmin, davg, dmax = (
        min(doc_chunk_counts),
        round(statistics.mean(doc_chunk_counts), 2),
        max(doc_chunk_counts),
    )
    lmin, lavg, lmax = min(lens), round(statistics.mean(lens)), max(lens)
    short = sum(1 for n in lens if n < 50)
    long = sum(1 for n in lens if n > 4000)

    print(f"[{table}] docs={len(records)} chunks={len(all_chunks)}")
    print(f"  chunk_id 중복={dup}  0-chunk docs={zero_doc}")
    print(f"  doc당 chunk min/avg/max={dmin}/{davg}/{dmax}")
    print(f"  chunk_text 길이 min/avg/max={lmin}/{lavg}/{lmax}")
    print(f"  너무 짧음(<50)={short}  너무 김(>4000)={long}")
    print(f"  표 chunk={tables}  content_type={dict(ct)}")
    print(f"  출력: {out}")

    # 샘플 2건
    print("\n--- 샘플 ---")
    for c in all_chunks[:2]:
        print(f"\n[{c.chunk_id}] is_table={c.is_table} header_path={c.header_path}")
        print(c.chunk_text[:400])


def main() -> None:
    tables = [sys.argv[1]] if len(sys.argv) > 1 else list(_PARSERS)
    for t in tables:
        run_table(t)
        print()


if __name__ == "__main__":
    main()
