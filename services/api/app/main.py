from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.audit import AuditMiddleware
from app.core.config import get_settings
from app.core.metrics import metrics_middleware, render_metrics
from app.routers import (
    accounts,
    agents,
    calculator,
    clerk_webhooks,
    context_engine,
    drivers,
    evidence,
    governance,
    hypotheses,
    intelligence,
    privacy,
    realization,
    reviews,
    value_cases,
    versioning,
)
from app.services.distributed_store import StorePayloadError, StoreUnavailableError, get_distributed_store
from app.services.seed_data import seed_all
from app.logging_config import configure_structured_logging

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
from value_fabric.shared.fastapi_framework.health import CallableProbe, ProbeResult, RedisHealthProbe

# Configure structured logging
configure_structured_logging()
logger = structlog.get_logger(__name__)

settings = get_settings()


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
        raise RuntimeError("FATAL: Distributed store initialization failed.") from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    _assert_database_ready()
    _assert_distributed_store_ready()
    validate_production_safety()
    if settings.seed_demo_data:
        seed_all()
    yield


async def _api_db_probe() -> ProbeResult:
    """Readiness probe for API gateway database."""
    try:
        from app.core.database import create_database
        create_database()
    except Exception as exc:
        return ProbeResult(name="database", healthy=False, detail=str(exc))
    return ProbeResult(name="database", healthy=True)


async def _api_redis_probe() -> ProbeResult:
    """Readiness probe for API gateway distributed store (Redis)."""
    try:
        from app.services.distributed_store import get_distributed_store
        store = get_distributed_store()
        client = getattr(store, "client", None)
        if client is None:
            return ProbeResult(name="redis", healthy=False, detail="store_has_no_client")
        await __import__("asyncio").to_thread(client.ping)
    except Exception as exc:
        return ProbeResult(name="redis", healthy=False, detail=str(exc))
    return ProbeResult(name="redis", healthy=True)


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
    ],
    readiness_path="/ready",
    enforcement_rollout=EnforcementRolloutConfig(
        tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.AUDIT),
        rate_limiting=EnforcementControlConfig(mode=EnforcementMode.ENFORCE),
        idempotency=EnforcementControlConfig(mode=EnforcementMode.ENFORCE),
    ),
    rate_limit=FrameworkRateLimitConfig(
        mode=EnforcementMode.ENFORCE,
        rate_limiter_factory=lambda: __import__("value_fabric.shared.rate_limiting.tenant_rate_limiter", fromlist=["TenantRateLimiter"]).TenantRateLimiter.create_from_env(),
    ),
    idempotency=FrameworkIdempotencyConfig(
        mode=EnforcementMode.ENFORCE,
        service_factory=lambda: __import__("value_fabric.shared.idempotency.core", fromlist=["IdempotencyService"]).IdempotencyService.create_from_env(),
        methods=frozenset({"POST", "PUT", "PATCH", "DELETE"}),
    ),
)

app.include_router(accounts.router, prefix="/v1")
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

# Clerk webhook handler is mounted unconditionally; the handler itself
# returns 503 when CLERK_WEBHOOK_SECRET is not configured. Network policy
# is responsible for restricting public access to /internal/*.
app.include_router(clerk_webhooks.router)

# Audit logging for all state-changing requests
app.add_middleware(AuditMiddleware)

app.middleware("http")(metrics_middleware)
register_health_endpoint(app, service_name="fabric-4l-api")


@app.get("/metrics")
async def metrics():
    return render_metrics()
