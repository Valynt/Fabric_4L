"""
Layer 5 Ground Truth — FastAPI application entry point.

Run with:
  uvicorn layer5_ground_truth.api.main:app --host 0.0.0.0 --port 8005 --reload

Or via Docker:
  docker compose up layer5-ground-truth

"""

import inspect
import logging
import re
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from layer5_ground_truth import __version__

from ..shared_bootstrap import (
    SecurityConfig,
    add_security_middleware,
    create_fabric_app,
    install_metrics_middleware,
    resolve_cors_policy,
    validate_production_safety,
    verify_metrics_access,
)

is_vault_healthy: Callable[[str], Awaitable[bool] | bool] | None

try:
    from value_fabric.shared.identity.vault_check import is_vault_healthy
except ImportError:
    is_vault_healthy = None

from metrics import MetricsMiddleware, get_metrics, initialize_metrics

from ..config import get_settings
from ..database import close_db, init_db
from ..integration.layer3_client import (
    Layer3ClientError,
    Layer3PolicyDeniedError,
    Layer3TenantMismatchError,
)
from .router import router
from .schemas import HealthResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
SECURITY_ERROR_CODES = frozenset(
    {
        "AUTH_REQUIRED",
        "AUTH_INVALID_TOKEN",
        "AUTH_TOKEN_EXPIRED",
        "AUTH_INVALID_TENANT",
        "AUTH_HEADER_TENANT_MISMATCH",
        "INSUFFICIENT_SCOPE",
    }
)


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
ALEMBIC_INI_PATH = MIGRATIONS_DIR.parents[1] / "alembic.ini"


async def _check_database_connectivity() -> None:
    """Raise if the readiness database probe cannot establish a connection."""
    from sqlalchemy import text

    from ..database import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


def _get_expected_migration_heads() -> tuple[str, ...]:
    """Return the Alembic head revision(s) declared by Layer 5 migrations."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    alembic_cfg = Config(str(ALEMBIC_INI_PATH))
    alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(alembic_cfg)
    return tuple(script.get_heads())


async def _get_database_migration_heads() -> tuple[str, ...]:
    """Return the current Alembic head revision(s) recorded in the database."""
    from alembic.migration import MigrationContext

    from ..database import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        return tuple(
            await conn.run_sync(
                lambda sync_conn: MigrationContext.configure(
                    sync_conn
                ).get_current_heads()
            )
        )


async def _check_schema_migration_alignment() -> dict[str, object]:
    """Return the readiness state for DB Alembic revision alignment."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    expected_heads = _get_expected_migration_heads()
    alembic_cfg = Config(str(ALEMBIC_INI_PATH))
    alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(alembic_cfg)

    if len(expected_heads) != 1:
        logger.error(
            "Layer 5 readiness requires a single Alembic head, found %s", expected_heads
        )
        return {
            "ready": False,
            "schema": "inconsistent",
            "reason": "schema_revision_inconsistent",
            "current_revisions": [],
            "expected_heads": sorted(expected_heads),
        }

    expected_head = expected_heads[0]

    try:
        current_heads = await _get_database_migration_heads()
    except Exception as exc:
        logger.warning(
            "Readiness schema probe could not determine Alembic revision: %s", exc
        )
        return {
            "ready": False,
            "schema": "inconsistent",
            "reason": "schema_revision_inconsistent",
            "current_revisions": [],
            "expected_heads": [expected_head],
        }

    if not current_heads:
        return {
            "ready": False,
            "schema": "behind",
            "reason": "schema_revision_behind",
            "current_revisions": [],
            "expected_heads": [expected_head],
        }

    if len(current_heads) != 1:
        return {
            "ready": False,
            "schema": "inconsistent",
            "reason": "schema_revision_inconsistent",
            "current_revisions": sorted(current_heads),
            "expected_heads": [expected_head],
        }

    current_head = current_heads[0]
    if current_head == expected_head:
        return {
            "ready": True,
            "schema": "aligned",
            "reason": "schema_aligned",
            "current_revisions": [current_head],
            "expected_heads": [expected_head],
        }

    try:
        current_revision = script.get_revision(current_head)
    except Exception:
        logger.warning(
            "Layer 5 readiness found Alembic revision outside known history: current=%s expected=%s",
            current_head,
            expected_head,
        )
        return {
            "ready": False,
            "schema": "inconsistent",
            "reason": "schema_revision_inconsistent",
            "current_revisions": [current_head],
            "expected_heads": [expected_head],
        }

    if current_revision is None:
        return {
            "ready": False,
            "schema": "inconsistent",
            "reason": "schema_revision_inconsistent",
            "current_revisions": [current_head],
            "expected_heads": [expected_head],
        }

    try:
        for revision in script.walk_revisions(base="base", head=expected_head):
            if revision.revision == current_head:
                return {
                    "ready": False,
                    "schema": "behind",
                    "reason": "schema_revision_behind",
                    "current_revisions": [current_head],
                    "expected_heads": [expected_head],
                }
    except Exception:
        logger.exception(
            "Layer 5 readiness could not compare Alembic revisions: current=%s expected=%s",
            current_head,
            expected_head,
        )
        return {
            "ready": False,
            "schema": "inconsistent",
            "reason": "schema_revision_inconsistent",
            "current_revisions": [current_head],
            "expected_heads": [expected_head],
        }

    return {
        "ready": False,
        "schema": "inconsistent",
        "reason": "schema_revision_inconsistent",
        "current_revisions": [current_head],
        "expected_heads": [expected_head],
    }


