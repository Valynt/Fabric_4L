import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.fastapi_framework.health import CallableProbe, ProbeResult
from value_fabric.shared.observability.metrics_access import verify_metrics_access
from value_fabric.shared.observability.sentry_init import init_sentry
from value_fabric.shared.startup import reject_insecure_bypass_in_production

from app.core.audit import AuditMiddleware
from app.core.clerk_config import AUTH_PROVIDER_CLERK
from app.core.config import get_settings
from app.core.governance import add_gateway_governance_middleware
from app.core.metrics import metrics_middleware, render_metrics
from app.core.sla_middleware import ContractVersionMiddleware
from app.logging_config import configure_structured_logging
from app.routers import (
    accounts,
    agents,
    api_keys,
    auth,
    benchmarks,
    calculator,
    clerk_auth,
    clerk_webhooks,
    context_engine,
    drivers,
    evidence,
    governance,
    hypotheses,
    intelligence,
    jobs,
    layer_delegation,
    layer_proxy,
    privacy,
    product_endpoints,
    realization,
    reviews,
    usage,
    value_cases,
    versioning,
)
from app.services.distributed_store import (
    StorePayloadError,
    StoreUnavailableError,
    get_distributed_store,
)
from app.services.seed_data import seed_all

from .shared_bootstrap import (
    EnforcementControlConfig,
    EnforcementMode,
    EnforcementRolloutConfig,
    FrameworkIdempotencyConfig,
    FrameworkRateLimitConfig,
    create_fabric_app,
    register_health_endpoint,
    validate_production_safety,
)

# Configure structured logging
configure_structured_logging()
logger = structlog.get_logger(__name__)

settings = get_settings()

# Initialise Sentry before any other component (fail-safe, no-op without DSN)
init_sentry()


def _assert_database_ready() -> None:
    """Fail fast if the database is unreachable or misconfigured."""
    from app.core.database import create_database

    try:
        create_database()
    except Exception as exc:
        error_message = "FATAL: Database initialization failed."
        raise RuntimeError(error_message) from exc


def _assert_distributed_store_ready() -> None:
    """Fail fast if the distributed store is unreachable or serialization is incompatible."""
    try:
        get_distributed_store().validate_backend()
    except (StoreUnavailableError, StorePayloadError) as exc:
        distributed_store_error_message = (
            "FATAL: Distributed store initialization failed."
        )
        raise RuntimeError(distributed_store_error_message) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    _assert_database_ready()
    _assert_distributed_store_ready()
    reject_insecure_bypass_in_production(
        service_name="fabric-4l-api", settings=settings
    )
    validate_production_safety()
    if settings.seed_demo_data:
        seed_all()
    try:
        yield
    finally:
        from app.core.database import close_engine

        await close_engine()


async def _api_db_probe() -> ProbeResult:
    """Readiness probe for API gateway database."""
    try:
        from app.core.database import create_database

        create_database()
    except Exception as exc:
        logger.warning(
            "API gateway database readiness probe failed",
            dependency="database",
            status="unhealthy",
            error=str(exc),
        )
        return ProbeResult(
            name="database", healthy=False, detail="database:unavailable"
        )
    return ProbeResult(name="database", healthy=True)


async def _api_redis_probe() -> ProbeResult:
    """Readiness probe for API gateway distributed store (Redis)."""
    try:
        from app.services.distributed_store import get_distributed_store

        store = get_distributed_store()
        client = getattr(store, "client", None)
        if client is None:
            return ProbeResult(
                name="redis", healthy=False, detail="store_has_no_client"
            )
        await __import__("asyncio").to_thread(client.ping)
    except Exception as exc:
        logger.warning(
            "API gateway redis readiness probe failed",
            dependency="redis",
            status="unhealthy",
            error=str(exc),
        )
        return ProbeResult(name="redis", healthy=False, detail="redis:unavailable")
    return ProbeResult(name="redis", healthy=True)


async def _api_layer4_probe() -> ProbeResult:
    """Readiness probe for downstream Layer 4 agent orchestration service."""
    import httpx

    try:
        url = f"{settings.layer4_api_base_url.rstrip('/')}/ready"
        response = httpx.get(url, timeout=2.0)
        if response.status_code == 200:
            return ProbeResult(name="layer4", healthy=True)
        return ProbeResult(
            name="layer4", healthy=False, detail=f"layer4:status_{response.status_code}"
        )
    except Exception as exc:
        logger.warning(
            "API gateway Layer 4 readiness probe failed",
            dependency="layer4",
            status="unhealthy",
            error=str(exc),
        )
        return ProbeResult(name="layer4", healthy=False, detail="layer4:unavailable")


