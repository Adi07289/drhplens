# DRHPLens FastAPI (serve) — Google Cloud Run image.
# SERVE deps only (fastembed/ONNX, no torch). Reads the committed cached data
# (data/forecasts, data/redflag, data/peers) — no ingest/ML stack.
FROM python:3.11-slim

# onnxruntime (fastembed's backend) needs libgomp1 on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the fastembed embedder + reranker at BUILD time — Cloud Run's
# runtime network can't fetch them from HuggingFace (models fail with "Could not
# load ... from any source"). Baked into the image; the app finds them at runtime
# via FASTEMBED_CACHE_DIR (read by tools/embedder.py + tools/reranker.py).
ENV FASTEMBED_CACHE_DIR=/opt/fastembed
RUN python -c "from fastembed import TextEmbedding; from fastembed.rerank.cross_encoder import TextCrossEncoder; TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/opt/fastembed'); TextCrossEncoder('Xenova/ms-marco-MiniLM-L-6-v2', cache_dir='/opt/fastembed')"

# App code + committed data caches (see .dockerignore for exclusions).
COPY . .

# Route model/tokenizer caches to a writable dir (Cloud Run fs is ephemeral).
ENV HOME=/tmp
# Give the remote Qdrant client headroom on a cold cluster.
ENV QDRANT_TIMEOUT=60

# Cloud Run injects $PORT (default 8080). Bind uvicorn to it.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
