FROM docker.io/python:3.11-slim@sha256:f5cf0344c9886ff24d34797578d5d7dd6e8911ae0fe5962bb55d0f89603ec361 AS builder

LABEL maintainer="Value Fabric Engineering"
LABEL description="Layer 7 — Billing Service"

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.6

WORKDIR /app

COPY services/layer7-billing/pyproject.toml ./pyproject.toml
RUN uv sync --no-install-project

COPY services/layer7-billing/src/ ./src/
COPY packages/shared/src/value_fabric/shared/ ./value_fabric/shared/

FROM docker.io/python:3.11-slim@sha256:f5cf0344c9886ff24d34797578d5d7dd6e8911ae0fe5962bb55d0f89603ec361 AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

# Upgrade base-image setuptools/wheel to remediate known CVEs flagged by Trivy
RUN pip install --no-cache-dir --upgrade setuptools wheel

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

COPY services/layer7-billing/src/ ./src/
COPY packages/shared/src/value_fabric/shared/ ./value_fabric/shared/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8008

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

CMD ["uvicorn", "layer7_billing.api.main:app", "--host", "0.0.0.0", "--port", "8008"]
