"""Milvus 벡터 저장소 구현."""

from typing import Any

from pymilvus import Collection, connections

from app.repositories.interfaces.vector_repository import VectorRepository


class MilvusVectorRepository(VectorRepository):
    """Milvus 벡터 저장소 어댑터."""

    def __init__(self, uri: str = "http://localhost:19530"):
        """
        Args:
            uri: Milvus 연결 URI (default: localhost:19530)
        """
        self.uri = uri
        self._connect()

    def _connect(self):
        """Milvus 연결."""
        connections.connect("default", uri=self.uri)

    async def insert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> list[str]:
        """벡터 삽입."""
        if not vectors:
            return []

        collection = Collection(collection_name)
        try:
            data = self._prepare_insert_data(vectors)
            result = collection.insert(data)
            return result.primary_keys
        except Exception as e:
            raise RuntimeError(f"벡터 삽입 실패: {str(e)}") from e

    async def upsert_vectors(
        self,
        collection_name: str,
        vectors: list[dict[str, Any]],
    ) -> int:
        """벡터 upsert."""
        if not vectors:
            return 0

        collection = Collection(collection_name)
        try:
            data = self._prepare_insert_data(vectors)
            result = collection.upsert(data)
            return len(result.primary_keys)
        except Exception as e:
            raise RuntimeError(f"벡터 upsert 실패: {str(e)}") from e

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """유사도 기반 벡터 검색."""
        collection = Collection(collection_name)
        try:
            # 필터 조건 생성 (Milvus 표현식)
            expr = self._build_filter_expr(filters) if filters else None

            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10},
            }

            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["*"],
            )

            # 결과 포매팅
            search_results = []
            if results and len(results) > 0:
                for hit in results[0]:
                    entity = hit.entity
                    search_results.append(
                        {
                            "id": hit.id,
                            "distance": hit.distance,
                            "title": entity.get("title"),
                            "content": entity.get("content"),
                            "source_type": entity.get("source_type"),
                            "source_table": entity.get("source_table"),
                            "site_code": entity.get("site_code"),
                            "url": entity.get("url"),
                            "metadata": entity.get("metadata", {}),
                        }
                    )

            return search_results
        except Exception as e:
            raise RuntimeError(f"벡터 검색 실패: {str(e)}") from e

    async def delete_vectors(
        self,
        collection_name: str,
        ids: list[str],
    ) -> int:
        """벡터 삭제."""
        if not ids:
            return 0

        collection = Collection(collection_name)
        try:
            collection.delete(f"id in {ids}")
            return len(ids)
        except Exception as e:
            raise RuntimeError(f"벡터 삭제 실패: {str(e)}") from e

    def _prepare_insert_data(self, vectors: list[dict[str, Any]]) -> list[list]:
        """벡터 데이터를 Milvus insert 형식으로 변환."""
        # vectors 리스트의 각 항목은 {"embedding": [...], "id": ..., ...} 형태
        # Milvus insert 형식: [[field1_values], [field2_values], ...]

        # 필드명 추출 (첫 벡터 항목에서)
        if not vectors:
            return []

        fields = set()
        for v in vectors:
            fields.update(v.keys())

        # 필드별 데이터 수집
        data = {field: [] for field in fields}
        for vector in vectors:
            for field in fields:
                data[field].append(vector.get(field))

        return [data[field] for field in sorted(fields)]

    def _build_filter_expr(self, filters: dict[str, Any]) -> str:
        """필터 조건을 Milvus 표현식으로 변환."""
        if not filters:
            return ""

        expressions = []
        for key, value in filters.items():
            if isinstance(value, str):
                expressions.append(f"{key} == '{value}'")
            elif isinstance(value, list):
                # IN 연산자
                value_str = ", ".join(
                    f"'{v}'" if isinstance(v, str) else str(v) for v in value
                )
                expressions.append(f"{key} in [{value_str}]")
            else:
                expressions.append(f"{key} == {value}")

        return " && ".join(expressions) if expressions else ""
