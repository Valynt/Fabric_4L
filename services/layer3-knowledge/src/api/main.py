from __future__ import annotations

"""Layer 3 FastAPI composition root.

This module is the sole application entry point for the Layer 3 Knowledge
Graph & Semantic Layer service. It owns:

- Application factory and lifespan
- Middleware wiring (CORS, request-ID, security, governance, rate-limiting,
  versioning, OpenTelemetry)
- Exception handler registration
- Router mounting for all V2 domain routers

No business logic lives here. All endpoint implementations are in
``api/routes/`` domain modules.
"""


import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from value_fabric.shared.fastapi_framework import (
    RouterMount,
    add_governance_middleware,
    add_security_validation_middleware,
    create_fabric_app,
    include_router_mounts,
    install_metrics_middleware,
    resolve_cors_policy,
)
from value_fabric.shared.fastapi_framework.health import CallableProbe, ProbeResult
from value_fabric.shared.identity.vault_check import is_vault_healthy
from value_fabric.shared.security import validate_production_safety
from value_fabric.shared.startup import reject_insecure_bypass_in_production

from src.config import Settings, get_settings
from src.logging_config import get_logger, setup_logging

from ..api.dependencies import close_app_state, init_app_state
from ..api.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
    ValueFabricException,
)
from ..api.metrics_state import set_app_metrics
from ..api.rate_limiter import add_rate_limiting
from ..api.routes import (
    agents,
    analytics,
    benchmarks,
    calculators,
    compat_aliases,
    competitive_intel,
    entities,
    evidence,
    formula_governance,
    formulas,
    graph_viz,
    ingestion,
    models,
    products,
    provenance_audit,
    roi_calculator,
    signals,
    system,
    value_packs,
    value_trees,
    variables,
)
from ..api.versioning import VersionMiddleware, get_version_compatibility

logger = get_logger(__name__)

_probe_app: list[FastAPI] = []
_security_config_l3: Any = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_migration_handler_with_policy(
    vc: Any,
    *,
    from_version: str,
    to_version: str,
    handler: Any,
    required: bool,
) -> None:
    try:
        vc.register_migration_handler(
            from_version=from_version, to_version=to_version, handler=handler
        )
    except Exception as exc:
        if required:
            logger.error(
                "Failed to register required migration handler %s: %s",
                getattr(handler, "__name__", handler),
                exc,
            )
            raise
        logger.warning(
            "Optional migration handler %s not registered: %s",
            getattr(handler, "__name__", handler),
            exc,
        )


def _exception_trace(exc: Exception) -> tuple:
    return (type(exc), exc, exc.__traceback__)


def _init_cache(settings: Settings) -> object | None:
    """Initialize Redis cache manager if enabled."""
    if not settings.cache_enabled:
        return None
    try:
        from ..cache import CacheConfig, initialize_cache

        cache_config = CacheConfig(
            default_ttl=settings.cache_default_ttl,
            max_ttl=settings.cache_max_ttl,
            key_prefix=settings.cache_key_prefix,
            serializer=settings.cache_serializer,
            compression=settings.cache_compression,
        )
        cache_manager = initialize_cache(
            redis_url=settings.cache_redis_url, config=cache_config
        )
        logger.info("Redis cache initialised")
        return cache_manager
    except (ImportError, ConnectionError, TimeoutError, OSError) as e:
        logger.warning("Cache unavailable: %s", e)
        return None


def _init_metrics(app: FastAPI, settings: Settings) -> object | None:
    """Initialize Prometheus metrics if enabled."""
    if not settings.metrics_enabled:
        return None
    try:
        from ..metrics import MetricsConfig, MetricsMiddleware, initialize_metrics

        metrics = initialize_metrics(
            MetricsConfig(
                enabled=True,
                prefix=settings.metrics_prefix,
                label_namespace=settings.metrics_namespace,
            )
        )
        logger.info("Prometheus metrics initialised")
        try:
            install_metrics_middleware(
                app,
                metrics=metrics,
                middleware_factory=MetricsMiddleware,
                logger=None,
            )
        except RuntimeError as exc:
            logger.warning("Skipping metrics middleware: %s", exc)
        return metrics
    except (ImportError, ConnectionError, RuntimeError, ValueError) as e:
        logger.warning("Metrics unavailable: %s", e)
        return None


