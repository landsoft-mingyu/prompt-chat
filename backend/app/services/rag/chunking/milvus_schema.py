"""Milvus `site_chunks` 컬렉션 스키마 정의 (분석 문서 6장).

- dense  : BGE-M3 dense 임베딩(1024d, COSINE) — 의미 검색
- sparse : BGE-M3 sparse(lexical) 임베딩 — 키워드/숫자(요금·전화·시간) 매칭
  → dense+sparse 하이브리드 검색 지원
- scalar : site_code/source_table/content_type/bc_id/menu_code 등 필터 필드

pymilvus 3.0 (MilvusClient) 기준.
"""

from __future__ import annotations

from pymilvus import DataType, MilvusClient

COLLECTION = "site_chunks"
DENSE_DIM = 1024  # BGE-M3 dense 차원

# (필드명, 타입, max_length, nullable, 용도)
# VARCHAR max_length는 문자 수 기준. 한국어 본문 여유 있게.
_SCALAR_FIELDS = [
    ("parent_id", 64, False),  # 원문 행 추적/그룹핑
    ("site_code", 32, False),  # 멀티사이트 필터
    ("source_table", 64, False),  # 테이블 필터
    ("source_id", 64, False),  # 원본 PK(탭키 포함)
    ("source_type", 32, False),  # article/menu_page/location
    ("content_type", 48, False),  # story/visit_fee/location_overview ...
    ("bc_id", 64, True),  # 게시판 종류
    ("menu_code", 32, True),  # 메뉴 코드(비고유)
    ("menu_path", 512, True),  # 메뉴 경로
    ("group_code", 16, True),  # ry 관리권역
    ("title", 256, True),  # 제목/위치명
    ("section_title", 256, True),  # 섹션명
    ("header_path", 512, True),  # breadcrumb 헤더 경로
    ("html_yn", 4, True),  # 소스 경로(Y/N)
    ("text_hash", 64, False),  # 멱등/중복 감지
    ("regdt", 32, True),
    ("upddt", 32, True),
]

# filter/조회에 자주 쓰는 scalar 인덱스 대상
_INDEXED_SCALARS = [
    "parent_id",
    "site_code",
    "source_table",
    "source_id",
    "source_type",
    "content_type",
    "bc_id",
    "menu_code",
    "text_hash",
]


def build_schema(client: MilvusClient):
    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    # primary key
    schema.add_field("chunk_id", DataType.VARCHAR, max_length=128, is_primary=True)
    # scalar
    for name, ml, nullable in _SCALAR_FIELDS:
        schema.add_field(name, DataType.VARCHAR, max_length=ml, nullable=nullable)
    schema.add_field("is_table", DataType.BOOL, nullable=True)
    schema.add_field("chunk_text", DataType.VARCHAR, max_length=8192)  # 임베딩 원문
    schema.add_field("metadata", DataType.JSON, nullable=True)
    # vectors
    schema.add_field("dense", DataType.FLOAT_VECTOR, dim=DENSE_DIM)
    schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)
    return schema


def build_index_params(client: MilvusClient):
    idx = client.prepare_index_params()
    idx.add_index(
        field_name="dense",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200},
    )
    idx.add_index(
        field_name="sparse",
        index_type="SPARSE_INVERTED_INDEX",
        metric_type="IP",
    )
    for f in _INDEXED_SCALARS:
        idx.add_index(field_name=f, index_type="INVERTED")
    return idx


def create_collection(client: MilvusClient, *, drop_existing: bool = False) -> None:
    if client.has_collection(COLLECTION):
        if not drop_existing:
            raise RuntimeError(f"'{COLLECTION}' 이미 존재. drop_existing=True 필요")
        client.drop_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        schema=build_schema(client),
        index_params=build_index_params(client),
    )
