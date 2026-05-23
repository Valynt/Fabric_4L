# syntax=docker/dockerfile:1
FROM python:3.11.13-slim-bookworm

# Security: Create non-root user early
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv from official image
RUN pip install --no-cache-dir uv==0.11.6

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies using uv (deterministic from lock file)
RUN uv sync --frozen --no-install-project

# Shared identity imports require additional runtime packages in the container.
RUN uv pip install "sqlalchemy>=2.0" "pyjwt>=2.8.0" "redis>=5.0"

# Copy source code
COPY src/ ./src/

# Set PATH to use uv virtual environment and PYTHONPATH for imports
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app:/app/src

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user before runtime
USER appuser

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8006"]
