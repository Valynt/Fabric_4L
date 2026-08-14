# Multi-stage build for Layer 1: Data Ingestion Service
# Stage 1: Builder - installs dependencies and Playwright browsers
FROM docker.io/python:3.11-slim@sha256:28255a3ace7eb4c48bc1b57b90af29e1bc82b4fd6c60614a8e3dce61b87ff941 AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image
RUN pip install --no-cache-dir uv==0.11.6

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies using uv (creates .venv)
RUN uv sync --frozen --no-install-project

# Make venv available for subsequent commands in builder stage
ENV PATH="/app/.venv/bin:$PATH"

# Install Playwright browsers by default. Release-smoke builds can set
# INSTALL_PLAYWRIGHT_BROWSERS=false to keep the image lightweight when the
# validation path only needs the API process and health endpoints.
ARG INSTALL_PLAYWRIGHT_BROWSERS=true
RUN if [ "$INSTALL_PLAYWRIGHT_BROWSERS" = "true" ]; then \
        python -m playwright install chromium && \
        python -m playwright install-deps chromium; \
    else \
        mkdir -p /root/.cache/ms-playwright; \
    fi

# Stage 2: Runtime - minimal image with only runtime dependencies
FROM docker.io/python:3.11-slim@sha256:28255a3ace7eb4c48bc1b57b90af29e1bc82b4fd6c60614a8e3dce61b87ff941 AS runtime

# Install runtime dependencies (Playwright libs + curl for healthcheck)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    poppler-utils \
    tesseract-ocr \
    curl \
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
ENV PYTHONPATH=/app/src

# Copy Playwright browsers from builder
COPY --from=builder /root/.cache/ms-playwright /home/appuser/.cache/ms-playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright

# Copy application code
COPY src/ ./src/
COPY alembic.ini .
COPY migrations/ ./migrations/

# Change ownership
RUN chown -R appuser:appgroup /app /home/appuser

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "layer1_ingestion.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
