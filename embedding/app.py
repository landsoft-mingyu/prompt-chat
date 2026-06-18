"""BGE-M3 임베딩 서비스 (dense + sparse).

적재 스크립트와 검색 API가 공통으로 호출하는 HTTP 임베딩 서버.
- dense  : 1024d (정규화) → Milvus FLOAT_VECTOR / COSINE
- sparse : lexical_weights {token_id: weight} → Milvus SPARSE_FLOAT_VECTOR

실행:
    uvicorn app:app --host 0.0.0.0 --port 8000
환경변수:
    BGE_MODEL   기본 BAAI/bge-m3 (또는 로컬 경로)
    BGE_USE_FP16=1
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="bge-m3-embedding")

_MODEL_NAME = os.getenv("BGE_MODEL", "BAAI/bge-m3")
_model = None


def _get_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel

        _model = BGEM3FlagModel(
            _MODEL_NAME,
            use_fp16=os.getenv("BGE_USE_FP16", "1") == "1",
        )
    return _model


class EmbedRequest(BaseModel):
    texts: list[str]
    max_length: int = 8192
    batch_size: int = 16


class EmbedResponse(BaseModel):
    dense: list[list[float]]
    sparse: list[dict[int, float]]
    dim: int


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": _MODEL_NAME, "loaded": _model is not None}


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    out = _get_model().encode(
        req.texts,
        batch_size=req.batch_size,
        max_length=req.max_length,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )
    dense = [v.tolist() for v in out["dense_vecs"]]
    sparse = [
        {int(k): float(v) for k, v in w.items()} or {0: 0.0}
        for w in out["lexical_weights"]
    ]
    return EmbedResponse(dense=dense, sparse=sparse, dim=len(dense[0]) if dense else 0)