app = create_fabric_app(
    service_name="fabric-4l-api",
    title=settings.app_name,
    version="0.1.0",
    description="Fabric_4L unified API for value management",
    lifespan=lifespan,
    cors_policy=settings.cors_policy,
    health_probes=[
        CallableProbe(name="database", fn=_api_db_probe),
        CallableProbe(name="redis", fn=_api_redis_probe),
        CallableProbe(name="layer4", fn=_api_layer4_probe),
    ],
    readiness_path="/ready",
    enforcement_rollout=EnforcementRolloutConfig(
        tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.ENFORCE),
        rate_limiting=EnforcementControlConfig(mode=EnforcementMode.ENFORCE),
        idempotency=EnforcementControlConfig(mode=EnforcementMode.ENFORCE),
    ),
    enforce_tenant_context=True,
    instrument_telemetry=True,
    rate_limit=FrameworkRateLimitConfig(
        mode=EnforcementMode.ENFORCE,
        rate_limiter_factory=lambda: __import__(
            "value_fabric.shared.rate_limiting.tenant_rate_limiter",
            fromlist=["TenantRateLimiter"],
        ).TenantRateLimiter.create_from_env(),
    ),
    idempotency=FrameworkIdempotencyConfig(
        mode=EnforcementMode.ENFORCE,
        service_factory=lambda: __import__("value_fabric.shared.idempotency.core", fromlist=["IdempotencyService"]).IdempotencyService.create_from_env(),
        methods=frozenset({"POST", "PUT", "PATCH", "DELETE"}),
    ),
)

# Primary auth + tenant-context gate. create_fabric_app installs the tenant
# enforcement rollout control, but the canonical GovernanceMiddleware must be
# present for route dependencies to establish tenant context.
add_gateway_governance_middleware(app, rate_limiter=None)

app.include_router(accounts.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")
app.include_router(api_keys.router, prefix="/v1")
app.include_router(benchmarks.router, prefix="/v1")
app.include_router(usage.router, prefix="/v1")
app.include_router(product_endpoints.router, prefix="/v1")
app.include_router(jobs.router, prefix="/v1")

# Clerk routes are exposed only when the gateway is configured for Clerk auth.
# This prevents 500 responses from the Clerk dependency when AUTH_PROVIDER is set
# to a legacy mode and keeps the API surface consistent with runtime config.
if os.getenv("AUTH_PROVIDER", "clerk").strip().lower() == AUTH_PROVIDER_CLERK:
    app.include_router(clerk_auth.router, prefix="/v1")

app.include_router(intelligence.router, prefix="/v1")
app.include_router(intelligence.legacy_router, prefix="/v1")
app.include_router(hypotheses.router, prefix="/v1")
app.include_router(drivers.router, prefix="/v1")
app.include_router(evidence.router, prefix="/v1")
app.include_router(calculator.router, prefix="/v1")
app.include_router(value_cases.router, prefix="/v1")
app.include_router(context_engine.router, prefix="/v1")
app.include_router(governance.router, prefix="/v1")
app.include_router(reviews.router, prefix="/v1")
app.include_router(versioning.router, prefix="/v1")
app.include_router(realization.router, prefix="/v1")
app.include_router(agents.router, prefix="/v1")
app.include_router(privacy.router, prefix="/v1")

# Layer proxy routes - delegate to underlying layer services
app.include_router(layer_proxy.router, prefix="/v1")

# Fail-closed mapping for Layer 4 delegation failures (decision D2): the
# gateway never returns record-only success when the owning service is down.
from app.services.agent_orchestrator import (  # noqa: E402
    Layer4DependencyError,
    Layer4UnavailableError,
)


@app.exception_handler(Layer4UnavailableError)
async def _layer4_unavailable_handler(request, exc: Layer4UnavailableError):
    from fastapi.responses import JSONResponse as _JSONResponse

    return _JSONResponse(
        status_code=503,
        content={"detail": "layer4_unavailable", "code": exc.code},
    )


@app.exception_handler(Layer4DependencyError)
async def _layer4_dependency_handler(request, exc: Layer4DependencyError):
    from fastapi.responses import JSONResponse as _JSONResponse

    status = 404 if exc.status_code == 404 else 502
    return _JSONResponse(
        status_code=status,
        content={
            "detail": "layer4_dependency_error",
            "code": exc.code,
            "upstream_status": exc.status_code,
        },
    )


# Layer-segment delegation (decision D1/D2): registered last so the
# product-domain routers and layer_proxy above keep precedence. Serves
# frontend-generated /v1/{agents,ingest,extract,graph,truths}/* paths no
# other router owns.
app.include_router(layer_delegation.router, prefix="/v1")

# Clerk webhook handler is mounted unconditionally; the handler itself
# returns 503 when CLERK_WEBHOOK_SECRET is not configured. Network policy
# is responsible for restricting public access to /internal/*.
app.include_router(clerk_webhooks.router)

# Audit logging for all state-changing requests
app.add_middleware(AuditMiddleware)

# Contract/SLA version enforcement
app.add_middleware(ContractVersionMiddleware)

app.middleware("http")(metrics_middleware)
register_health_endpoint(app, service_name="fabric-4l-api")


@app.get("/metrics")
async def metrics(request: Request):
    # Metrics expose internal counters (tenant volume, error rates, build info).
    # Gate scraping to internal callers only, consistent with all other layers.
    if not verify_metrics_access(request):
        raise AuthorizationError(message="Metrics endpoint requires internal access")
    return render_metrics()