def _request_correlation_context(
    request: Request, *, error_code: str
) -> dict[str, object | None]:
    request_id = getattr(request.state, "trace_id", None) or request.headers.get(
        "X-Request-ID"
    )
    context = getattr(request.state, "governance_context", None)
    tenant_id = getattr(context, "tenant_id", None)
    return {
        "error_code": error_code,
        "request_id": str(request_id) if request_id else None,
        "correlation_id": str(request_id) if request_id else None,
        "tenant_id": (
            str(tenant_id)
            if tenant_id is not None
            else request.headers.get("X-Tenant-ID")
        ),
        "path": request.url.path,
        "method": request.method,
    }


def _layer3_error_response(request: Request, exc: Layer3ClientError) -> JSONResponse:
    request_id = getattr(request.state, "trace_id", None) or request.headers.get(
        "X-Request-ID"
    )
    context = getattr(request.state, "governance_context", None)
    tenant_id = getattr(context, "tenant_id", None) or getattr(exc, "tenant_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Request-ID": str(request_id)} if request_id else None,
        content={
            "code": exc.error_code,
            "message": str(exc),
            "trace_id": str(request_id) if request_id else None,
            "details": {
                "service": "layer3-knowledge",
                "tenant_id": str(tenant_id) if tenant_id is not None else None,
            },
        },
    )


async def layer3_security_exception_handler(
    request: Request, exc: Layer3ClientError
) -> JSONResponse:
    """Return explicit security/policy responses without collapsing them into 500s."""
    logger.warning(
        "layer3_security_policy_error",
        extra=_request_correlation_context(request, error_code=exc.error_code),
    )
    return _layer3_error_response(request, exc)