def _init_versioning() -> object:
    """Initialize API versioning and register migration handlers."""
    from ..api.versioning import (
        initialize_versioning,
        migrate_v1_to_v2_ingestion_request,
        migrate_v1_to_v2_search_request,
        transform_v1_health_response,
        transform_v1_search_response,
    )

    version_compatibility = initialize_versioning("v1")
    _register_migration_handler_with_policy(
        version_compatibility,
        from_version="v1",
        to_version="v2",
        handler=migrate_v1_to_v2_search_request,
        required=True,
    )
    _register_migration_handler_with_policy(
        version_compatibility,
        from_version="v1",
        to_version="v2",
        handler=migrate_v1_to_v2_ingestion_request,
        required=True,
    )
    version_compatibility.register_response_transformer(
        "v1", "/v1/search", transform_v1_search_response
    )
    version_compatibility.register_response_transformer(
        "v1", "/health", transform_v1_health_response
    )
    logger.info("API versioning system initialised")
    return version_compatibility


async def _verify_production_vault() -> None:
    """Verify Vault connectivity when running in production."""
    if os.getenv("ENVIRONMENT", "development") == "production":
        vault_addr = os.getenv("VAULT_ADDR")
        if vault_addr:
            logger.info(
                "L3: Checking Vault connectivity", extra={"vault_addr": vault_addr}
            )
            if not await is_vault_healthy(vault_addr):
                raise RuntimeError(
                    "Vault unreachable — cannot start in production without secrets backend"
                )
            logger.info("L3: Vault connectivity verified")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    validate_production_safety()

    settings = get_settings()
    setup_logging(settings)
    if os.getenv("TESTING", "").lower() != "true":
        from ..retrieval.vector_store import Neo4jVectorStore

        Neo4jVectorStore(settings=settings)._get_embedding_model()
    logger.info(
        "Starting Value Fabric Knowledge Graph API",
        extra={"component": "layer3-knowledge", "version": "1.0.0"},
    )

    cache_manager = _init_cache(settings)
    metrics = _init_metrics(app, settings)
    version_compatibility = _init_versioning()

    app.state.cache_manager = cache_manager
    app.state.metrics = metrics
    app.state.version_compatibility = version_compatibility
    set_app_metrics(metrics)

    await _verify_production_vault()

    await init_app_state(app)
    yield

    # Shutdown
    logger.info("Shutting down Value Fabric Knowledge Graph API")
    if cache_manager:
        try:
            await cache_manager.disconnect()
            logger.info("Redis cache disconnected")
        except Exception as e:
            logger.warning("Error disconnecting cache: %s", e)
    await close_app_state(app)
    governance_redis_client = getattr(app.state, "governance_redis_client", None)
    if governance_redis_client is not None:
        await governance_redis_client.aclose()


# ---------------------------------------------------------------------------
# Service-specific middleware hook
# ---------------------------------------------------------------------------

try:
    _settings = get_settings()
except Exception:
    logger.warning("Falling back to default rate-limit settings during import")
    _settings = None


async def _neo4j_probe() -> ProbeResult:
    """Readiness probe for Neo4j connectivity."""
    if not _probe_app:
        return ProbeResult(name="neo4j", healthy=False, detail="app not initialized")
    app = _probe_app[0]
    app_state = getattr(app.state, "app_state", None)
    if app_state is None:
        return ProbeResult(
            name="neo4j", healthy=False, detail="app state not initialized"
        )
    if getattr(app_state, "neo4j_driver", None) is None:
        return ProbeResult(
            name="neo4j", healthy=False, detail="neo4j driver not connected"
        )
    return ProbeResult(name="neo4j", healthy=True)


async def _vector_store_probe() -> ProbeResult:
    """Readiness probe for Neo4j-native vector store (embedding + index availability)."""
    if not _probe_app:
        return ProbeResult(
            name="vector_store", healthy=False, detail="app not initialized"
        )
    app = _probe_app[0]
    app_state = getattr(app.state, "app_state", None)
    if app_state is None:
        return ProbeResult(
            name="vector_store", healthy=False, detail="app state not initialized"
        )
    if getattr(app_state, "vector_store", None) is None:
        return ProbeResult(
            name="vector_store", healthy=False, detail="vector_store not initialized"
        )
    return ProbeResult(name="vector_store", healthy=True)


