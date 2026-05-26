from contextlib import asynccontextmanager

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
from app.services.seed_data import seed_all

from .shared_bootstrap import (
    create_fabric_app,
    register_health_endpoint,
    validate_production_safety,
)

settings = get_settings()


def _assert_database_ready() -> None:
    """Fail fast if the database is unreachable or misconfigured."""
    from app.core.database import create_database

    try:
        create_database()
    except Exception as exc:
        error_message = "FATAL: Database initialization failed."
        raise RuntimeError(error_message) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    _assert_database_ready()
    validate_production_safety()
    if settings.seed_demo_data:
        seed_all()
    yield


app = create_fabric_app(
    service_name="fabric-4l-api",
    title=settings.app_name,
    version="0.1.0",
    description="Fabric_4L unified API for value management",
    lifespan=lifespan,
    cors_policy=settings.cors_policy,
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
