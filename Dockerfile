# multi-stage build untuk optimasi ukuran image
FROM python:3.12-slim AS builder

WORKDIR /app

# install system dependencies untuk build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy requirements dan install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# final stage
FROM python:3.12-slim

WORKDIR /app

# copy Python dependencies dari builder
COPY --from=builder /root/.local /root/.local

# install runtime dependencies (jika ada)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# copy aplikasi
COPY app/ ./app/
COPY artifacts/ ./artifacts/

# pastikan PATH include user local bin
ENV PATH=/root/.local/bin:$PATH

# expose port
EXPOSE 8000

# health check menggunakan curl (lebih ringan dari requests)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# run aplikasi — PORT dari Render, fallback 8000 untuk lokal
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]