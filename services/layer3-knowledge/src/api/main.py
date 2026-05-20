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

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from value_fabric.layer3.config import get_settings
from value_fabric.layer3.logging_config import get_logger, setup_logging
from value_fabric.shared.fastapi_framework import (
    RouterMount,
    add_governance_middleware,
    add_request_id_middleware,
    add_security_validation_middleware,
    include_router_mounts,
    resolve_cors_policy,
)
from value_fabric.shared.identity.vault_check import is_vault_healthy
from value_fabric.shared.security import validate_production_safety

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
    documents,
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
    system,
    value_packs,
    value_trees,
    variables,
)
from ..api.telemetry import (
    OTEL_AVAILABLE,
    SERVICE_NAME,
    BatchSpanProcessor,
    FastAPIInstrumentor,
    OTLPSpanExporter,
    Resource,
    TracerProvider,
    trace,
)
from ..api.versioning import VersionMiddleware, get_version_compatibility

logger = get_logger(__name__)

_tracer_provider: Any | None = None


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------


def init_telemetry() -> Any | None:
    """Initialise OpenTelemetry tracing if an OTLP endpoint is configured."""
    if not OTEL_AVAILABLE:
        logger.debug("OpenTelemetry not available (module not installed)")
        return None

    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otel_endpoint:
        return None

    resource = Resource.create({SERVICE_NAME: "layer3-knowledge"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{otel_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


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


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    global _tracer_provider

    validate_production_safety()

    _tracer_provider = init_telemetry()
    if _tracer_provider:
        logger.info("L3: OpenTelemetry tracing initialised")

    settings = get_settings()
    setup_logging(settings)
    logger.info(
        "Starting Value Fabric Knowledge Graph API",
        extra={"component": "layer3-knowledge", "version": "1.0.0"},
    )

    # Cache
    cache_manager = None
    try:
        from ..cache import CacheConfig, initialize_cache

        if settings.cache_enabled:
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
    except (ImportError, ConnectionError, TimeoutError, OSError) as e:
        logger.warning("Cache unavailable: %s", e)

    # Metrics
    metrics = None
    try:
        from ..metrics import MetricsConfig, MetricsMiddleware, initialize_metrics

        if settings.metrics_enabled:
            metrics = initialize_metrics(
                MetricsConfig(
                    enabled=True,
                    prefix=settings.metrics_prefix,
                    label_namespace=settings.metrics_namespace,
                )
            )
            logger.info("Prometheus metrics initialised")
            if not getattr(app.state, "_metrics_middleware_installed", False):
                try:
                    app.middleware("http")(MetricsMiddleware(metrics))
                    app.state._metrics_middleware_installed = True
                except RuntimeError as exc:
                    logger.warning("Skipping metrics middleware: %s", exc)
    except (ImportError, ConnectionError, RuntimeError, ValueError) as e:
        logger.warning("Metrics unavailable: %s", e)

    # Versioning
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

    app.state.cache_manager = cache_manager
    app.state.metrics = metrics
    app.state.version_compatibility = version_compatibility
    set_app_metrics(metrics)

    # Production Vault gate
    if os.getenv("ENVIRONMENT", "development") == "production":
        vault_addr = os.getenv("VAULT_ADDR")
        if vault_addr:
            logger.info("L3: Checking Vault connectivity", extra={"vault_addr": vault_addr})
            if not await is_vault_healthy(vault_addr):
                raise RuntimeError(
                    "Vault unreachable — cannot start in production without secrets backend"
                )
            logger.info("L3: Vault connectivity verified")

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


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def _create_app() -> FastAPI:
    return FastAPI(
        title="Value Fabric - Knowledge Graph & Semantic Layer",
        description="""
## Layer 3: Knowledge Graph & Semantic Layer API

Provides intelligent semantic search, graph-based retrieval, and analytics
capabilities for enterprise AI workflows.
""",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "Value Fabric Team", "email": "value-fabric@example.com"},
        license_info={"name": "Proprietary", "url": "https://valuefabric.com/license"},
        lifespan=lifespan,
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


app = _create_app()

# OpenTelemetry instrumentation (after app creation)
if OTEL_AVAILABLE and os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    FastAPIInstrumentor.instrument_app(app)
    logger.info("L3: FastAPI instrumented with OpenTelemetry")


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

_cors_policy = resolve_cors_policy()
app.add_middleware(CORSMiddleware, **_cors_policy.as_kwargs())

add_request_id_middleware(app)

_security_config_l3 = add_security_validation_middleware(
    app,
    skip_validation_paths={"/health", "/metrics"},
    strict_mode=True,
)

add_governance_middleware(app)

try:
    _settings = get_settings()
except Exception:
    logger.warning("Falling back to default rate-limit settings during import")
    _settings = None

# Safe defaults: rate limiting is ON when settings cannot be loaded so that
# a misconfigured production deployment fails closed rather than unprotected.
add_rate_limiting(
    app,
    requests_per_minute=_settings.rate_limit_requests_per_minute if _settings else 100,
    burst_size=_settings.rate_limit_burst_size if _settings else 200,
    enabled=_settings.rate_limit_enabled if _settings else True,
)

app.middleware("http")(VersionMiddleware(get_version_compatibility()))


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(ValueFabricException)
async def value_fabric_exception_handler(request: Request, exc: ValueFabricException):
    try:
        from value_fabric.shared.error_handling.handlers import (
            value_fabric_exception_handler as shared_handler,
        )
        response = await shared_handler(request, exc)
    except ImportError:
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    try:
        from value_fabric.shared.error_handling.handlers import (
            http_exception_handler as shared_handler,
        )
        response = await shared_handler(request, exc)
    except ImportError:
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    from value_fabric.shared.error_handling.handlers import (
        validation_exception_handler as shared_handler,
    )
    response = await shared_handler(request, exc)
    logger.warning(
        "Validation exception at %s %s",
        request.method,
        request.url.path,
        extra={"trace_id": getattr(request.state, "trace_id", None)},
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    try:
        from value_fabric.shared.error_handling.handlers import (
            global_exception_handler as shared_handler,
        )
        response = await shared_handler(request, exc)
    except ImportError:
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
        "Unhandled %s at %s %s: %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        str(exc),
        exc_info=_exception_trace(exc),
        extra={"trace_id": getattr(request.state, "trace_id", None)},
    )
    metrics = getattr(request.app.state, "metrics", None)
    if metrics:
        metrics.increment_errors(
            error_type=type(exc).__name__, component="api", namespace="layer3"
        )
    return response


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
        RouterMount(benchmarks.router, prefix="/v1/roi"),
        RouterMount(calculators.router, prefix="/v1"),
        RouterMount(provenance_audit.router),
        # V2 domain routers (ARCH-L3-011)
        RouterMount(ingestion.router),
        RouterMount(analytics.router),
        RouterMount(agents.router),
        RouterMount(graph_viz.router),
        RouterMount(documents.router),
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
    "init_telemetry",
    "lifespan",
]
