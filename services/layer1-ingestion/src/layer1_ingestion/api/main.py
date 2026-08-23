# mypy: ignore-missing-imports, disable-error-code="import-not-found,import-untyped,type-arg,no-any-return,no-untyped-def,truthy-function,list-item,assignment,arg-type,call-overload,union-attr,var-annotated,misc,attr-defined"
"""FastAPI application for Layer 1: Intelligent Data Ingestion Service.

Spec-compliant REST API with multi-tenancy support.
Base URL: /api/v1/ingestion

Provides endpoints for:
- ScrapingTarget CRUD (/targets)
- ScrapingJob management (/jobs)
- Content retrieval (/content)
- Compliance auditing (/compliance)
"""

import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, NoReturn

import sqlalchemy.exc
import structlog
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import Response

try:
    from value_fabric.shared.error_handling import register_exception_handlers
    from value_fabric.shared.fastapi_framework import (
        EnforcementControlConfig,
        EnforcementMode,
        EnforcementRolloutConfig,
        FrameworkRateLimitConfig,
        create_fabric_app,
    )
    from value_fabric.shared.fastapi_framework.health import (
        CallableProbe,
        ProbeResult,
        RedisHealthProbe,
    )
    from value_fabric.shared.governance.deprecation_register import (
        DeprecationItem,
        DeprecationRegisterError,
    )
    from value_fabric.shared.governance.deprecation_register import (
        load_items as load_deprecation_items,
    )
    from value_fabric.shared.identity.api_key_stub import reject_api_key_unsupported
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    from value_fabric.shared.identity.rate_limiter import RedisRateLimiter
    from value_fabric.shared.identity.vault_check import is_vault_healthy
    from value_fabric.shared.security import (
        SecurityConfig,
        add_security_middleware,
        install_redaction_filter,
        redaction_processor,
        validate_production_safety,
    )
    from value_fabric.shared.startup import reject_insecure_bypass_in_production
except ImportError as e:
    raise ImportError(
        f"Failed to import from value_fabric.shared. Ensure packages/shared is in PYTHONPATH. Error: {e}"
    ) from e

from ..metrics import MetricsMiddleware, get_metrics, initialize_metrics
from ..shared.config import is_production_like_environment, settings
from ..shared.database import (
    engine,
    get_db_from_context_sync,
    redis_client_async,
)
from ..shared.models import AccountIntelligencePacket, SourceCorpus
from .admin_handlers import (
    create_proxy_pool_endpoint,
    health_check,
    legacy_metrics,
    metrics_endpoint,
    trigger_cleanup,
)
from .compliance_handlers import get_compliance_summary, list_compliance_logs
from .content_handlers import get_extracted_data, get_raw_content, list_content
from .dependencies import get_current_user_id, get_tenant_id
from .job_handlers import (
    cancel_job,
    get_domain_fallback_stats,
    get_job,
    get_job_progress,
    get_job_results,
    get_job_router_report,
    list_jobs,
    retry_job,
)
from .schemas.admin_schemas import (
    ComponentHealth as ComponentHealth,
)
from .schemas.admin_schemas import (
    CreateProxyPoolRequest as CreateProxyPoolRequest,
)
from .schemas.admin_schemas import (
    HealthCheckResponse as HealthCheckResponse,
)
from .schemas.admin_schemas import (
    ProxyPoolResponse as ProxyPoolResponse,
)
from .schemas.target_schemas import (
    CreateTargetRequest,
    ExecuteTargetRequest,
    ExecuteTargetResponse,
    ScrapingTargetDetail,
    ScrapingTargetSummary,
    TargetListResponse,
    UpdateTargetRequest,
    ValidateTargetRequest,
    ValidateTargetResponse,
    ValidationWarning,
)
from .skill_handlers import (
    create_licensing_company_intake_job,
    create_prospect_research_job,
    get_account_intelligence_packet,
    get_account_intelligence_packet_detail,
    get_job_skill_output,
    get_source_corpus,
    get_source_corpus_detail,
    list_account_intelligence_packets,
    list_source_corpora,
)
from .target_handlers import (
    create_target,
    delete_target,
    execute_target,
    get_target,
    get_target_decisions,
    list_targets,
    update_target,
    validate_target,
)

