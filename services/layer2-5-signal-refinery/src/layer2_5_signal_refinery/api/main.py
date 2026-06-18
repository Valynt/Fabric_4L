from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from value_fabric.shared.probes import normalize_probe_payload
from value_fabric.shared.fastapi_framework import create_fabric_app, CallableProbe, ProbeResult
from value_fabric.shared.fastapi_framework.middleware import resolve_cors_policy
from value_fabric.shared.startup import reject_insecure_bypass_in_production

from ..clients.l3_graph_client import get_l3_client
from ..config import get_settings
from ..database import close_db, init_db
from ..logging_config import configure_structured_logging
from .routes.signals import router as signals_router

"""Layer 2.5 Signal Refinery — FastAPI application.

Run with:
  uvicorn layer2_5_signal_refinery.api.main:app --host 0.0.0.0 --port 8007 --reload

Port: 8007
"""

# Configure structured logging
configure_structured_logging()
logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Health probes
# ---------------------------------------------------------------------------

async def _probe_database() -> ProbeResult:
    from sqlalchemy import text
    from ..database import get_engine
    try:
        # Infrastructure connectivity check only — no tenant context. A health
        # probe must not open a tenant-scoped session (db_session_for_context),
        # so it connects at the engine level and runs a read-only SELECT 1.
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return ProbeResult(name="database", healthy=True, detail="postgresql:ok")
    except Exception as exc:
        logger.warning("Database health probe failed", exc_info=exc)
        return ProbeResult(name="database", healthy=False, detail="postgresql:unavailable")


async def _probe_l3_client() -> ProbeResult:
    try:
        l3_client = get_l3_client()
        if l3_client is None:
            return ProbeResult(name="l3_client", healthy=False, detail="l3_client:not_initialized")
        return ProbeResult(name="l3_client", healthy=True, detail="l3_client:ok")
    except Exception as exc:
        logger.warning("L3 client health probe failed", exc_info=exc)
        return ProbeResult(name="l3_client", healthy=False, detail="l3_client:unavailable")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting L2.5 Signal Refinery (env=%s)", settings.environment)
    await init_db()
    yield
    await close_db()
    await get_l3_client().aclose()
    logger.info("L2.5 Signal Refinery shut down")


# ---------------------------------------------------------------------------
# Middleware hooks
# ---------------------------------------------------------------------------


def _post_core_middleware_hook(app: FastAPI) -> None:
    try:
        from value_fabric.shared.identity.middleware import GovernanceMiddleware
        from value_fabric.shared.security import SecurityConfig, add_security_middleware

        app.add_middleware(
            GovernanceMiddleware,
            api_key_resolver=None,
            rate_limiter=None,
        )
        security_config = SecurityConfig.from_env(
            skip_validation_paths=frozenset({"/health", "/metrics", "/ready"}),
            strict_mode=True,
        )
        add_security_middleware(app, config=security_config)
        logger.info("Governance middleware loaded from value_fabric.shared")
    except ImportError as exc:
        raise RuntimeError(
            "FATAL: value_fabric.shared is required for secure configuration. "
            "Install the shared package or set security config explicitly."
        ) from exc


def _health_augmentation_hook(app: FastAPI) -> None:
    settings = get_settings()

    @app.get("/health", include_in_schema=False)
    @app.get("/health/live", include_in_schema=False)
    async def health() -> dict[str, Any]:
        return normalize_probe_payload(
            status="ok",
            service="layer2-5-signal-refinery",
            extra={
                "version": "0.1.0",
                "environment": settings.environment,
            },
        )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> str:
        return ""


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    settings = get_settings()
    reject_insecure_bypass_in_production(service_name="layer2-5-signal-refinery", settings=settings)

    app = create_fabric_app(
        service_name="layer2-5-signal-refinery",
        title="Layer 2.5: Signal Refinery",
        description=(
            "Turns L2 extraction output into trusted, evidence-backed ValueSignal objects. "
            "Provides CRUD, review, promote, and refinement endpoints."
        ),
        version="0.1.0",
        lifespan=lifespan,
        cors_policy=resolve_cors_policy(),
        post_core_middleware_hook=_post_core_middleware_hook,
        health_probes=[
            CallableProbe(name="database", fn=_probe_database),
            CallableProbe(name="l3_client", fn=_probe_l3_client),
        ],
        readiness_path="/ready",
        health_readiness_augmentation_hook=_health_augmentation_hook,
        enforce_tenant_context=True,
        docs_url="/docs",
        redoc_url="/redoc",
        telemetry_service_name="layer2-5-signal-refinery",
        instrument_telemetry=True,
    )

    # Routes
    app.include_router(signals_router)

    return app


app = create_app()
