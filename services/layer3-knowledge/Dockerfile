# syntax=docker/dockerfile:1
FROM python@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1 AS builder
WORKDIR /app
ENV UV_TORCH_BACKEND=cpu
RUN pip install --no-cache-dir uv==0.11.6
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

FROM python@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/.venv /app/.venv
RUN pip install --no-cache-dir uv==0.11.6
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    UVICORN_CMD="uvicorn value_fabric.layer3.api.main:app --host 0.0.0.0 --port 8001"
COPY src/ ./src/
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1
CMD ["uvicorn", "value_fabric.layer3.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
