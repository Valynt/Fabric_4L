from contextlib import asynccontextmanager

from fastapi import FastAPI

from .shared_bootstrap import (
    create_fabric_app,
    register_health_endpoint,
    validate_production_safety,
)

from app.core.audit import AuditMiddleware
from app.core.config import get_settings
from app.core.metrics import metrics_middleware, render_metrics
from app.routers import (
    accounts,
    agents,
    auth,
    calculator,
    context_engine,
    drivers,
    evidence,
    governance,
    hypotheses,
    intelligence,
    realization,
    reviews,
    value_cases,
    versioning,
)
from app.services.seed_data import seed_all

settings = get_settings()


def _assert_bcrypt_available() -> None:
    """Fail fast if bcrypt is not functional.

    Prevents the application from starting in a state where password hashing
    would silently fall back to an insecure algorithm.

    Uses passlib's identify() rather than a full hash round to avoid the
    bcrypt cost on every startup while still confirming the backend is loaded.
    """
    try:
        from app.core.security import pwd_context
        # identify() returns the scheme name for a known hash without computing
        # a new one — cheaper than a full bcrypt round.
        # A well-formed bcrypt hash (cost 4, known salt+digest) used only for
        # scheme identification — passlib.identify() checks the $2b$ prefix and
        # structure without verifying the password, so no bcrypt round is run.
        _BCRYPT_PROBE_HASH = (
            "$2b$04$aaaaaaaaaaaaaaaaaaaaaaaaaa"  # 22-char salt
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 31-char digest (padded)
        )
        scheme = pwd_context.identify(_BCRYPT_PROBE_HASH)
        if scheme != "bcrypt":
            raise RuntimeError(f"Expected bcrypt scheme, got: {scheme!r}")
    except Exception as exc:
        raise RuntimeError(
            "FATAL: bcrypt is not available or not functional. "
            "Install bcrypt and ensure the native library is present. "
            f"Original error: {exc}"
        ) from exc


def _assert_database_ready() -> None:
    """Fail fast if the database is unreachable or misconfigured."""
    from app.core.database import create_database

    try:
        create_database()
    except Exception as exc:
        raise RuntimeError(
            f"FATAL: Database initialization failed: {exc}"
        ) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    _assert_bcrypt_available()
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

app.include_router(auth.router, prefix="/v1")
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

# Audit logging for all state-changing requests
app.add_middleware(AuditMiddleware)

app.middleware("http")(metrics_middleware)
register_health_endpoint(app, service_name="fabric-4l-api")


@app.get("/metrics")
async def metrics():
    return render_metrics()