def _post_core_middleware_hook(app: FastAPI) -> None:
    """Install service-specific middleware after framework core middleware."""
    global _security_config_l3
    _security_config_l3 = add_security_validation_middleware(
        app,
        skip_validation_paths={"/health", "/metrics", "/ready", "/live", "/v1/ingest"},
        strict_mode=True,
    )
    redis_rate_limiter = None
    try:
        import redis.asyncio as redis
        from value_fabric.shared.identity.rate_limiter import RedisRateLimiter

        if os.getenv("TESTING", "").lower() == "true":
            redis_rate_limiter = RedisRateLimiter()
        else:
            redis_client = redis.from_url(
                _settings.cache_redis_url if _settings else "redis://localhost:6379/0",
                decode_responses=True,
            )
            app.state.governance_redis_client = redis_client
            redis_rate_limiter = RedisRateLimiter(redis_client)
    except (ImportError, TypeError, ValueError) as exc:
        logger.error(
            "Redis-backed governance initialization failed (%s); tenant status "
            "will fail closed",
            type(exc).__name__,
        )
    add_governance_middleware(app, rate_limiter=redis_rate_limiter)
    # Safe defaults: rate limiting is ON when settings cannot be loaded so that
    # a misconfigured production deployment fails closed rather than unprotected.
    add_rate_limiting(
        app,
        requests_per_minute=(
            _settings.rate_limit_requests_per_minute if _settings else 100
        ),
        burst_size=_settings.rate_limit_burst_size if _settings else 200,
        enabled=_settings.rate_limit_enabled if _settings else True,
    )


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

reject_insecure_bypass_in_production(
    service_name="layer3-knowledge", settings=get_settings()
)

app = create_fabric_app(
    service_name="layer3-knowledge",
    title="Value Fabric - Knowledge Graph & Semantic Layer",
    description="""
## Layer 3: Knowledge Graph & Semantic Layer API

Provides intelligent semantic search, graph-based retrieval, and analytics
capabilities for enterprise AI workflows.
""",
    version="1.0.0",
    lifespan=lifespan,
    cors_policy=resolve_cors_policy(),
    register_default_exception_handlers=False,
    include_request_id_middleware=True,
    post_core_middleware_hook=_post_core_middleware_hook,
    telemetry_service_name="layer3-knowledge",
    instrument_telemetry=True,
    health_probes=[
        CallableProbe(name="neo4j", fn=_neo4j_probe),
        CallableProbe(name="vector_store", fn=_vector_store_probe),
    ],
    readiness_path="/ready",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "Value Fabric Team", "email": "value-fabric@example.com"},
    license_info={"name": "Proprietary", "url": "https://valuefabric.com/license"},
    enforce_tenant_context=True,
    openapi_tags=[
        {"name": "Health", "description": "Service health monitoring"},
        {"name": "Schema", "description": "Database schema management"},
        {"name": "Search", "description": "Entity search and discovery"},
        {"name": "GraphRAG", "description": "Graph-based question answering"},
        {"name": "Analytics", "description": "Graph analytics"},
        {"name": "Ingestion", "description": "Data ingestion and synchronisation"},
        {"name": "Value Trees", "description": "Value tree traversal"},
        {"name": "Formulas", "description": "Formula evaluation"},
        {"name": "Graph", "description": "Graph visualisation"},
        {"name": "Models", "description": "Value model management"},
        {"name": "Agents", "description": "Agentic workflow endpoints"},
        {"name": "Documents", "description": "Document export"},
    ],
)

_probe_app.append(app)

# Phase 1 Clerk integration: verify the Fabric4L internal AuthContext envelope.
# No-op when FABRIC_AUTH_PUBLIC_KEYS is unset.
from value_fabric.shared.identity.fabric_auth import (
    register_fabric_auth_from_env,  # noqa: E402
)

register_fabric_auth_from_env(app, service_name="layer3-knowledge")

app.middleware("http")(VersionMiddleware(get_version_compatibility()))


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Exception handlers (defined at module level for testability)
# ---------------------------------------------------------------------------