__all__ = [
    "CreateTargetRequest",
    "ExecuteTargetRequest",
    "ExecuteTargetResponse",
    "ScrapingTargetDetail",
    "ScrapingTargetSummary",
    "TargetListResponse",
    "UpdateTargetRequest",
    "ValidateTargetRequest",
    "ValidateTargetResponse",
    "ValidationWarning",
    "AccountIntelligencePacket",
    "SourceCorpus",
    "create_proxy_pool_endpoint",
    "create_target",
    "delete_target",
    "execute_target",
    "get_current_user_id",
    "get_compliance_summary",
    "get_db_from_context_sync",
    "get_domain_fallback_stats",
    "get_extracted_data",
    "get_job",
    "get_job_progress",
    "get_job_results",
    "get_job_router_report",
    "health_check",
    "get_raw_content",
    "get_target",
    "get_target_decisions",
    "get_tenant_id",
    "list_jobs",
    "list_content",
    "list_compliance_logs",
    "list_targets",
    "cancel_job",
    "create_licensing_company_intake_job",
    "create_prospect_research_job",
    "get_account_intelligence_packet",
    "get_account_intelligence_packet_detail",
    "retry_job",
    "get_job_skill_output",
    "get_source_corpus",
    "get_source_corpus_detail",
    "list_account_intelligence_packets",
    "list_source_corpora",
    "metrics_endpoint",
    "trigger_cleanup",
    "update_target",
    "validate_target",
]


def _build_task_unavailable_detail() -> dict[str, str]:
    return {
        "code": "SERVICE_UNAVAILABLE",
        "message": (
            "Background processing is temporarily unavailable. "
            "Please retry shortly or contact support if the issue persists."
        ),
    }


class _UnavailableTask:
    """Fail closed when task infrastructure is unavailable."""

    def __init__(self, task_name: str, import_error: ImportError) -> None:
        self.task_name = task_name
        self.import_error = import_error

    def delay(self, *args: Any, **kwargs: Any) -> "NoReturn":
        job_id = str(args[0]) if args else None
        logger.error(
            "background_task_unavailable",
            task_name=self.task_name,
            job_id=job_id,
            correlation_id=job_id,
            error_type=type(self.import_error).__name__,
            error=str(self.import_error),
            exc_info=self.import_error,
        )
        raise HTTPException(status_code=503, detail=_build_task_unavailable_detail())


try:
    from ..shared.otel_celery import build_celery_options
    from ..shared.tasks import cleanup_old_content, process_scraping_job
except ImportError as exc:
    build_celery_options = None  # type: ignore[assignment]
    cleanup_old_content = _UnavailableTask("cleanup_old_content", exc)
    process_scraping_job = _UnavailableTask("process_scraping_job", exc)

# Configure logging
install_redaction_filter()
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        redaction_processor,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
reject_insecure_bypass_in_production(service_name="layer1-ingestion", settings=settings)

def _url_safety_error_payload(reason_code: str) -> dict[str, str]:
    return {
        "error": "url_validation_failed",
        "reason_code": reason_code,
        "message": "URL blocked by compliance policy",
    }


# =============================================================================
# DEPRECATION REGISTER
# =============================================================================


def _load_deprecation_register() -> list[DeprecationItem]:
    """Load the canonical deprecation register via the shared loader.

    The register lives at ``docs/deprecation_register.json`` and is keyed by
    ``items``; the shared loader owns path resolution and schema validation so
    runtime headers, startup warnings, and the CI gate cannot drift apart.
    A missing or malformed register is surfaced as an explicit error log rather
    than being silently replaced with an empty register.
    """
    try:
        return load_deprecation_items()
    except DeprecationRegisterError as e:
        logger.error(
            "Deprecation register unavailable",
            error_code="DEPRECATION_LOAD_ERROR",
            error=repr(e),
        )
        return []


