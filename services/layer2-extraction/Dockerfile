# syntax=docker/dockerfile:1
# Layer 2: Extraction Service - Deterministic build with uv
FROM python:3.11.13-slim-bookworm

# Security: Run as non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image
RUN pip install --no-cache-dir uv==0.11.6

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies using uv (deterministic from lock file)
RUN uv sync --frozen --no-install-project

# Copy application code
COPY src/ ./src/

# Set PATH to use uv virtual environment and PYTHONPATH for imports
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app:/app/src

# Change ownership to non-root user (including .venv)
RUN chown -R appuser:appgroup /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: Run the FastAPI application
CMD ["uvicorn", "src.layer2_extraction.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