async def layer3_operational_exception_handler(
    request: Request, exc: Layer3ClientError
) -> JSONResponse:
    """Return explicit operational dependency errors if a caller elects to raise them."""
    logger.warning(
        "layer3_operational_error",
        extra=_request_correlation_context(request, error_code=exc.error_code),
    )
    return _layer3_error_response(request, exc)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle — database init and teardown."""
    validate_production_safety()

    if getattr(app.state, "telemetry_provider", None):
        logger.info("L5: OpenTelemetry tracing initialized")

    settings = get_settings()
    logger.info("Starting Layer 5 Ground Truth service on port %d", settings.api_port)

    # Security: fail fast if weak JWT secret is used in production
    if not settings.debug:
        _validate_jwt_secret(settings.jwt_secret)

    # Initialize DB tables (no-op if already exist; Alembic handles migrations)
    if settings.debug:
        logger.info("DEBUG mode: running init_db() to create tables if missing")
        await init_db()

    # Production Vault smoke gate
    if settings.is_production_like:
        vault_addr = settings.vault_addr
        if vault_addr and is_vault_healthy is not None:
            logger.info("L5: Checking Vault connectivity at %s", vault_addr)
            health_result = is_vault_healthy(vault_addr)
            ok = (
                await health_result
                if inspect.isawaitable(health_result)
                else health_result
            )
            if not ok:
                logger.error(
                    "L5: Vault unreachable — cannot start in production without secrets backend"
                )
                raise RuntimeError(
                    "Vault unreachable — cannot start in production without secrets backend"
                )
            logger.info("L5: Vault connectivity verified")

    # Initialize Redis client for rate limiting (async context)
    app.state.redis_rate_limiter = None
    try:
        import redis.asyncio as redis
        from value_fabric.shared.identity.rate_limiter import RedisRateLimiter

        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        # Validate connection before using for rate limiting
        await redis_client.ping()
        app.state.redis_rate_limiter = RedisRateLimiter(redis_client)
        logger.info("L5: Redis rate limiter initialized")
    except Exception as e:
        env = settings.effective_environment
        redis_required = settings.redis_rate_limiting_required

        if redis_required or settings.is_production_like:
            logger.error(f"L5: Redis rate limiting required but unavailable: {e}")
            raise RuntimeError(
                f"Redis rate limiting required in {env} but unavailable: {e}"
            )

        logger.warning(f"L5: Redis rate limiter disabled - {e}")
        app.state.redis_rate_limiter = None

    logger.info(
        "L5: FreshnessMonitor background scheduler not started in API workers; "
        "use an external cron/job runner or the explicit trigger endpoint"
    )

    yield

    logger.info("Shutting down Layer 5 Ground Truth service")
    await close_db()

    # Close Layer 3 client connection pool
    try:
        from ..integration.layer3_client import get_layer3_client

        client = get_layer3_client()
        await client.close()
        logger.info("L5: Layer 3 client closed")
    except Exception as exc:
        logger.warning("L5: Error closing Layer 3 client: %s", exc)

    # Close Redis connection if initialized
    if app.state.redis_rate_limiter:
        try:
            await app.state.redis_rate_limiter.close()
            logger.info("L5: Redis connection closed")
        except Exception as e:
            logger.warning(f"L5: Error closing Redis connection: {e}")

    # Shutdown OpenTelemetry tracer provider to flush pending spans
    if getattr(app.state, "telemetry_provider", None):
        logger.info("L5: Shutting down OpenTelemetry tracer provider")
        app.state.telemetry_provider.shutdown()
        app.state.telemetry_provider = None


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = create_fabric_app(
        service_name="layer5-ground-truth",
        title="Value Fabric — Ground Truth Layer (L5)",
        description=(
            "Evidence-backed, CFO-defensible facts for the Value Fabric platform. "
            "Provides a validation state machine (extracted → supported → corroborated → approved), "
            "a 0–5 maturity ladder, and bidirectional integration with the Layer 3 Knowledge Graph."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        telemetry_service_name="layer5-ground-truth",
        instrument_telemetry=True,
        contact={
            "name": "Value Fabric Engineering",
            "url": "https://github.com/bmsull560/Fabric_4L",
        },
        license_info={
            "name": "Proprietary",
        },
        openapi_tags=[
            {
                "name": "ground-truth",
                "description": (
                    "CRUD and validation operations for TruthObject records. "
                    "All endpoints are scoped to an tenant_id for multi-tenancy."
                ),
            },
            {
                "name": "model-registry",
                "description": (
                    "LLM model versioning, deployment, and evaluation tracking. "
                    "Manages model lifecycles with cost attribution and canary releases."
                ),
            },
            {
                "name": "system",
                "description": "Health check and operational endpoints.",
            },
        ],
    )

    app.add_exception_handler(
        Layer3PolicyDeniedError, layer3_security_exception_handler
    )
    app.add_exception_handler(
        Layer3TenantMismatchError, layer3_security_exception_handler
    )
    app.add_exception_handler(Layer3ClientError, layer3_operational_exception_handler)

    install_metrics_middleware(
        app,
        metrics=initialize_metrics(),
        middleware_factory=MetricsMiddleware,
        logger=logger,
    )

    # SecurityMiddleware — input validation and security headers (before CORS)
    # L5 has no skip paths — all endpoints require strict validation
    _security_config_l5 = SecurityConfig.from_env(
        skip_validation_paths=frozenset(),
        strict_mode=True,
    )
    add_security_middleware(app, config=_security_config_l5)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        error_code = str(detail.get("error_code") or detail.get("code") or "HTTP_EXCEPTION")
        ctx = getattr(request.state, "governance_context", None)
        tenant_id = (
            str(getattr(ctx, "tenant_id", "")) if ctx and getattr(ctx, "tenant_id", None) else
            request.headers.get("X-Tenant-ID")
        )
        request_id = request.headers.get("X-Request-ID")
        is_security_error = exc.status_code in (401, 403) or error_code in SECURITY_ERROR_CODES
        logger.warning(
            "security error response" if is_security_error else "operational http error response",
            extra={
                "error_code": error_code,
                "request_id": request_id,
                "tenant_id": tenant_id,
                "path": request.url.path,
                "status_code": exc.status_code,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "security_error" if is_security_error else "operational_error",
                "error_code": error_code,
                "message": detail.get("message") or detail.get("detail") or str(exc.detail),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        ctx = getattr(request.state, "governance_context", None)
        tenant_id = (
            str(getattr(ctx, "tenant_id", "")) if ctx and getattr(ctx, "tenant_id", None) else
            request.headers.get("X-Tenant-ID")
        )
        logger.exception(
            "unhandled operational error",
            extra={
                "error_code": "L5_UNHANDLED_ERROR",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "operational_error",
                "error_code": "L5_UNHANDLED_ERROR",
                "message": "Internal server error",
            },
        )

    class _AppStateRateLimiterProxy:
        def __init__(self, application: FastAPI):
            self._application = application

        async def check(self, rate_key, config):
            limiter = getattr(self._application.state, "redis_rate_limiter", None)
            if limiter is None:
                return None
            return await limiter.check(rate_key, config)

    # GovernanceMiddleware — provides auth and tenant context with rate limiting.
    # Fail closed in production and staging; dev bypass requires explicit opt-in.
    #
    # ALLOW_INSECURE_DEV_AUTH_BYPASS=true disables auth enforcement in development
    # only. This flag must never be set in production or staging environments.
    # REDIS_RATE_LIMITING_REQUIRED=true forces Redis availability at startup.
    # In production-like environments Redis is always required; the lifespan
    # handler calls `await redis_client.ping()` to verify connectivity before
    # accepting traffic.
    redis_rate_limiter = _AppStateRateLimiterProxy(app)

    try:
        from value_fabric.shared.identity.middleware import GovernanceMiddleware

        app.add_middleware(
            GovernanceMiddleware,
            api_key_resolver=None,
            rate_limiter=redis_rate_limiter,
        )
        logger.info("L5: GovernanceMiddleware with rate limiting initialized")
    except ImportError:
        logger.error(
            "CRITICAL: GovernanceMiddleware not importable. "
            "Authentication is required in all environments."
        )
        raise RuntimeError(
            "GovernanceMiddleware is required. shared.identity.middleware is not importable."
        )

    # CORS — fail-safe via shared resolve_cors_policy()
    app.state.cors_policy = resolve_cors_policy()

    # Mount the API routers
    app.include_router(router)

    # Mount the Model Registry router
    try:
        from .model_registry_routes import router as model_registry_router

        app.include_router(model_registry_router)
    except ImportError:
        logging.getLogger(__name__).warning("Model Registry router not available")

    # Prometheus metrics endpoint — internal only, protected by network/auth
    @app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
    async def metrics_endpoint(request: Request):
        """Prometheus metrics endpoint — requires internal access token."""
        # Verify internal access for metrics (blocks public ingress access).
        # Delegated to shared.observability so all layers stay aligned.
        if not verify_metrics_access(request):
            raise HTTPException(
                status_code=403, detail="Metrics endpoint requires internal access"
            )

        metrics = get_metrics()
        if not metrics:
            return Response(
                content="# Metrics collection is disabled",
                status_code=503,
                media_type="text/plain",
            )
        try:
            return Response(
                content=metrics.get_metrics(),
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return Response(
                content=f"# Error: {e}", status_code=500, media_type="text/plain"
            )

    # Public health check (matches middleware PUBLIC_PATH_ALLOWLIST)
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        include_in_schema=False,
    )
    async def public_health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=__version__,
            timestamp=datetime.now(UTC),
            database="ok",
        )

    # Readiness check — verifies database connectivity and migration alignment
    @app.get("/ready", tags=["system"], include_in_schema=False)
    async def readiness() -> JSONResponse:
        try:
            await _check_database_connectivity()
            schema_state = await _check_schema_migration_alignment()
            if not schema_state["ready"]:
                return JSONResponse(
                    content={
                        "status": "not_ready",
                        "database": "ok",
                        "schema": schema_state["schema"],
                        "not_ready": {
                            "component": "schema",
                            "reason": schema_state["reason"],
                            "current_revisions": schema_state["current_revisions"],
                            "expected_heads": schema_state["expected_heads"],
                        },
                    },
                    status_code=503,
                )
            return JSONResponse(
                content={"status": "ready", "database": "ok"},
                status_code=200,
            )
        except Exception as exc:
            logger.warning("Readiness check failed: %s", exc)
            return JSONResponse(
                content={"status": "not_ready", "database": "unavailable"},
                status_code=503,
            )

    # Root redirect to docs
    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            content={
                "service": "Value Fabric Ground Truth Layer (L5)",
                "version": __version__,
                "docs": "/docs",
                "health": "/health",
                "metrics": "/metrics",
            }
        )

    return app


# ---------------------------------------------------------------------------
# Module-level app instance (used by uvicorn)
# ---------------------------------------------------------------------------

# JWT Secret validation denylist — known weak/placeholder values (exact match,
# case-insensitive).  Defined at module level so the set is constructed once.
JWT_SECRET_DENYLIST: frozenset[str] = frozenset(
    {
        "changeme-in-production",
        "changeme",
        "password",
        "password123",
        "admin",
        "secret",
        "jwt-secret",
        "default",
        "test",
        "",
        "null",
        "none",
        "123456",
        "12345678",
        "qwerty",
        "abc123",
    }
)

# Weak prefix patterns — catches padded placeholders like "changemexxxxxxxx"
# that pass the length check but are still predictable.  Defined at module
# level so the tuple is constructed once, not on every validation call.
_JWT_WEAK_PREFIXES: tuple[str, ...] = (
    "changeme",
    "password",
    "secret",
    "admin",
    "test",
    "default",
    "123456",
    "qwerty",
    "abc123",
)

# Compiled pattern for common weak-secret stems followed by digits.
_JWT_WEAK_PATTERN = re.compile(r"^(changeme|password|secret|admin|test|default)[0-9]*$")


def _validate_jwt_secret(secret: str) -> None:
    """
    Validate JWT secret meets security requirements for production.

    Requirements:
    - Non-empty
    - Minimum 32 characters
    - Not in the exact-match denylist
    - Does not start with a known weak prefix
    - Does not match a weak stem+digits pattern
    """
    if not secret:
        raise RuntimeError(
            "JWT_SECRET is empty or not set. Set a secure JWT_SECRET environment variable."
        )

    if len(secret) < 32:
        raise RuntimeError(
            f"JWT_SECRET is too short ({len(secret)} chars). "
            f"Minimum 32 characters required for security. "
            f"Generate a secure secret: openssl rand -base64 32"
        )

    secret_lower = secret.lower()

    if secret_lower in JWT_SECRET_DENYLIST:
        raise RuntimeError(
            "JWT_SECRET is a known weak/placeholder value. "
            "Generate a secure secret: openssl rand -base64 32"
        )

    if _JWT_WEAK_PATTERN.match(secret_lower):
        raise RuntimeError(
            "JWT_SECRET matches a weak secret pattern. "
            "Generate a secure secret: openssl rand -base64 32"
        )


def _is_internal_ip(ip: str) -> bool:
    """Return True if *ip* is an RFC-1918 / loopback / link-local address.

    Handles both plain IPv4 strings and IPv4-mapped IPv6 (``::ffff:x.x.x.x``).
    Used by the metrics endpoint to restrict access to internal callers.
    """
    import ipaddress

    try:
        # Strip IPv4-mapped IPv6 prefix so the private-range check works uniformly.
        if ip.startswith("::ffff:"):
            ip = ip[7:]
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


app = create_app()
