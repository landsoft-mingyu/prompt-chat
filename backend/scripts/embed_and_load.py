"""4단계: chunk → BGE-M3 임베딩(dense+sparse) → Milvus `site_chunks` 적재.

- 입력: rag/chunks/{table}.jsonl
- 임베딩: BGE-M3 임베딩 서비스(HTTP) 호출 → dense 1024d + sparse(lexical)
- 적재: gungneung-milvus @ 19530, collection=site_chunks
- 배치 단위로 임베딩→적재를 파이프라인하며 진행 로그 출력.

실행:
    # 1) 임베딩 서비스 먼저 기동 (embedding/ 참고)
    # 2) 적재
    EMBEDDING_URL=http://127.0.0.1:18086 \
      PYTHONPATH=backend python3 backend/scripts/embed_and_load.py [--recreate]
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

from pymilvus import MilvusClient

from app.services.rag.chunking import milvus_schema as ms
from app.services.rag.embedding_client import EmbeddingClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("embed_and_load")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHUNK_DIR = _REPO_ROOT / "rag" / "chunks"
_TABLES = ["cms_board", "cms_menu_contents", "ry_info_loca"]
_MILVUS_URI = "http://127.0.0.1:19530"
_BATCH = 32  # 임베딩+적재 배치 크기

# Milvus에 넣을 scalar 필드(스키마와 일치). 벡터/메타는 별도 처리.
_SCALAR_KEYS = [
    "chunk_id",
    "parent_id",
    "site_code",
    "source_table",
    "source_id",
    "source_type",
    "content_type",
    "bc_id",
    "menu_code",
    "menu_path",
    "group_code",
    "title",
    "section_title",
    "header_path",
    "html_yn",
    "text_hash",
    "regdt",
    "upddt",
    "is_table",
    "chunk_text",
]


def _load_chunks() -> list[dict]:
    """테이블별 chunk 로드 + 건수 로그."""
    rows: list[dict] = []
    for t in _TABLES:
        p = _CHUNK_DIR / f"{t}.jsonl"
        tbl = [json.loads(ln) for ln in open(p, encoding="utf-8")]
        log.info("로드 [%s] %d chunk", t, len(tbl))
        rows += tbl
    log.info("총 %d chunk 로드 완료", len(rows))
    return rows


def _to_milvus_row(chunk: dict, dense: list, sparse: dict) -> dict:
    row: dict = {}
    for k in _SCALAR_KEYS:
        v = chunk.get(k)
        if k == "is_table":
            row[k] = bool(v)
        else:
            # nullable 의존 대신 None → "" 코어싱 (VARCHAR는 nil 불가)
            row[k] = "" if v is None else v
    row["metadata"] = chunk.get("metadata") or {}
    row["dense"] = dense
    row["sparse"] = sparse or {0: 0.0}
    return row


def main() -> None:
    recreate = "--recreate" in sys.argv
    chunks = _load_chunks()
    total = len(chunks)

    # 임베딩 서비스 확인
    embedder = EmbeddingClient()
    log.info("임베딩 서비스: %s", embedder.base_url)
    try:
        log.info("health=%s", embedder.health())
    except Exception as e:  # noqa: BLE001
        log.error("임베딩 서비스 연결 실패: %s — 서비스 기동 여부 확인", e)
        sys.exit(1)

    # 컬렉션 준비
    client = MilvusClient(uri=_MILVUS_URI)
    if recreate or not client.has_collection(ms.COLLECTION):
        ms.create_collection(client, drop_existing=True)
        log.info("컬렉션 재생성: %s", ms.COLLECTION)
    else:
        log.info("기존 컬렉션 사용: %s", ms.COLLECTION)

    # 배치 파이프라인: 임베딩 → 적재 (진행률 로그)
    done = 0
    ct_counter: Counter = Counter()
    n_batches = (total + _BATCH - 1) // _BATCH
    for bi, start in enumerate(range(0, total, _BATCH), start=1):
        batch = chunks[start : start + _BATCH]
        texts = [c["chunk_text"] for c in batch]
        dense_vecs, sparse_w = embedder.embed(texts)
        rows = [
            _to_milvus_row(c, dense_vecs[i], sparse_w[i]) for i, c in enumerate(batch)
        ]
        client.insert(ms.COLLECTION, rows)
        done += len(batch)
        ct_counter.update(c["content_type"] for c in batch)
        log.info(
            "진행 %d/%d (%.0f%%) | batch %d/%d (임베딩+적재 %d건)",
            done,
            total,
            done / total * 100,
            bi,
            n_batches,
            len(batch),
        )

    client.flush(ms.COLLECTION)
    n = client.get_collection_stats(ms.COLLECTION)["row_count"]

    # 최종 통계
    log.info("=" * 50)
    log.info("적재 완료: %s", ms.COLLECTION)
    log.info("  총 chunk: %d / 적재된 entities: %d", total, n)
    log.info("  content_type별: %s", dict(ct_counter))
    if n != total:
        log.warning("  ⚠ chunk 수(%d) ≠ entities(%d) — 일부 누락 가능", total, n)


if __name__ == "__main__":
    main()