def _check_deprecation_warnings(items: list[DeprecationItem]) -> None:
    """Log warnings for overdue or upcoming deprecations."""
    now = datetime.now(UTC)
    for item in items:
        try:
            removal_date = datetime.fromisoformat(
                item.target_removal.replace("Z", "+00:00")
            ).replace(tzinfo=UTC)
        except ValueError:
            continue
        if removal_date <= now:
            logger.warning(
                "Deprecation overdue",
                feature=item.feature,
                target_removal=item.target_removal,
                owner=item.owner,
                path=item.path,
                deferred=item.is_deferred,
            )
        else:
            days_until = (removal_date - now).days
            if days_until <= 7:
                logger.warning(
                    "Deprecation expiring soon",
                    feature=item.feature,
                    days_until=days_until,
                    target_removal=item.target_removal,
                )


# Load deprecation register at startup
_deprecation_register = _load_deprecation_register()
_check_deprecation_warnings(_deprecation_register)


def _add_deprecation_headers(response: Response, endpoint_path: str) -> None:
    """Add deprecation headers if endpoint matches a deprecated feature."""
    for item in _deprecation_register:
        if endpoint_path in item.path:
            if item.deprecated_since:
                response.headers["X-Deprecated-Since"] = item.deprecated_since
            if item.target_removal:
                response.headers["X-Target-Removal-Date"] = item.target_removal
            if item.owner:
                response.headers["X-Deprecation-Owner"] = item.owner
            # RFC 7234 Warning header
            response.headers["Warning"] = f'299 - "Deprecated since {item.deprecated_since}"'
            break


# =============================================================================
# FASTAPI APP INITIALIZATION
# =============================================================================

# Initialize Prometheus metrics
metrics = initialize_metrics()

