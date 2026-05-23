# syntax=docker/dockerfile:1
FROM python:3.11.13-slim-bookworm

LABEL maintainer="Value Fabric Engineering"
LABEL description="Layer 2.5 — Signal Refinery Service"

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.6

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-install-project 2>/dev/null || uv sync --no-install-project

COPY src/ ./src/
COPY alembic.ini .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app:/app/src

RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8007

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

CMD ["uvicorn", "layer2_5_signal_refinery.api.main:app", "--host", "0.0.0.0", "--port", "8007"]
