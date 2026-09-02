FROM docker.io/python:3.11-slim@sha256:f5cf0344c9886ff24d34797578d5d7dd6e8911ae0fe5962bb55d0f89603ec361 AS builder

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.6

WORKDIR /app

COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --frozen --no-install-project

RUN uv pip install "sqlalchemy>=2.0" "pyjwt>=2.8.0" "redis>=5.0"

COPY src/ ./src/

FROM docker.io/python:3.11-slim@sha256:f5cf0344c9886ff24d34797578d5d7dd6e8911ae0fe5962bb55d0f89603ec361 AS runtime

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

# Upgrade base-image setuptools/wheel to remediate known CVEs flagged by Trivy
RUN pip install --no-cache-dir --upgrade setuptools wheel \
    && pip uninstall --yes pip

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app:/app/src

COPY src/ ./src/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8006

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

CMD ["python", "-m", "uvicorn", "layer6_benchmarks.api.main:app", "--host", "0.0.0.0", "--port", "8006"]
