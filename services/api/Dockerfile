# syntax=docker/dockerfile:1
FROM python@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.6

WORKDIR /app

COPY services/api/pyproject.toml .
COPY services/api/uv.lock .
RUN uv sync --frozen --no-install-project

COPY services/api/app/ ./app/
COPY services/api/migrations/ ./migrations/
COPY packages/shared/src/value_fabric/ ./value_fabric/

FROM python@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93 AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

# Upgrade base-image setuptools/wheel to remediate known CVEs flagged by Trivy
RUN pip install --no-cache-dir --upgrade setuptools wheel

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

COPY services/api/app/ ./app/
COPY services/api/migrations/ ./migrations/
COPY packages/shared/src/value_fabric/ ./value_fabric/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