async def value_fabric_exception_handler(request: Request, exc: ValueFabricException):
    from fastapi.responses import JSONResponse

    status_code = 500
    if isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, AuthenticationError):
        status_code = 401
    elif isinstance(exc, AuthorizationError):
        status_code = 403
    elif exc.error_code == "NOT_FOUND":
        status_code = 404
    elif exc.error_code == "CONFLICT":
        status_code = 409
    elif isinstance(exc, RateLimitError):
        status_code = 429
    elif isinstance(exc, ServiceUnavailableError):
        status_code = 503
    response = JSONResponse(status_code=status_code, content=exc.to_dict())

    logger.error(
        "Value Fabric exception: %s at %s %s - %s",
        exc.error_code,
        request.method,
        request.url.path,
        exc.message,
        exc_info=_exception_trace(exc),
        extra={"trace_id": getattr(request.state, "trace_id", None)},
    )
    metrics = getattr(request.app.state, "metrics", None)
    if metrics:
        metrics.increment_errors(
            error_type=exc.error_code, component="api", namespace="layer3"
        )
    return response


async def http_exception_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse

    response = JSONResponse(status_code=exc.status_code, content=exc.detail)

    logger.warning(
        "HTTP exception %s at %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
        extra={"trace_id": getattr(request.state, "trace_id", None)},
    )
    return response


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    from fastapi.responses import JSONResponse

    response = JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )
    logger.warning(
        "Validation exception at %s %s",
        request.method,
        request.url.path,
        extra={"trace_id": getattr(request.state, "trace_id", None)},
    )
    return response


async def global_exception_handler(request: Request, exc: Exception):
    from fastapi.responses import JSONResponse

    response = JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "type": type(exc).__name__,
            "request_id": getattr(request.state, "request_id", None),
        },
    )

    logger.error(
        "Unhandled %s at %s %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc_info=_exception_trace(exc),
        extra={"trace_id": getattr(request.state, "trace_id", None)},
    )
    metrics = getattr(request.app.state, "metrics", None)
    if metrics:
        metrics.increment_errors(
            error_type=type(exc).__name__, component="api", namespace="layer3"
        )
    return response


# Register canonical error envelope handlers from shared package
try:
    from value_fabric.shared.error_handling.handlers import register_exception_handlers

    register_exception_handlers(app)
except ImportError:
    # Fallback to local handlers if shared package not available
    app.exception_handler(ValueFabricException)(value_fabric_exception_handler)
    app.exception_handler(HTTPException)(http_exception_handler)
    app.exception_handler(RequestValidationError)(validation_exception_handler)
    app.exception_handler(Exception)(global_exception_handler)


# ---------------------------------------------------------------------------
# Router mounting — V2 domain routers (canonical)
# ---------------------------------------------------------------------------

include_router_mounts(
    app,
    [
        # Operational
        RouterMount(system.router),
        # Domain routers
        RouterMount(value_trees.router, prefix="/v1"),
        RouterMount(formulas.router, prefix="/v1"),
        RouterMount(value_packs.router, prefix="/v1"),
        RouterMount(formula_governance.router, prefix="/v1"),
        RouterMount(variables.router, prefix="/v1"),
        RouterMount(models.router, prefix="/v1"),
        RouterMount(entities.router, prefix="/v1"),
        RouterMount(products.router, prefix="/v1"),
        RouterMount(evidence.router, prefix="/v1"),
        RouterMount(competitive_intel.router, prefix="/v1"),
        RouterMount(roi_calculator.router, prefix="/v1"),
        RouterMount(signals.router, prefix="/v1"),
        RouterMount(benchmarks.router, prefix="/v1/roi"),
        RouterMount(calculators.router, prefix="/v1"),
        RouterMount(provenance_audit.router),
        # V2 domain routers (ARCH-L3-011)
        RouterMount(ingestion.router),
        RouterMount(analytics.router),
        RouterMount(agents.router),
        RouterMount(graph_viz.router),
        # Compatibility aliases (deprecated, governed by deprecation phase)
        RouterMount(compat_aliases.router),
    ],
)


# ---------------------------------------------------------------------------
# Public re-exports (consumed by tests and the value_fabric.layer3 shim)
# ---------------------------------------------------------------------------

__all__ = [
    "_security_config_l3",
    "app",
    "close_app_state",
    "init_app_state",
    "lifespan",
    "global_exception_handler",
    "value_fabric_exception_handler",
]
