"""Layer 2.5 Signal Refinery — FastAPI application.

Run with:
  uvicorn layer2_5_signal_refinery.api.main:app --host 0.0.0.0 --port 8007 --reload

Port: 8007
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from value_fabric.shared.startup import reject_insecure_bypass_in_production

from ..clients.l3_graph_client import get_l3_client
from ..config import get_settings
from ..database import close_db, init_db
from .routes.signals import router as signals_router

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ---------------------------------------------------------------------------
# Governance middleware (optional — graceful fallback)
# ---------------------------------------------------------------------------

def _add_governance_middleware(app: FastAPI) -> None:
    try:
        from value_fabric.shared.identity.middleware import GovernanceMiddleware
        from value_fabric.shared.security import SecurityConfig, add_security_middleware
        from value_fabric.shared.fastapi_framework.middleware import resolve_cors_policy

        app.add_middleware(
            GovernanceMiddleware,
            api_key_resolver=None,
            rate_limiter=None,
        )
        security_config = SecurityConfig.from_env(
            skip_validation_paths=frozenset({"/health", "/metrics"}),
            strict_mode=True,
        )
        add_security_middleware(app, config=security_config)
        app.add_middleware(CORSMiddleware, **resolve_cors_policy().as_kwargs())
        logger.info("Governance middleware loaded from value_fabric.shared")
    except ImportError as exc:
        raise RuntimeError(
            "FATAL: value_fabric.shared is required for secure CORS configuration. "
            "Running without governance middleware is not permitted. "
            "Install the shared package or set CORS_ORIGINS explicitly."
        ) from exc


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
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    settings = get_settings()
    reject_insecure_bypass_in_production(service_name="layer2-5-signal-refinery", settings=settings)

    app = FastAPI(
        title="Layer 2.5: Signal Refinery",
        description=(
            "Turns L2 extraction output into trusted, evidence-backed ValueSignal objects. "
            "Provides CRUD, review, promote, and refinement endpoints."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    _add_governance_middleware(app)

    # Routes
    app.include_router(signals_router)

    # Health
    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "layer2-5-signal-refinery",
            "version": "0.1.0",
            "environment": settings.environment,
        }

    # Metrics stub
    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> str:
        return ""

    return app


app = create_app()
