FROM docker.io/python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4 AS builder
WORKDIR /app
ENV UV_TORCH_BACKEND=cpu
RUN pip install --no-cache-dir uv==0.11.6
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

FROM docker.io/python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app:/app/src \
    UVICORN_CMD="uvicorn src.api.main:app --host 0.0.0.0 --port 8001"
COPY src/ ./src/
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

# Upgrade base-image setuptools/wheel to remediate known CVEs flagged by Trivy
RUN pip install --no-cache-dir --upgrade setuptools wheel \
    && pip uninstall --yes pip
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
