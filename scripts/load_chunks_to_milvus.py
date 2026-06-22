"""rag/chunks/*.jsonl → Milvus 적재 스크립트.

실행 예시:
    # 기본 (EMBEDDING_URL=http://localhost:18086, MILVUS_HOST=localhost)
    python scripts/load_chunks_to_milvus.py

    # 환경변수 오버라이드
    EMBEDDING_URL=http://localhost:18086 \\
    MILVUS_HOST=localhost MILVUS_PORT=19530 \\
    python scripts/load_chunks_to_milvus.py

    # CLI 인자
    python scripts/load_chunks_to_milvus.py \\
        --milvus-uri http://localhost:19530 \\
        --embedding-url http://localhost:18086 \\
        --collection chunks \\
        --chunks-dir rag/chunks \\
        --batch-size 8 \\
        --drop-existing
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

# ── 상수 ────────────────────────────────────────────
DENSE_DIM = 1024  # BGE-M3 dense 벡터 차원
VARCHAR_MAX = 65535
DEFAULT_BATCH = 8


# ── 임베딩 호출 (동기) ────────────────────────────────
def embed_texts(
    embedding_url: str,
    texts: list[str],
    batch_size: int = DEFAULT_BATCH,
    timeout: float = 300.0,
) -> list[list[float]]:
    """embedding 서버에 배치 요청 후 dense 벡터만 반환."""
    dense_all: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = httpx.post(
            f"{embedding_url.rstrip('/')}/embed",
            json={"texts": batch, "max_length": 8192, "batch_size": batch_size},
            timeout=timeout,
        )
        resp.raise_for_status()
        dense_all.extend(resp.json()["dense"])
        print(f"  embedded {min(i + batch_size, len(texts))}/{len(texts)}", end="\r")
    print()
    return dense_all


# ── Milvus 컬렉션 생성 ────────────────────────────────
def ensure_collection(collection_name: str, drop_existing: bool = False) -> Collection:
    if utility.has_collection(collection_name):
        if drop_existing:
            utility.drop_collection(collection_name)
            print(f"[milvus] dropped existing collection: {collection_name}")
        else:
            print(f"[milvus] collection already exists, appending: {collection_name}")
            return Collection(collection_name)

    fields = [
        FieldSchema("chunk_id", DataType.VARCHAR, is_primary=True, max_length=256),
        FieldSchema("title", DataType.VARCHAR, max_length=512),
        FieldSchema("content", DataType.VARCHAR, max_length=VARCHAR_MAX),
        FieldSchema("source_type", DataType.VARCHAR, max_length=64),
        FieldSchema("source_table", DataType.VARCHAR, max_length=64),
        FieldSchema("site_code", DataType.VARCHAR, max_length=32),
        FieldSchema("url", DataType.VARCHAR, max_length=1024),
        FieldSchema("content_hash", DataType.VARCHAR, max_length=64),
        FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=DENSE_DIM),
    ]
    schema = CollectionSchema(fields, description="prompt_chat RAG chunks")
    col = Collection(collection_name, schema)
    print(f"[milvus] created collection: {collection_name}")
    return col


# ── 인덱스 생성 ──────────────────────────────────────
def create_index(col: Collection) -> None:
    if col.has_index():
        print("[milvus] index already exists, skipping")
        return
    col.create_index(
        field_name="embedding",
        index_params={
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        },
    )
    print("[milvus] index created (IVF_FLAT / COSINE)")


# ── JSONL 읽기 ───────────────────────────────────────
def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ── 메인 ─────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Load RAG chunks into Milvus")
    parser.add_argument(
        "--milvus-uri",
        default=f"http://{os.getenv('MILVUS_HOST', 'localhost')}:{os.getenv('MILVUS_PORT', '19530')}",
        help="Milvus 연결 URI (기본: env MILVUS_HOST/PORT)",
    )
    parser.add_argument(
        "--embedding-url",
        default=os.getenv("EMBEDDING_URL", "http://localhost:18086"),
        help="임베딩 서버 URL (기본: env EMBEDDING_URL)",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("MILVUS_COLLECTION", "chunks"),
        help="Milvus 컬렉션명 (기본: chunks)",
    )
    parser.add_argument(
        "--chunks-dir",
        default="rag/chunks",
        help="JSONL 청크 디렉터리 (기본: rag/chunks)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH,
        help=f"임베딩 배치 크기 (기본: {DEFAULT_BATCH})",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="기존 컬렉션 삭제 후 재생성",
    )
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    jsonl_files = sorted(chunks_dir.glob("*.jsonl"))
    if not jsonl_files:
        print(f"[error] No .jsonl files found in {chunks_dir}", file=sys.stderr)
        sys.exit(1)

    # ── Milvus 연결 ──
    print(f"[milvus] connecting to {args.milvus_uri}")
    connections.connect("default", uri=args.milvus_uri)

    col = ensure_collection(args.collection, drop_existing=args.drop_existing)

    # ── 파일별 적재 ──
    total_inserted = 0
    for jsonl_path in jsonl_files:
        rows = load_jsonl(jsonl_path)
        if not rows:
            continue
        print(f"\n[load] {jsonl_path.name}  ({len(rows)} chunks)")

        texts = [r.get("chunk_text", "") for r in rows]
        print(f"  embedding {len(texts)} texts ...")
        embeddings = embed_texts(args.embedding_url, texts, batch_size=args.batch_size)

        insert_data = {
            "chunk_id": [r.get("chunk_id", "") for r in rows],
            "title": [r.get("title", "")[:512] for r in rows],
            "content": [r.get("chunk_text", "")[:VARCHAR_MAX] for r in rows],
            "source_type": [r.get("source_type", "")[:64] for r in rows],
            "source_table": [r.get("source_table", "")[:64] for r in rows],
            "site_code": [r.get("site_code", "")[:32] for r in rows],
            "url": [
                str(r.get("metadata", {}).get("loca_url") or "")[:1024] for r in rows
            ],
            "content_hash": [r.get("text_hash", "")[:64] for r in rows],
            "embedding": embeddings,
        }
        col.insert(list(insert_data.values()))
        total_inserted += len(rows)
        print(f"  inserted {len(rows)} chunks")

    # ── 인덱스 & 로드 ──
    print(f"\n[milvus] total inserted: {total_inserted}")
    create_index(col)
    col.load()
    print(f"[milvus] collection loaded: {args.collection}")
    print("Done.")


if __name__ == "__main__":
    main()
