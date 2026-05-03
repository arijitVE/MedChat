FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install core dependencies for HDMIS Pipeline A
RUN pip install --no-cache-dir \
    fastapi uvicorn sqlalchemy pydantic pydantic-settings \
    celery redis structlog rapidfuzz sentence-transformers \
    google-cloud-vision pymupdf psycopg2-binary alembic python-multipart

COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
