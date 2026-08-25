"""FastAPI application factory for Layer 2 extraction service.

Configures middleware, health/readiness probes, exception handlers,
lifespan hooks, and routes.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import AsyncGenerator, Awaitable, Callable

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]
import structlog
from fastapi import FastAPI, Request, Response
from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.fastapi_framework import (
    EnforcementControlConfig,
    EnforcementMode,
    EnforcementRolloutConfig,
    HealthChecksConfig,
)
from value_fabric.shared.fastapi_framework.health import (
    CallableProbe,
    ProbeResult,
    RedisHealthProbe,
)
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.startup import reject_insecure_bypass_in_production

from layer2_extraction.api import s2s_auth
from layer2_extraction.api._shared import _is_strict_runtime
from layer2_extraction.api.routes import health as health_routes
from layer2_extraction.api.routes.signal_lifecycle import (
    router as signal_lifecycle_router,
)
from layer2_extraction.api.routes_extract import router as extract_router
from layer2_extraction.api.websocket import get_pipeline_ws_manager
from layer2_extraction.integration.layer3_client import Layer3KnowledgeClient
from layer2_extraction.integration.pending_ingestion_store import (
    PendingIngestionStore,
    build_pending_ingestion_store,
)
from layer2_extraction.integration.quarantine_store import (
    QuarantineStore,
    build_quarantine_store,
)
from layer2_extraction.metrics import get_metrics
from layer2_extraction.shared_bootstrap import (
    create_fabric_app,
    register_health_endpoint,
    verify_metrics_access,
)

logger = structlog.get_logger(__name__)


# Bootstrap Infisical secrets on import (optional in dev, required in prod)
def _bootstrap_secrets() -> None:
    """Load secrets from Infisical if available (optional in dev, required in prod)."""
    try:
        from value_fabric.shared.secrets import load_infisical_secrets

        load_infisical_secrets()
    except Exception as exc:
        from value_fabric.shared.environment import (
            get_service_environment,
            is_production_like_environment,
        )

        _secret_env = get_service_environment("layer2")
        logger.warning("Failed to load Infisical secrets (dev mode): %s", exc)
        if is_production_like_environment(_secret_env):
            raise RuntimeError(
                "Failed to load Infisical secrets in production-like Layer 2 runtime"
            ) from exc


_bootstrap_secrets()

# App start time for uptime calculation
_app_start_time = time.time()

# WebSocket manager for real-time pipeline streaming
_ws_manager = get_pipeline_ws_manager()

_S2S_INTERNAL_PATHS = s2s_auth.S2S_INTERNAL_PATHS

_TENANT_CONTEXT_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/health/live",
        "/ready",
        "/readiness",
    }
)


def _get_active_pending_ingestion_store() -> PendingIngestionStore:
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "pending_ingestion_store"):
        return main_mod.pending_ingestion_store
    return build_pending_ingestion_store()


def _get_active_quarantine_store() -> QuarantineStore:
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "quarantine_store"):
        return main_mod.quarantine_store
    return build_quarantine_store()


def _get_active_layer3_client_class():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "Layer3KnowledgeClient"):
        return main_mod.Layer3KnowledgeClient
    return Layer3KnowledgeClient


def _get_active_metrics():
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if main_mod and hasattr(main_mod, "get_metrics"):
        return main_mod.get_metrics()
    return get_metrics()


async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown."""
    logger.info("Layer2 extraction service starting up")
    yield
    logger.info("Layer2 extraction service shutting down")


async def _pending_ingestion_probe() -> ProbeResult:
    """Readiness probe for the pending-ingestion store."""
    return await health_routes.pending_ingestion_probe(_get_active_pending_ingestion_store())


async def _quarantine_probe() -> ProbeResult:
    """Readiness probe for the quarantine store."""
    return await health_routes.quarantine_probe(_get_active_quarantine_store())


class health_checkResult(TypedDictModel):
    dependencies: dict[str, object]
    metrics: dict[str, object]
    response_time_ms: float
    service: str
    status: str
    timestamp: str
    uptime_seconds: float
    version: str


def create_app() -> FastAPI:
    """Create and configure the Layer 2 FastAPI application."""
    _bootstrap_secrets()
    reject_insecure_bypass_in_production(service_name="layer2-extraction")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = None
    try:
        import redis.asyncio as _redis_async

        redis_client = _redis_async.Redis.from_url(redis_url, decode_responses=True)
    except Exception:
        pass

    app = create_fabric_app(
        service_name="layer2-extraction",
        title="Layer 2 Extraction Service",
        version="1.0.0",
        description="Extraction pipeline for entities and relationships from content",
        lifespan=lifespan,
        health_probes=[
            RedisHealthProbe(name="redis", _client=redis_client),
            CallableProbe(name="pending_ingestion_store", fn=_pending_ingestion_probe),
            CallableProbe(name="quarantine_store", fn=_quarantine_probe),
        ],
        readiness_path="/ready",
        enforcement_rollout=EnforcementRolloutConfig(
            tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.ENFORCE),
            health_checks=HealthChecksConfig(route_opt_out_paths=_TENANT_CONTEXT_EXEMPT_PATHS),
        ),
        enforce_tenant_context=True,
        instrument_telemetry=True,
    )

    register_health_endpoint(app, service_name="layer2-extraction")

    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=None,
        rate_limiter=None,
    )
    logger.info("GovernanceMiddleware installed", component="layer2-extraction")

    if _is_strict_runtime() and not os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "").strip():
        raise RuntimeError(
            "FABRIC_AUTH_PUBLIC_KEYS is required in strict environments for Layer 2 authentication."
        )

    try:
        from value_fabric.shared.error_handling import register_exception_handlers

        register_exception_handlers(app)
    except ImportError:
        pass

    app.include_router(signal_lifecycle_router)

    @app.middleware("http")
    async def _s2s_auth_guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Enforce inbound S2S JWT on internal extraction routes."""
        return await s2s_auth.enforce_s2s_auth_guard(
            request,
            call_next,
            is_strict_runtime=_is_strict_runtime,
        )

    @app.get("/health")
    async def health_check():
        """Health check endpoint with real metrics and dependency status."""
        metrics = _get_active_metrics()
        layer3_client_cls = _get_active_layer3_client_class()
        payload = await health_routes.build_health_payload(
            app_start_time=_app_start_time,
            metrics=metrics,
            layer3_client_factory=layer3_client_cls,
            psutil_module=psutil,
        )
        return health_checkResult.model_validate(payload)

    @app.get("/metrics")
    async def metrics_endpoint(request: Request):
        """Prometheus metrics endpoint."""
        if not verify_metrics_access(request):
            raise AuthorizationError(message="Metrics endpoint requires internal access")

        metrics = _get_active_metrics()
        if not metrics:
            return Response(
                content="# Metrics collection is disabled",
                status_code=503,
                media_type="text/plain",
            )

        try:
            metrics_data = metrics.get_metrics()
            return Response(
                content=metrics_data,
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except Exception:
            logger.exception("Failed to collect metrics")
            return Response(
                content="# Error collecting metrics",
                status_code=500,
                media_type="text/plain",
            )

    app.include_router(extract_router)

    return app