# Vault health check error message
_VAULT_UNREACHABLE_ERROR = (
    "Vault unreachable — cannot start in production without secrets backend"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify production safety and Vault connectivity before accepting traffic."""
    validate_production_safety()

    if is_production_like_environment():
        vault_addr = os.getenv("VAULT_ADDR")
        if vault_addr and is_vault_healthy:
            logger.info("L1: Checking Vault connectivity", vault_addr=vault_addr)
            ok = await is_vault_healthy(vault_addr)
            if not ok:
                logger.error("L1: Vault unreachable", vault_addr=vault_addr)
                raise RuntimeError(_VAULT_UNREACHABLE_ERROR)
            logger.info("L1: Vault connectivity verified")
    yield


async def _l1_db_probe() -> ProbeResult:
    """Readiness probe for Layer 1 PostgreSQL (sync engine)."""
    import asyncio

    from sqlalchemy import text

    try:
        await asyncio.to_thread(
            lambda: engine.connect().execute(text("SELECT 1")).close()
        )
    except (sqlalchemy.exc.SQLAlchemyError, OSError) as e:
        logger.warning("l1_db_probe_failed", error=str(e))
        return ProbeResult(name="postgres", healthy=False, detail="probe_failed")
    return ProbeResult(name="postgres", healthy=True)


app = create_fabric_app(
    service_name="layer1-ingestion",
    title="Value Fabric - Layer 1: Intelligent Data Ingestion",
    description="Production-grade web data ingestion service with spec-compliant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    cors_policy=settings.cors_policy,
    register_default_exception_handlers=False,
    include_request_id_middleware=True,
    health_probes=[
        CallableProbe(name="postgres", fn=_l1_db_probe),
        RedisHealthProbe(name="redis", _client=redis_client_async),
    ],
    readiness_path="/ready",
    enforce_tenant_context=True,
    enforcement_rollout=EnforcementRolloutConfig(
        tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.AUDIT),
        rate_limiting=EnforcementControlConfig(mode=EnforcementMode.ENFORCE),
    ),
    rate_limit=FrameworkRateLimitConfig(
        mode=EnforcementMode.ENFORCE,
        rate_limiter_factory=lambda: __import__(
            "value_fabric.shared.rate_limiting.tenant_rate_limiter",
            fromlist=["TenantRateLimiter"],
        ).TenantRateLimiter.create_from_env(),
    ),
    telemetry_service_name="layer1-ingestion",
    instrument_telemetry=True,
)

# Effective middleware/request order (outermost -> innermost):
#   CORS (from create_fabric_app)
#   RequestIDMiddleware (from create_fabric_app)  -- NEW, additive
#   SecurityMiddleware (added below)
#   Exception handlers (register_exception_handlers)
#   Fabric auth registration (register_fabric_auth_from_env)
#   GovernanceMiddleware (with RedisRateLimiter)
#   MetricsMiddleware (innermost, via app.middleware("http"))
# DB engine/session lifecycle remains service-owned.

# SecurityMiddleware — input validation and security headers (mandatory)
_security_config_l1 = SecurityConfig.from_env(
    # P1-14 FIX: Removed /v1/ingest paths from skip list
    # All untrusted input must pass through SecurityMiddleware validation
    skip_validation_paths=frozenset(
        {
            "/health",
            "/metrics",
            "/",
            "/robots.txt",
        }
    ),
    strict_mode=True,
)
add_security_middleware(app, config=_security_config_l1)
register_exception_handlers(app)

# Phase 1 Clerk integration: verify the Fabric4L internal AuthContext envelope.
# No-op when FABRIC_AUTH_PUBLIC_KEYS is unset.
from value_fabric.shared.identity.fabric_auth import (
    register_fabric_auth_from_env,
)  # noqa: E402

register_fabric_auth_from_env(app, service_name="layer1-ingestion")

# GovernanceMiddleware — verifies JWTs and resolves tenant/user context (mandatory)
redis_rate_limiter = None
try:
    from ..shared.database import redis_client_async

    if redis_client_async is not None:
        redis_rate_limiter = RedisRateLimiter(redis_client_async)
except Exception as e:
    logger.warning(
        "redis_init_failed",
        error_code="REDIS_INIT_ERROR",
        error=repr(e),
        degraded_mode=True,
        message="Rate limiting disabled - Redis unavailable",
    )
    metrics_instance = get_metrics()
    if metrics_instance:
        metrics_instance.increment_errors(error_type="redis_init_failed", component="api")


app.add_middleware(
    GovernanceMiddleware,
    api_key_resolver=reject_api_key_unsupported,
    rate_limiter=redis_rate_limiter,
)

# Add metrics middleware if available — INNERMOST
if metrics:
    metrics_middleware = MetricsMiddleware(metrics)
    app.middleware("http")(metrics_middleware)


# Create router for spec-compliant endpoints
router = APIRouter(prefix="/api/v1/ingestion")


# =============================================================================
# API ENDPOINTS - ScrapingTarget
# =============================================================================

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


# Include the router in the main app


# Adjacent route modules register cohesive endpoint groups without changing public paths.
from . import _batch_and_stats

# Public compatibility re-exports used by tests and external imports.
# Do not remove unless import paths are migrated.
from ._batch_and_stats import (
    BatchOperationItemResult,  # noqa: F401
    BatchOperationRequest,  # noqa: F401
    BatchOperationResponse,  # noqa: F401
    BatchOperationType,  # noqa: F401
    TargetStatsResponse,  # noqa: F401
)
from .consent_routes import register_routes as register_consent_routes
from .main_admin_routes import router as admin_routes
from .main_compliance_routes import router as compliance_routes
from .main_content_routes import router as content_routes
from .main_job_routes import router as job_routes
from .main_skill_routes import router as skill_routes
from .main_target_routes import router as target_routes
from .routes import compatibility as compatibility_routes
from .source_routes import register_routes as register_source_routes
from .validation_seed_routes import router as validation_seed_routes

register_source_routes(router)
register_consent_routes(router)
router.include_router(target_routes)
router.include_router(skill_routes)
router.include_router(job_routes)
router.include_router(content_routes)
router.include_router(compliance_routes)
router.include_router(admin_routes)
router.include_router(validation_seed_routes)
router.include_router(_batch_and_stats.router)

app.include_router(router)
app.include_router(compatibility_routes.router)


# Canonical observability routes. Mounted at the app root so they are reachable
# at ``/health`` and ``/metrics`` regardless of the prefixed API router.
#
# ``/health`` uses the legacy handler: the canonical ``health_check`` depends on
# a DB session (auth-gated), but observability probes must be callable by
# orchestrators without credentials. The legacy handler is the documented
# migration path in the deprecation register; once callers have moved off it,
# the route and its handler can both be removed.
from .admin_handlers import legacy_health_check

app.get("/health", tags=["health"])(legacy_health_check)
app.get("/metrics", include_in_schema=False)(legacy_metrics)


@app.get("/", include_in_schema=False)
async def root():
    return {"status": "ok"}


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse("User-agent: *\nDisallow: /\n")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec B104
