# Multi-stage build for Layer 4: Agentic Workflow Engine
# Stage 1: Builder - compiles dependencies
FROM docker.io/python:3.11-slim@sha256:d1e9ca7c4e78d1e8ecadb5d44bfc8e956e7a65b659a9950f569f243d72b326d0 AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image
RUN pip install --no-cache-dir uv==0.11.6

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (deterministic from lock file)
RUN uv sync --frozen --no-install-project

# Ensure email-validator is installed (runtime dep for pydantic email validation)
RUN uv pip install "email-validator>=2.1.0"

# Copy source code (separate layer for better caching)
COPY src/ ./src/
# Copy versioned prompt templates used by the workflow engine
COPY prompts/ ./src/prompts/
COPY config/ ./config/
COPY migrations/ ./migrations/
COPY alembic.ini ./alembic.ini
# value_fabric is mounted as a volume in docker-compose.dev.yml

# Stage 2: Runtime - minimal image with only runtime libraries
FROM docker.io/python:3.11-slim@sha256:d1e9ca7c4e78d1e8ecadb5d44bfc8e956e7a65b659a9950f569f243d72b326d0 AS runtime

# Install only runtime library (libpq for psycopg2)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with home directory
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

# Upgrade base-image setuptools/wheel to remediate known CVEs flagged by Trivy
RUN pip install --no-cache-dir --upgrade setuptools wheel \
    && pip uninstall --yes pip

WORKDIR /app

# Copy uv virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app:/app/src

# Copy source code from builder (separate layer for better caching)
COPY --from=builder /app/src ./src/
# Copy versioned prompt templates used by the workflow engine
COPY --from=builder /app/src/prompts ./src/prompts/
COPY --from=builder /app/config ./config/
COPY --from=builder /app/migrations ./migrations/
COPY --from=builder /app/alembic.ini ./alembic.ini
# value_fabric is mounted as a volume in docker-compose.dev.yml

# Change ownership
RUN chown -R appuser:appgroup /app /home/appuser

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API server
CMD ["uvicorn", "layer4_agents.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
