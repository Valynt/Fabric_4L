```dockerfile
# syntax=docker/dockerfile:1.6
# -----------------------------------------------------------------------------
# Layer 1: Data Ingestion Service — Enterprise Hardened
# -----------------------------------------------------------------------------

# Stage 1: Builder
FROM python@sha256:28255a3ace7eb4c48bc1b57b90af29e1bc82b4fd6c60614a8e3dce61b87ff941 AS builder

WORKDIR /app

RUN set -eux; \
    apt-get update; \
    apt-get upgrade -y; \
    apt-get install -y --no-install-recommends gcc libpq-dev curl; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /var/tmp/*

RUN pip install --no-cache-dir uv==0.11.6

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

ENV PATH="/app/.venv/bin:$PATH"

ARG INSTALL_PLAYWRIGHT_BROWSERS=true
RUN set -eux; \
    if [ "$INSTALL_PLAYWRIGHT_BROWSERS" = "true" ]; then \
        python -m playwright install chromium; \
        python -m playwright install-deps chromium; \
    else \
        mkdir -p /root/.cache/ms-playwright; \
    fi

# Stage 2: Runtime
FROM python@sha256:28255a3ace7eb4c48bc1b57b90af29e1bc82b4fd6c60614a8e3dce61b87ff941 AS runtime

RUN set -eux; \
    apt-get update; \
    apt-get upgrade -y; \
    apt-get install -y --no-install-recommends \
        libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
        libpango-1.0-0 libcairo2 libatspi2.0-0 poppler-utils \
        tesseract-ocr tini; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /var/tmp/*

RUN set -eux; \
    groupadd -r -g 1000 appgroup; \
    useradd -r -u 1000 -g appgroup -m -s /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder --chown=root:root /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright

COPY --from=builder --chown=appuser:appgroup /root/.cache/ms-playwright /home/appuser/.cache/ms-playwright

COPY --chown=root:root src/ ./src/
COPY --chown=root:root alembic.ini .
COPY --chown=root:root migrations/ ./migrations/

RUN set -eux; \
    find /app/src /app/migrations -type d -exec chmod 755 {} +; \
    find /app/src /app/migrations -type f -exec chmod 644 {} +; \
    chmod 644 /app/alembic.ini; \
    chown -R root:root /app; \
    chown -R appuser:appgroup /home/appuser/.cache; \
    chmod 700 /home/appuser/.cache; \
    pip install --no-cache-dir --upgrade setuptools wheel; \
    pip uninstall --yes pip; \
    rm -rf /usr/local/lib/python*/ensurepip; \
    rm -rf /usr/local/lib/python*/dist-packages/pip*; \
    rm -rf /usr/local/lib/python*/site-packages/pip*; \
    rm -f /usr/local/bin/pip*; \
    find / -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true; \
    rm -rf /root/.cache/pip /root/.local /tmp/* /var/tmp/*

USER appuser:appgroup

ENTRYPOINT ["/usr/bin/tini", "--"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

EXPOSE 8000

CMD ["uvicorn", "layer1_ingestion.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```