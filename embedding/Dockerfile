# BGE-M3 임베딩 서비스 (GPU).
# torch ≥2.6 필요 (최신 transformers가 .bin 로드 시 요구, CVE-2025-32434).
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# 모델 캐시 경로(볼륨 마운트 권장 → 재빌드 시 재다운로드 방지)
ENV HF_HOME=/models

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
