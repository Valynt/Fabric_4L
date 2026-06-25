# mypy: ignore-missing-imports, disable-error-code="import-not-found,import-untyped,type-arg,no-any-return,no-untyped-def,truthy-function,list-item,assignment,arg-type,call-overload,union-attr,var-annotated,misc,attr-defined"
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
)

"""FastAPI application for Layer 1: Intelligent Data Ingestion Service.

Spec-compliant REST API with multi-tenancy support.
Base URL: /api/v1/ingestion

Provides endpoints for:
- ScrapingTarget CRUD (/targets)
- ScrapingJob management (/jobs)
- Content retrieval (/content)
- Compliance auditing (/compliance)
"""

import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn
from uuid import UUID

import redis
import sqlalchemy.exc
import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

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
    from value_fabric.shared.identity.api_key_stub import reject_api_key_unsupported
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    from value_fabric.shared.identity.rate_limiter import RedisRateLimiter
    from value_fabric.shared.identity.vault_check import is_vault_healthy
    from value_fabric.shared.models.typed_dict import TypedDictModel
    from value_fabric.shared.observability.metrics_access import verify_metrics_access
    from value_fabric.shared.probes import normalize_probe_payload
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
    get_db_from_context,
    get_db_from_context_sync,
    redis_client_async,
)
from ..shared.models import (
    AccountIntelligencePacket,
    ComplianceEventType,
    ComplianceLog,
    JobStatus,
    ScrapingJob,
    SourceCorpus,
    create_proxy_pool,
)
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
    ComponentHealth,
    CreateProxyPoolRequest,
    HealthCheckResponse,
    ProxyPoolResponse,
)
from .schemas.compliance_schemas import ComplianceSummaryResponse
from .schemas.content_schemas import (
    ExtractedDataResponse,
    RawContentResponse,
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
    "create_target",
    "delete_target",
    "execute_target",
    "get_current_user_id",
    "get_domain_fallback_stats",
    "get_extracted_data",
    "get_job",
    "get_job_progress",
    "get_job_results",
    "get_job_router_report",
    "get_raw_content",
    "get_target",
    "get_target_decisions",
    "get_tenant_id",
    "list_jobs",
    "list_content",
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


class _load_deprecation_registerResult(TypedDictModel):
    deprecations: list[Any]


def _load_deprecation_register() -> dict:
    """Load deprecation register from docs/deprecation_register.json."""
    try:
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        register_path = repo_root / "docs" / "deprecation_register.json"
        if register_path.exists():
            with open(register_path, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(
            "Failed to load deprecation register",
            error_code="DEPRECATION_LOAD_ERROR",
            error=repr(e),
        )
    return _load_deprecation_registerResult.model_validate(
        {"deprecations": []}
    ).model_dump()


def _check_deprecation_warnings(register: dict) -> None:
    """Log warnings for overdue or upcoming deprecations."""
    now = datetime.now(UTC)
    for item in register.get("deprecations", []):
        target_removal = item.get("target_removal")
        if not target_removal:
            continue
        try:
            removal_date = datetime.fromisoformat(target_removal.replace("Z", "+00:00"))
            if removal_date <= now:
                logger.warning(
                    "Deprecation overdue",
                    feature=item.get("feature"),
                    target_removal=target_removal,
                    owner=item.get("owner"),
                    path=item.get("path"),
                )
            else:
                days_until = (removal_date - now).days
                if days_until <= 7:
                    logger.warning(
                        "Deprecation expiring soon",
                        feature=item.get("feature"),
                        days_until=days_until,
                        target_removal=target_removal,
                    )
        except ValueError:
            continue


# Load deprecation register at startup
_deprecation_register = _load_deprecation_register()
_check_deprecation_warnings(_deprecation_register)


def _add_deprecation_headers(response: Response, endpoint_path: str) -> None:
    """Add deprecation headers if endpoint matches a deprecated feature."""
    for item in _deprecation_register.get("deprecations", []):
        if endpoint_path in item.get("path", ""):
            deprecated_since = item.get("deprecated_since", "")
            target_removal = item.get("target_removal", "")
            owner = item.get("owner", "")

            if deprecated_since:
                response.headers["X-Deprecated-Since"] = deprecated_since
            if target_removal:
                response.headers["X-Target-Removal-Date"] = target_removal
            if owner:
                response.headers["X-Deprecation-Owner"] = owner
            # RFC 7234 Warning header
            response.headers["Warning"] = f'299 - "Deprecated since {deprecated_since}"'
            break


# =============================================================================
# FASTAPI APP INITIALIZATION
# =============================================================================

# Initialize Prometheus metrics
metrics = initialize_metrics()

# Vault health check error message
_VAULT_UNREACHABLE_ERROR = (
    "Vault unreachable â€” cannot start in production without secrets backend"
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

# SecurityMiddleware â€” input validation and security headers (mandatory)
_security_config_l1 = SecurityConfig.from_env(
    # P1-14 FIX: Removed /v1/ingest paths from skip list
    # All untrusted input must pass through SecurityMiddleware validation
    skip_validation_paths=frozenset(
        {
            "/health",
            "/metrics",
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

# GovernanceMiddleware â€” verifies JWTs and resolves tenant/user context (mandatory)
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
    metrics = get_metrics()
    if metrics:
        metrics.increment_errors(error_type="redis_init_failed", component="api")


class list_contentResult(TypedDictModel):
    items: Any
    limit: Any
    page: Any
    total: Any


class list_compliance_logsResult(TypedDictModel):
    items: Any
    limit: Any
    page: Any
    total: Any


class trigger_cleanupResult(TypedDictModel):
    message: str
    status: str


class legacy_health_checkResult(TypedDictModel):
    dependencies: Any
    note: str
    status: Any


app.add_middleware(
    GovernanceMiddleware,
    api_key_resolver=reject_api_key_unsupported,
    rate_limiter=redis_rate_limiter,
)

# Add metrics middleware if available â€” INNERMOST
if metrics:
    metrics_middleware = MetricsMiddleware(metrics)
    app.middleware("http")(metrics_middleware)


# Create router for spec-compliant endpoints
router = APIRouter(prefix="/api/v1/ingestion")


# =============================================================================
# API ENDPOINTS - ScrapingTarget
# =============================================================================

# =============================================================================
# API ENDPOINTS - Content
# =============================================================================


async def get_raw_content(
    content_id: UUID,
    include_html: bool = Query(default=True),
    include_screenshot: bool = Query(default=False),
    include_har: bool = Query(default=False),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context),
):
    """Retrieve raw content by ID."""
    content = (
        db.query(RawContent)
        .filter(RawContent.id == content_id, RawContent.tenant_id == org_id)
        .first()
    )

    if not content:
        raise NotFoundError(message="Content not found")

    storage = {}
    if include_html:
        storage["html"] = content.storage_html_path
    if include_screenshot:
        storage["screenshot"] = content.storage_screenshot_path
    if include_har:
        storage["har"] = content.storage_har_path

    return RawContentResponse(
        id=content.id,
        job_id=content.job_id,
        source_url=content.source_url,
        source_final_url=content.source_final_url,
        source_domain=content.source_domain,
        source_http_status=content.source_http_status,
        storage=storage,
        metadata={
            "title": content.meta_title,
            "description": content.meta_description,
            "language": content.meta_language,
            "og_tags": content.meta_og_tags,
            "structured_data": content.meta_structured_data,
        },
        capture={
            "method": content.capture_method,
            "browser_version": content.capture_browser_version,
            "javascript_executed": content.capture_javascript_executed,
            "wait_time_ms": content.capture_wait_time_ms,
        },
        content_hash=content.content_hash,
        is_duplicate=content.is_duplicate,
        processing_status=content.processing_status,
        created_at=content.created_at,
    )


async def get_extracted_data(
    extracted_data_id: UUID,
    format: str = Query(default="json", regex="^(json|markdown|flattened)$"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context),
):
    """Retrieve extracted data by ID."""
    data = (
        db.query(ExtractedData)
        .filter(
            ExtractedData.id == extracted_data_id, ExtractedData.tenant_id == org_id
        )
        .first()
    )

    if not data:
        raise NotFoundError(message="Extracted data not found")

    return ExtractedDataResponse(
        id=data.id,
        job_id=data.job_id,
        raw_content_id=data.raw_content_id,
        extraction_method=data.extraction_method,
        extraction_confidence_score=(
            float(data.extraction_confidence_score)
            if data.extraction_confidence_score
            else 0.0
        ),
        data=data.data,
        validation={
            "schema_valid": data.validation_schema_valid,
            "errors": data.validation_errors,
            "data_quality_score": (
                float(data.validation_data_quality_score)
                if data.validation_data_quality_score
                else 0.0
            ),
        },
        post_processing={
            "pii_redaction_applied": data.post_pii_redaction_applied,
            "redacted_fields": data.post_redacted_fields,
            "normalized_fields": data.post_normalized_fields,
            "enriched_fields": data.post_enriched_fields,
        },
        created_at=data.created_at,
    )


async def list_content(
    job_id: UUID | None = Query(None),
    domain: str | None = Query(None),
    processing_status: str | None = Query(None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context),
):
    """List raw content with filtering."""
    query = db.query(RawContent).filter(RawContent.tenant_id == org_id)

    if job_id:
        query = query.filter(RawContent.job_id == job_id)

    if domain:
        query = query.filter(RawContent.source_domain == domain)

    if processing_status:
        query = query.filter(RawContent.processing_status == processing_status)

    total = query.count()
    offset = (page - 1) * limit
    items = (
        query.order_by(RawContent.created_at.desc()).offset(offset).limit(limit).all()
    )

    return list_contentResult.model_validate(
        {
            "items": [
                {
                    "id": str(item.id),
                    "job_id": str(item.job_id),
                    "source_url": item.source_url,
                    "source_domain": item.source_domain,
                    "processing_status": item.processing_status,
                    "created_at": item.created_at.isoformat(),
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }
    )


# =============================================================================
# API ENDPOINTS - Compliance
# =============================================================================


async def list_compliance_logs(
    event_type: list[ComplianceEventType] | None = Query(None),
    severity: str | None = Query(None),
    domain: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    job_id: UUID | None = Query(None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Query compliance logs."""
    query = db.query(ComplianceLog).filter(ComplianceLog.tenant_id == org_id)

    if event_type:
        types = [t.value for t in event_type]
        query = query.filter(ComplianceLog.event_type.in_(types))

    if severity:
        query = query.filter(ComplianceLog.severity == severity)

    if domain:
        query = query.filter(ComplianceLog.request_url.contains(domain))

    if date_from:
        query = query.filter(ComplianceLog.created_at >= date_from)

    if date_to:
        query = query.filter(ComplianceLog.created_at <= date_to)

    if job_id:
        query = query.filter(ComplianceLog.job_id == job_id)

    total = query.count()
    offset = (page - 1) * limit
    logs = (
        query.order_by(ComplianceLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return list_compliance_logsResult.model_validate(
        {
            "items": [
                {
                    "id": str(log.id),
                    "event_type": log.event_type,
                    "severity": log.severity,
                    "request_url": log.request_url,
                    "request_timestamp": log.request_timestamp.isoformat(),
                    "response_action_taken": log.response_action_taken,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }
    )


async def get_compliance_summary(
    period_start: datetime = Query(...),
    period_end: datetime = Query(...),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get compliance summary for organization."""
    query = db.query(ComplianceLog).filter(
        ComplianceLog.tenant_id == org_id,
        ComplianceLog.created_at >= period_start,
        ComplianceLog.created_at <= period_end,
    )

    total_logs = query.count()

    robots_checks = query.filter(
        ComplianceLog.event_type == ComplianceEventType.ROBOTS_TXT_CHECK.value
    ).count()
    allowed = query.filter(
        ComplianceLog.event_type == ComplianceEventType.ROBOTS_TXT_CHECK.value,
        ComplianceLog.robots_txt_check.isnot(None),
    ).count()  # Simplified

    rate_limits = query.filter(
        ComplianceLog.event_type == ComplianceEventType.RATE_LIMIT_APPLIED.value
    ).count()
    pii_detections = query.filter(
        ComplianceLog.event_type == ComplianceEventType.PII_DETECTED.value
    ).count()
    domain_blocks = query.filter(
        ComplianceLog.event_type == ComplianceEventType.DOMAIN_BLOCKED.value
    ).count()

    robots_logs = query.filter(
        ComplianceLog.event_type == ComplianceEventType.ROBOTS_TXT_CHECK.value
    ).all()
    crawl_delays_respected = sum(
        1
        for log in robots_logs
        if (log.robots_txt_check or {}).get("crawl_delay") not in (None, 0)
    )

    rate_limit_logs = query.filter(
        ComplianceLog.event_type == ComplianceEventType.RATE_LIMIT_APPLIED.value
    ).all()
    delay_values = [
        (log.rate_limit_event or {}).get("delay_ms")
        for log in rate_limit_logs
        if isinstance((log.rate_limit_event or {}).get("delay_ms"), int)
    ]
    average_delay_ms = (
        int(sum(delay_values) / len(delay_values)) if delay_values else None
    )

    allowlisted_count = query.filter(
        ComplianceLog.event_type == ComplianceEventType.DOMAIN_ALLOWED.value
    ).count()

    return ComplianceSummaryResponse(
        period={"start": period_start, "end": period_end},
        robots_txt_compliance={
            "total_checks": robots_checks,
            "allowed": allowed,
            "blocked": robots_checks - allowed,
            "crawl_delays_respected": crawl_delays_respected,
        },
        rate_limiting={
            "total_requests": total_logs,
            "throttled_requests": rate_limits,
            "average_delay_ms": average_delay_ms,
            "average_delay_ms_metadata": {
                "status": "unknown" if average_delay_ms is None else "measured",
                "reason": (
                    "No delay_ms values found in compliance rate_limit_event logs"
                    if average_delay_ms is None
                    else None
                ),
            },
        },
        pii_detection={
            "scans_performed": total_logs,
            "detections": pii_detections,
            "redactions_applied": query.filter(
                ComplianceLog.event_type == ComplianceEventType.PII_REDACTED.value
            ).count(),
        },
        domain_policies={
            "allowlisted": allowlisted_count,
            "blocklisted": domain_blocks,
            "blocked_requests": domain_blocks,
        },
    )


# =============================================================================
# API ENDPOINTS - Health & Admin
# =============================================================================


async def health_check(db: Session = Depends(get_db_from_context_sync)):
    """Enhanced health check endpoint."""
    components = {}
    metrics = {}

    # Database check
    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        components["database"] = ComponentHealth(status="healthy", latency_ms=0)
    except Exception as e:
        logger.error(
            "health_check_database_failed", error_code="DB_HEALTH_ERROR", error=repr(e)
        )
        components["database"] = ComponentHealth(
            status="unhealthy", message="Database connection failed"
        )

    # Queue check (Redis)
    try:
        from ..shared.database import redis_client

        redis_client.ping()
        components["queue"] = ComponentHealth(status="healthy", latency_ms=0)
    except (redis.RedisError, ConnectionError) as e:
        logger.warning("redis_ping_failed", error=str(e))
        components["queue"] = ComponentHealth(
            status="degraded", message="Redis not available"
        )

    # Active jobs metrics
    active_jobs = (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.status.in_(
                [
                    JobStatus.QUEUED.value,
                    JobStatus.VALIDATING.value,
                    JobStatus.BROWSER_ACQUIRING.value,
                    JobStatus.NAVIGATING.value,
                    JobStatus.EXTRACTING.value,
                    JobStatus.TRANSFORMING.value,
                    JobStatus.STORING.value,
                ]
            )
        )
        .count()
    )

    queued_jobs = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.status == JobStatus.QUEUED.value)
        .count()
    )

    started_jobs = db.query(ScrapingJob).all()
    wait_times_ms = [
        int((job.started_at - job.created_at).total_seconds() * 1000)
        for job in started_jobs
        if job.started_at and job.created_at
    ]
    average_wait_time_ms = (
        int(sum(wait_times_ms) / len(wait_times_ms)) if wait_times_ms else None
    )

    metrics = {
        "active_jobs": active_jobs,
        "queued_jobs": queued_jobs,
        "available_browsers": None,
        "available_browsers_metadata": {
            "status": "unknown",
            "reason": "Browser pool telemetry is not yet wired in Layer 1",
        },
        "average_wait_time_ms": average_wait_time_ms,
        "average_wait_time_ms_metadata": {
            "status": "unknown" if average_wait_time_ms is None else "measured",
            "reason": (
                "No started jobs available to calculate queue wait time"
                if average_wait_time_ms is None
                else None
            ),
        },
    }

    # Determine overall status
    if any(c.status == "unhealthy" for c in components.values()):
        overall_status = "unhealthy"
    elif any(c.status == "degraded" for c in components.values()):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        components={k: v.dict() for k, v in components.items()},
        metrics=metrics,
    )


async def metrics_endpoint(request: Request):
    """Prometheus-compatible metrics endpoint."""
    if not verify_metrics_access(request):
        raise AuthorizationError(message="Metrics endpoint requires internal access")

    metrics = get_metrics()

    if not metrics:
        return Response(
            content="Metrics collection is disabled",
            status_code=503,
            media_type="text/plain",
        )

    try:
        metrics_data = metrics.get_metrics()
        return Response(
            content=metrics_data, media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        return Response(
            content=f"Error generating metrics: {e}",
            status_code=500,
            media_type="text/plain",
        )


async def trigger_cleanup(
    days: int = Query(default=30, ge=1, le=365),
    org_id: UUID = Depends(get_tenant_id),
):
    """Trigger content cleanup for old data.

    SECURITY: Tenant-scoped cleanup - only deletes content for the requesting tenant.
    """
    cleanup_old_content.apply_async(
        args=[days, str(org_id)],
        **(build_celery_options() or {}),
    )
    return trigger_cleanupResult.model_validate(
        {
            "message": f"Cleanup initiated for content older than {days} days",
            "status": "processing",
        }
    )


# =============================================================================
# API ENDPOINTS - Proxy Pools
# =============================================================================


async def create_proxy_pool_endpoint(
    request: CreateProxyPoolRequest,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a proxy pool."""
    pool = create_proxy_pool(
        tenant_id=org_id,
        name=request.name,
        proxies=request.proxies,
        rotation_strategy=request.rotation_strategy,
    )

    db.add(pool)
    db.commit()
    db.refresh(pool)

    return ProxyPoolResponse(
        id=pool.id,
        name=pool.name,
        proxy_count=len(pool.proxies) if pool.proxies else 0,
        rotation_strategy=pool.rotation_strategy,
        created_at=pool.created_at,
    )


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

register_source_routes(router)
register_consent_routes(router)
router.include_router(target_routes)
router.include_router(job_routes)
router.include_router(skill_routes)
router.include_router(content_routes)
router.include_router(compliance_routes)
router.include_router(admin_routes)
router.include_router(_batch_and_stats.router)

app.include_router(router)
app.include_router(compatibility_routes.router)


# Legacy compatibility routes (redirect to new endpoints)
@app.get("/health")
@app.get("/health/live", include_in_schema=False)
async def legacy_health_check():
    """Legacy-compatible health check with dependency status."""
    from ..shared.database import SessionLocal, redis_client

    dependencies = []
    overall_status = "healthy"

    # Database dependency
    db = SessionLocal()
    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        dependencies.append({"name": "database", "status": "healthy", "error": None})
    except Exception as e:
        logger.error(
            "health_check_database_failed", error_code="DB_HEALTH_ERROR", error=repr(e)
        )
        dependencies.append(
            {
                "name": "database",
                "status": "unhealthy",
                "error": "Database connection failed",
            }
        )
        overall_status = "degraded"
    finally:
        db.close()

    # Redis dependency
    try:
        if redis_client is None:
            dependencies.append(
                {
                    "name": "redis",
                    "status": "degraded",
                    "error": "Redis client not configured",
                }
            )
            overall_status = "degraded"
        else:
            redis_client.ping()
            dependencies.append({"name": "redis", "status": "healthy", "error": None})
    except Exception as e:
        logger.error(
            "health_check_redis_failed", error_code="REDIS_HEALTH_ERROR", error=repr(e)
        )
        dependencies.append(
            {"name": "redis", "status": "degraded", "error": "Redis connection failed"}
        )
        overall_status = "degraded"

    payload = normalize_probe_payload(
        status=overall_status,
        service="layer1-ingestion",
        dependencies=dependencies,
        extra={
            "note": "Legacy endpoint; use /api/v1/ingestion/health for full schema response",
        },
    )
    return legacy_health_checkResult.model_validate(payload)


@app.get("/metrics", include_in_schema=False)
async def legacy_metrics():
    """Legacy-compatible metrics endpoint."""
    content = "# HELP layer1_ingestion_metrics_legacy placeholder\n# TYPE layer1_ingestion_metrics_legacy gauge\nlayer1_ingestion_metrics_legacy 0\n"
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec B104
