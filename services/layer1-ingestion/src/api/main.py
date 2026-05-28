from value_fabric.shared.error_handling.exceptions import AuthenticationError, AuthorizationError, NotFoundError, ServiceUnavailableError, ValidationError
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
from uuid import UUID, uuid4
from zoneinfo import available_timezones

import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

try:
    from value_fabric.shared.error_handling import register_exception_handlers
    from value_fabric.shared.identity.api_key_stub import reject_api_key_unsupported
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    from value_fabric.shared.identity.rate_limiter import RedisRateLimiter
    from value_fabric.shared.identity.vault_check import is_vault_healthy
    from value_fabric.shared.models.typed_dict import TypedDictModel
    from value_fabric.shared.security import SecurityConfig, add_security_middleware
    from value_fabric.shared.startup import reject_insecure_bypass_in_production
except ImportError as e:
    raise ImportError(
        f"Failed to import from value_fabric.shared. Ensure packages/shared is in PYTHONPATH. Error: {e}"
    ) from e

from ..compliance.url_safety import URLSafetyError, validate_url_safety
from ..crawler.decision_store import CrawlDecisionRepository
from ..metrics import MetricsMiddleware, get_metrics, initialize_metrics
from ..shared.config import is_production_like_environment, settings
from ..shared.database import get_db_from_context_sync
from ..shared.models import (
    AccountIntelligencePacket,
    AuthenticationType,
    BrowserEngine,
    ComplianceEventType,
    ComplianceLog,
    CrawlDecision,
    CrawlPath,
    ExtractedData,
    ExtractionMethod,
    JobError,
    JobStageDetail,
    JobStatus,
    LLMProvider,
    PipelineStage,
    ProxyRotationStrategy,
    RawContent,
    RetryBackoff,
    ScrapingJob,
    ScrapingJobType,
    ScrapingTarget,
    SourceCorpus,
    TargetStatus,
    TargetType,
    TriggeredBy,
    create_proxy_pool,
    create_scraping_job,
    create_scraping_target,
)
from ..skills import get_skill


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
        raise ServiceUnavailableError(message = str(_build_task_unavailable_detail()))


try:
    from ..shared.tasks import cleanup_old_content, process_scraping_job
except ImportError as exc:
    cleanup_old_content = _UnavailableTask("cleanup_old_content", exc)
    process_scraping_job = _UnavailableTask("process_scraping_job", exc)

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
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
        logger.warning("Failed to load deprecation register", error_code="DEPRECATION_LOAD_ERROR", error=str(e))
    return _load_deprecation_registerResult.model_validate({"deprecations": []}).model_dump()


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
_VAULT_UNREACHABLE_ERROR = "Vault unreachable â€” cannot start in production without secrets backend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify Vault connectivity in production before accepting traffic."""
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


app = FastAPI(
    title="Value Fabric - Layer 1: Intelligent Data Ingestion",
    description="Production-grade web data ingestion service with spec-compliant API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware with production validation (P0-20) â€” OUTERMOST.
# The policy comes from Settings so production-like environments fail before
# middleware installation, and credentials are never combined with wildcard
# origins or broad method/header exposure.
app.add_middleware(CORSMiddleware, **settings.cors_policy)

# SecurityMiddleware â€” input validation and security headers (mandatory)
_security_config_l1 = SecurityConfig.from_env(
    # P1-14 FIX: Removed /v1/ingest paths from skip list
    # All untrusted input must pass through SecurityMiddleware validation
    skip_validation_paths=frozenset({
        "/health",
        "/metrics",
    }),
    strict_mode=True,
)
add_security_middleware(app, config=_security_config_l1)
register_exception_handlers(app)

# Phase 1 Clerk integration: verify the Fabric4L internal AuthContext envelope.
# No-op when FABRIC_AUTH_PUBLIC_KEYS is unset.
from value_fabric.shared.identity.fabric_auth import register_fabric_auth_from_env  # noqa: E402

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
        error=str(e),
        degraded_mode=True,
        message="Rate limiting disabled - Redis unavailable",
    )
    metrics = get_metrics()
    if metrics:
        metrics.increment_errors(error_type="redis_init_failed", component="api")


class cancel_jobResult(TypedDictModel):
    job_id: Any
    status: str

class get_job_resultsResult(TypedDictModel):
    data: Any
    format: Any
    job_id: Any
    limit: Any
    page: Any
    total_records: Any

class retry_jobResult(TypedDictModel):
    new_job_id: Any
    original_job_id: Any
    status: Any

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

app.add_middleware(GovernanceMiddleware, api_key_resolver=reject_api_key_unsupported, rate_limiter=redis_rate_limiter)

# Add metrics middleware if available â€” INNERMOST
if metrics:
    metrics_middleware = MetricsMiddleware(metrics)
    app.middleware("http")(metrics_middleware)



# Create router for spec-compliant endpoints
router = APIRouter(prefix="/api/v1/ingestion")


# =============================================================================
# DEPENDENCY: ORGANIZATION ID (Multi-tenancy)
# =============================================================================


def get_tenant_id(request: Request) -> UUID:
    """Extract organization (tenant) ID from the GovernanceMiddleware context.
    """
    ctx = getattr(request.state, "governance_context", None)
    header_value = request.headers.get("X-Organization-ID")
    if ctx is not None:
        if header_value and str(header_value) != str(ctx.tenant_id):
            raise AuthorizationError(message = "X-Organization-ID does not match authenticated tenant")
        return ctx.tenant_id

    if header_value:
        try:
            UUID(header_value)
        except ValueError:
            raise ValidationError(message = "Invalid X-Organization-ID header format")

    raise AuthenticationError(message = "Authentication required")


def get_current_user_id(request: Request) -> UUID:
    """Extract user ID from the GovernanceMiddleware context."""
    ctx = getattr(request.state, "governance_context", None)
    if ctx is not None and ctx.user_id:
        try:
            return UUID(ctx.user_id)
        except ValueError:
            logger.error(
                "invalid_user_id_format",
                user_id=ctx.user_id,
                path=request.url.path,
                error="UUID parsing failed",
            )
            metrics = get_metrics()
            if metrics:
                metrics.increment_errors(error_type="invalid_uuid", component="auth")
            raise AuthenticationError(message = "Invalid user ID format")
    # P0 FIX: Never fall back to a hardcoded user â€” require authentication
    raise AuthenticationError(message = "Authentication required")


# =============================================================================
# PYDANTIC SCHEMAS - ScrapingTarget
# =============================================================================


class ExtractionConfigInput(BaseModel):
    """Extraction configuration for a target."""

    method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    llm_provider: LLMProvider | None = None
    extraction_schema: dict[str, Any] | None = None
    visual_hints: bool = False
    max_depth: int | None = Field(None, ge=0, le=10)
    follow_links: bool = True
    link_selectors: list[str] | None = None


class BrowserConfigInput(BaseModel):
    """Browser configuration for a target."""

    engine: BrowserEngine = BrowserEngine.CHROMIUM
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str | None = None
    javascript_enabled: bool = True
    wait_for_selector: str | None = None
    wait_timeout: int = 30000
    stealth_mode: bool = True


def _validate_cron_expression(expr: str) -> str:
    """Parse and validate a 5-field cron expression using croniter.

    Raises ValueError with a human-readable message on any of:
    - Non-standard macros (@reboot, @yearly, etc.) â€” not schedulable by Celery Beat
    - Wrong field count (must be exactly 5: minute hour dom month dow)
    - Out-of-range or syntactically invalid field values
    """
    from croniter import CroniterBadCronError, croniter

    expr = expr.strip()

    # Reject @-macros â€” Celery Beat requires explicit 5-field expressions
    if expr.startswith("@"):
        raise ValueError(
            f"Cron macro '{expr}' is not supported; use an explicit 5-field expression "
            "(e.g. '0 * * * *' instead of '@hourly')"
        )

    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(
            f"Cron expression must have exactly 5 fields "
            f"(minute hour day-of-month month day-of-week), got {len(parts)}: '{expr}'"
        )

    try:
        # croniter raises CroniterBadCronError for invalid field values
        croniter(expr)
    except CroniterBadCronError as exc:
        raise ValueError(f"Invalid cron expression '{expr}': {exc}") from exc

    return expr


class ScheduleInput(BaseModel):
    """Schedule configuration for a target."""

    enabled: bool = False
    cron_expression: str | None = None
    timezone: str = "UTC"
    max_concurrent_jobs: int = Field(default=1, ge=1, le=100)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is not None:
            v = _validate_cron_expression(v)
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in available_timezones():
            raise ValueError(
                f"Unknown timezone '{v}'. Use an IANA timezone name "
                "(e.g. 'America/New_York', 'Europe/London', 'UTC')."
            )
        return v


class RateLimitInput(BaseModel):
    """Rate limiting configuration."""

    requests_per_second: float = 1.0
    requests_per_minute: int = 30
    requests_per_hour: int = 500
    burst_limit: int = 5
    retry_attempts: int = 3
    retry_backoff: RetryBackoff = RetryBackoff.EXPONENTIAL
    retry_delay_ms: int = 1000


class ComplianceInput(BaseModel):
    """Compliance settings."""

    respect_robots_txt: bool = True
    strict_robots_compliance: bool = False
    user_agent_string: str | None = None
    crawl_delay_seconds: float = 1.0
    domain_allowlist: list[str] = []
    domain_blocklist: list[str] = []
    pii_redaction_enabled: bool = True
    sensitive_field_patterns: list[str] = []


class ProxyConfigInput(BaseModel):
    """Proxy configuration."""

    enabled: bool = False
    rotation_strategy: ProxyRotationStrategy = ProxyRotationStrategy.ROUND_ROBIN
    proxy_pool_id: UUID | None = None
    sticky_sessions: bool = False
    session_duration_minutes: int | None = None


class AuthenticationInput(BaseModel):
    """Authentication configuration."""

    type: AuthenticationType = AuthenticationType.NONE
    credentials_ref: str | None = None


class CreateTargetRequest(BaseModel):
    """Request to create a scraping target."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    url: str = Field(..., description="Target URL")
    target_type: TargetType = TargetType.SINGLE_PAGE
    crawl_path: CrawlPath = CrawlPath.BROWSER  # HTTPX Fast Path selection
    extraction_config: ExtractionConfigInput = Field(default_factory=lambda: ExtractionConfigInput())
    browser_config: BrowserConfigInput = Field(default_factory=lambda: BrowserConfigInput())
    schedule: ScheduleInput | None = None
    rate_limit: RateLimitInput = Field(default_factory=lambda: RateLimitInput())
    compliance: ComplianceInput = Field(default_factory=lambda: ComplianceInput())
    proxy_config: ProxyConfigInput = Field(default_factory=lambda: ProxyConfigInput())
    authentication: AuthenticationInput | None = None
    tags: list[str] = []


class UpdateTargetRequest(BaseModel):
    """Request to update a scraping target."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    target_type: TargetType | None = None
    crawl_path: CrawlPath | None = None  # HTTPX Fast Path selection
    extraction_config: ExtractionConfigInput | None = None
    browser_config: BrowserConfigInput | None = None
    schedule: ScheduleInput | None = None
    rate_limit: RateLimitInput | None = None
    compliance: ComplianceInput | None = None
    proxy_config: ProxyConfigInput | None = None
    authentication: AuthenticationInput | None = None
    tags: list[str] | None = None
    status: TargetStatus | None = None


class ScrapingTargetSummary(BaseModel):
    """Summary of a scraping target."""

    id: UUID
    name: str
    url: str
    target_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_success_at: datetime | None = None
    success_count: int
    error_count: int
    average_execution_time_ms: int
    tags: list[str]


class ScrapingTargetDetail(ScrapingTargetSummary):
    """Detailed scraping target response."""

    tenant_id: UUID
    description: str | None
    url_pattern: str | None
    crawl_path: str  # HTTPX Fast Path selection
    extraction_config: dict[str, Any]
    browser_config: dict[str, Any]
    schedule: dict[str, Any] | None
    rate_limit: dict[str, Any]
    compliance: dict[str, Any]
    proxy_config: dict[str, Any]
    authentication: dict[str, Any] | None
    created_by: UUID
    last_error_at: datetime | None


class TargetListResponse(BaseModel):
    """List of scraping targets."""

    data: list[ScrapingTargetSummary]
    pagination: dict[str, Any]


class ValidateTargetRequest(BaseModel):
    """Request to validate a target configuration."""

    test_url: str | None = None
    validate_robots_txt: bool = True
    validate_schema: bool = True
    test_browser_connection: bool = False


class ValidationError(BaseModel):
    """Validation error detail."""

    field: str
    message: str
    severity: str = "error"


class ValidationWarning(BaseModel):
    """Validation warning detail."""

    field: str
    message: str


class ValidateTargetResponse(BaseModel):
    """Response from target validation."""

    valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationWarning]
    robots_txt_check: dict[str, Any] | None = None
    schema_validation: dict[str, Any] | None = None
    browser_test: dict[str, Any] | None = None


class ExecuteTargetRequest(BaseModel):
    """Request to execute a target."""

    priority: int = Field(default=5, ge=1, le=10)
    override_config: dict[str, Any] | None = None
    callback_url: str | None = None
    webhook_events: list[str] | None = None
    idempotency_key: str | None = Field(default=None, max_length=255)


class ExecuteTargetResponse(BaseModel):
    """Response from target execution."""

    job_id: UUID
    status: str
    estimated_start_time: datetime | None = None
    queue_position: int | None = None
    queue_position_metadata: dict[str, Any] | None = None


# =============================================================================
# PYDANTIC SCHEMAS - ScrapingJob
# =============================================================================


class JobSummary(BaseModel):
    """Summary of a scraping job."""

    id: UUID
    target_id: UUID
    status: str
    priority: int
    progress_percent_complete: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobStageDetailResponse(BaseModel):
    """Pipeline stage detail."""

    stage: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_message: str | None = None


class JobErrorResponse(BaseModel):
    """Job error detail."""

    id: UUID
    stage: str
    error_code: str
    error_message: str
    url: str | None = None
    retryable: bool
    retry_count: int
    occurred_at: datetime
    resolved_at: datetime | None = None


class ResourceUsageDetail(BaseModel):
    """Resource usage metrics."""

    browser_sessions_used: int
    proxy_requests_made: int
    llm_tokens_consumed: int
    compute_time_ms: int


class JobResultsDetail(BaseModel):
    """Job results summary."""

    raw_content_count: int
    extracted_record_count: int
    storage_bytes_used: int
    output_location: str | None = None


class JobProgressDetail(BaseModel):
    """Job progress information."""

    total_pages: int | None = None
    processed_pages: int
    failed_pages: int
    current_url: str | None = None
    current_stage: str
    percent_complete: int


class ScrapingJobDetail(BaseModel):
    """Detailed job response."""

    id: UUID
    tenant_id: UUID
    target_id: UUID
    configuration: dict[str, Any]
    status: str
    priority: int
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_duration_ms: int | None = None
    progress: JobProgressDetail
    results: JobResultsDetail
    resources: ResourceUsageDetail
    triggered_by: str
    correlation_id: str | None = None
    created_at: datetime
    created_by: UUID
    stages: list[JobStageDetailResponse]
    errors: list[JobErrorResponse]


class JobListResponse(BaseModel):
    """List of jobs response."""

    data: list[JobSummary]
    aggregation: dict[str, Any]
    pagination: dict[str, Any]


class RetryJobRequest(BaseModel):
    """Request to retry a job."""

    retry_strategy: str = "FULL"  # FULL, FAILED_ONLY, FROM_STAGE
    from_stage: str | None = None
    max_retries: int = 3


class CreateLicensingCompanyIntakeRequest(BaseModel):
    """Request to create a licensing company ontology intake job."""

    target_id: UUID
    company_name: str
    company_id: str | None = None
    priority: int = 5
    override_config: dict[str, Any] | None = None


class CreateProspectResearchRequest(BaseModel):
    """Request to create a prospect research job."""

    target_id: UUID
    account_name: str
    account_id: str | None = None
    priority: int = 5
    override_config: dict[str, Any] | None = None


class SkillJobResponse(BaseModel):
    """Response for skill-aware job creation."""

    job_id: UUID
    status: str
    job_type: str
    skill_name: str
    queue_position: int
    queue_position_metadata: dict[str, str]
    estimated_start_time: datetime | None = None


class SourceCorpusResponse(BaseModel):
    """SourceCorpus API response."""

    id: UUID
    tenant_id: UUID
    company_id: str | None
    company_name: str
    corpus_type: str
    source_groups: list[dict[str, Any]]
    candidate_concepts: list[str]
    provenance: list[dict[str, Any]]
    extraction_status: str
    created_at: datetime
    updated_at: datetime


class AccountIntelligencePacketResponse(BaseModel):
    """AccountIntelligencePacket API response."""

    id: UUID
    tenant_id: UUID
    account_id: str | None
    account_name: str
    packet_type: str
    company_profile: dict[str, Any]
    observed_signals: list[dict[str, Any]]
    likely_pain_areas: list[str]
    likely_stakeholders: list[str]
    source_references: list[dict[str, Any]]
    confidence_summary: dict[str, Any]
    next_recommended_events: list[str]
    created_at: datetime
    updated_at: datetime


class SourceCorpusSummary(BaseModel):
    """Summary view of a SourceCorpus for list responses.

    Omits raw provenance arrays to keep list payloads compact.
    """

    id: UUID
    company_name: str
    company_id: str | None
    corpus_type: str
    source_count: int
    extraction_status: str
    created_at: datetime


class SourceCorpusListResponse(BaseModel):
    """Paginated list of SourceCorpus summaries."""

    items: list[SourceCorpusSummary]
    total: int
    limit: int
    next_cursor: str | None


class AccountIntelligencePacketSummary(BaseModel):
    """Summary view of an AccountIntelligencePacket for list responses.

    Omits raw source_references to keep list payloads compact.
    """

    id: UUID
    account_name: str
    account_id: str | None
    packet_type: str
    observed_signal_count: int
    high_confidence_signal_count: int
    created_at: datetime


class AccountIntelligencePacketListResponse(BaseModel):
    """Paginated list of AccountIntelligencePacket summaries."""

    items: list[AccountIntelligencePacketSummary]
    total: int
    limit: int
    next_cursor: str | None


class JobProgressResponse(BaseModel):
    """Real-time job progress."""

    job_id: UUID
    status: str
    progress: JobProgressDetail
    last_update: datetime


# =============================================================================
# PYDANTIC SCHEMAS - Crawl Decisions (HTTPX Fast Path)
# =============================================================================


class CrawlDecisionSummary(BaseModel):
    """Summary of a crawl decision for API responses."""

    decision_id: UUID
    url: str
    router_decision: str
    router_rule: str
    final_path: str
    fallback_reason: str | None
    fetch_time_ms: int
    created_at: datetime


class RouterQualityReportResponse(BaseModel):
    """Quality metrics for a job's routing decisions."""

    job_id: UUID
    total_urls: int
    fast_path_count: int
    browser_path_count: int
    fallback_count: int
    fallback_rate: float
    quality_gate_accuracy: float
    top_router_rules: dict[str, int]
    avg_fetch_time_ms: float
    slowest_url: str | None
    fastest_url: str | None


class DomainFallbackStatsResponse(BaseModel):
    """Fallback statistics for a domain."""

    domain: str
    total_decisions: int
    fast_count: int
    browser_count: int
    fallback_count: int
    fallback_rate: float
    top_fallback_reasons: dict[str, int]
    avg_fast_duration_ms: float
    avg_browser_duration_ms: float


# =============================================================================
# PYDANTIC SCHEMAS - Content
# =============================================================================


class RawContentResponse(BaseModel):
    """Raw content response."""

    id: UUID
    job_id: UUID
    source_url: str
    source_final_url: str | None
    source_domain: str
    source_http_status: int | None
    storage: dict[str, str | None]
    metadata: dict[str, Any]
    capture: dict[str, Any]
    content_hash: str | None
    is_duplicate: bool
    processing_status: str
    created_at: datetime


class ExtractedDataResponse(BaseModel):
    """Extracted data response."""

    id: UUID
    job_id: UUID
    raw_content_id: UUID
    extraction_method: str
    extraction_confidence_score: float
    data: dict[str, Any]
    validation: dict[str, Any]
    post_processing: dict[str, Any]
    created_at: datetime


class ContentListResponse(BaseModel):
    """List of raw content items."""

    items: list[RawContentResponse]
    total: int
    page: int
    per_page: int


# =============================================================================
# PYDANTIC SCHEMAS - Compliance
# =============================================================================


class ComplianceLogResponse(BaseModel):
    """Compliance log entry."""

    id: UUID
    event_type: str
    severity: str
    request_url: str
    request_timestamp: datetime
    response_action_taken: str | None
    response_reason: str | None
    created_at: datetime


class ComplianceSummaryResponse(BaseModel):
    """Compliance summary statistics."""

    period: dict[str, datetime]
    robots_txt_compliance: dict[str, int | None | dict[str, Any]]
    rate_limiting: dict[str, int | None | dict[str, Any]]
    pii_detection: dict[str, int]
    domain_policies: dict[str, int | None | dict[str, Any]]


# =============================================================================
# PYDANTIC SCHEMAS - Health & Admin
# =============================================================================


class ComponentHealth(BaseModel):
    """Component health status."""

    status: str  # healthy, degraded, unhealthy
    latency_ms: int | None = None
    message: str | None = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str  # healthy, degraded, unhealthy
    version: str
    timestamp: datetime
    components: dict[str, ComponentHealth]
    metrics: dict[str, int | None | dict[str, Any]]


class CreateProxyPoolRequest(BaseModel):
    """Request to create a proxy pool."""

    name: str
    proxies: list[dict[str, Any]]
    rotation_strategy: ProxyRotationStrategy = ProxyRotationStrategy.ROUND_ROBIN


class ProxyPoolResponse(BaseModel):
    """Proxy pool response."""

    id: UUID
    name: str
    proxy_count: int
    rotation_strategy: str
    created_at: datetime


# =============================================================================
# API ENDPOINTS - ScrapingTarget
# =============================================================================


@router.get("/targets", response_model=TargetListResponse)
async def list_targets(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: TargetStatus | None = Query(None),
    search: str | None = Query(None, description="Search in name, description, url"),
    tags: list[str] | None = Query(None),
    sort_by: str = Query(
        default="created_at", regex="^(created_at|updated_at|last_success_at|name)$"
    ),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List all scraping targets for the organization."""
    query = db.query(ScrapingTarget).filter(ScrapingTarget.tenant_id == org_id)

    if status:
        query = query.filter(ScrapingTarget.status == status.value)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (ScrapingTarget.name.ilike(search_filter))
            | (ScrapingTarget.description.ilike(search_filter))
            | (ScrapingTarget.url.ilike(search_filter))
        )

    if tags:
        # JSONB containment check
        for tag in tags:
            query = query.filter(ScrapingTarget.tags.contains([tag]))

    total = query.count()
    total_pages = (total + limit - 1) // limit

    # Apply sorting
    sort_column = getattr(ScrapingTarget, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    offset = (page - 1) * limit
    targets = query.offset(offset).limit(limit).all()

    return TargetListResponse(
        data=[
            ScrapingTargetSummary(
                id=t.id,  # type: ignore[arg-type]
                name=t.name,  # type: ignore[arg-type]
                url=t.url,  # type: ignore[arg-type]
                target_type=t.target_type,  # type: ignore[arg-type]
                status=t.status,  # type: ignore[arg-type]
                created_at=t.created_at,  # type: ignore[arg-type]
                updated_at=t.updated_at,  # type: ignore[arg-type]
                last_success_at=t.last_success_at,  # type: ignore[arg-type]
                success_count=t.success_count,  # type: ignore[arg-type]
                error_count=t.error_count,  # type: ignore[arg-type]
                average_execution_time_ms=t.average_execution_time_ms,  # type: ignore[arg-type]
                tags=t.tags or [],
            )
            for t in targets
        ],
        pagination={"page": page, "limit": limit, "total": total, "total_pages": total_pages},
    )


@router.post("/targets", response_model=ScrapingTargetDetail, status_code=201)
async def create_target(
    request: CreateTargetRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a new scraping target."""
    # Validate URL
    try:
        validated = validate_url_safety(
            request.url, allowlist_domains=request.compliance.domain_allowlist
        )
    except URLSafetyError as exc:
        raise ValidationError(message = str(_url_safety_error_payload(exc.reason_code))) from exc

    # Validate extraction schema if method requires LLM
    if (
        request.extraction_config.method == ExtractionMethod.AI_LLM
        and not request.extraction_config.llm_provider
    ):
        raise ValidationError(message = "llm_provider is required when method is AI_LLM")

    # Build config objects
    extraction_config = {
        "method": request.extraction_config.method.value,
        "llm_provider": request.extraction_config.llm_provider.value
        if request.extraction_config.llm_provider
        else None,
        "extraction_schema": request.extraction_config.extraction_schema,
        "visual_hints": request.extraction_config.visual_hints,
        "max_depth": request.extraction_config.max_depth,
        "follow_links": request.extraction_config.follow_links,
        "link_selectors": request.extraction_config.link_selectors,
    }

    browser_config = {
        "engine": request.browser_config.engine.value,
        "headless": request.browser_config.headless,
        "viewport": {
            "width": request.browser_config.viewport_width,
            "height": request.browser_config.viewport_height,
        },
        "user_agent": request.browser_config.user_agent,
        "javascript_enabled": request.browser_config.javascript_enabled,
        "wait_for_selector": request.browser_config.wait_for_selector,
        "wait_timeout": request.browser_config.wait_timeout,
        "stealth_mode": request.browser_config.stealth_mode,
    }

    schedule = None
    if request.schedule:
        schedule = {
            "enabled": request.schedule.enabled,
            "cron_expression": request.schedule.cron_expression,
            "timezone": request.schedule.timezone,
            "max_concurrent_jobs": request.schedule.max_concurrent_jobs,
        }

    rate_limit = {
        "requests_per_second": request.rate_limit.requests_per_second,
        "requests_per_minute": request.rate_limit.requests_per_minute,
        "requests_per_hour": request.rate_limit.requests_per_hour,
        "burst_limit": request.rate_limit.burst_limit,
        "retry_attempts": request.rate_limit.retry_attempts,
        "retry_backoff": request.rate_limit.retry_backoff.value,
        "retry_delay_ms": request.rate_limit.retry_delay_ms,
    }

    compliance = {
        "respect_robots_txt": request.compliance.respect_robots_txt,
        "strict_robots_compliance": request.compliance.strict_robots_compliance,
        "user_agent_string": request.compliance.user_agent_string,
        "crawl_delay_seconds": request.compliance.crawl_delay_seconds,
        "domain_allowlist": request.compliance.domain_allowlist,
        "domain_blocklist": request.compliance.domain_blocklist,
        "pii_redaction_enabled": request.compliance.pii_redaction_enabled,
        "sensitive_field_patterns": request.compliance.sensitive_field_patterns,
    }

    proxy_config = {
        "enabled": request.proxy_config.enabled,
        "rotation_strategy": request.proxy_config.rotation_strategy.value,
        "proxy_pool_id": str(request.proxy_config.proxy_pool_id)
        if request.proxy_config.proxy_pool_id
        else None,
        "sticky_sessions": request.proxy_config.sticky_sessions,
        "session_duration_minutes": request.proxy_config.session_duration_minutes,
    }

    authentication = None
    if request.authentication:
        authentication = {
            "type": request.authentication.type.value,
            "credentials_ref": request.authentication.credentials_ref,
        }

    # Add crawl_path to extraction config
    extraction_config["crawl_path"] = request.crawl_path.value

    target = create_scraping_target(
        tenant_id=org_id,
        name=request.name,
        url=validated.normalized_url,
        target_type=request.target_type,
        created_by=user_id,
        description=request.description,
        extraction_config=extraction_config,
        browser_config=browser_config,
        schedule=schedule,
        rate_limit=rate_limit,
        compliance=compliance,
        proxy_config=proxy_config,
        tags=request.tags,
    )

    if authentication:
        target.authentication = authentication

    db.add(target)
    db.commit()
    db.refresh(target)

    logger.info("Created scraping target", target_id=str(target.id), name=target.name)

    return _target_to_detail(target)


@router.get("/targets/{target_id}", response_model=ScrapingTargetDetail)
async def get_target(
    target_id: UUID, org_id: UUID = Depends(get_tenant_id), db: Session = Depends(get_db_from_context_sync)
):
    """Get detailed information about a specific target."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message = "Target not found")

    return _target_to_detail(target)


@router.put("/targets/{target_id}", response_model=ScrapingTargetDetail)
async def update_target(
    target_id: UUID,
    request: UpdateTargetRequest,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Update a scraping target."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message = "Target not found")

    # Check if jobs are in progress
    active_jobs = (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.target_id == target_id,
            ScrapingJob.status.in_(
                [
                    JobStatus.PENDING.value,
                    JobStatus.QUEUED.value,
                    JobStatus.VALIDATING.value,
                    JobStatus.BROWSER_ACQUIRING.value,
                    JobStatus.NAVIGATING.value,
                    JobStatus.EXTRACTING.value,
                    JobStatus.TRANSFORMING.value,
                    JobStatus.STORING.value,
                ]
            ),
        )
        .count()
    )

    if active_jobs > 0:
        raise HTTPException(
            status_code=409, detail=f"Cannot modify target with {active_jobs} active jobs"
        )

    # Update fields
    if request.name is not None:
        target.name = request.name
    if request.description is not None:
        target.description = request.description
    if request.target_type is not None:
        target.target_type = request.target_type.value
    if request.status is not None:
        target.status = request.status.value
    if request.tags is not None:
        target.tags = request.tags
    if request.crawl_path is not None:
        if target.extraction_config is None:
            target.extraction_config = {}
        target.extraction_config["crawl_path"] = request.crawl_path.value

    # Update nested configs
    if request.extraction_config:
        target.extraction_config = {
            "method": request.extraction_config.method.value,
            "llm_provider": request.extraction_config.llm_provider.value
            if request.extraction_config.llm_provider
            else None,
            "extraction_schema": request.extraction_config.extraction_schema,
            "visual_hints": request.extraction_config.visual_hints,
            "max_depth": request.extraction_config.max_depth,
            "follow_links": request.extraction_config.follow_links,
            "link_selectors": request.extraction_config.link_selectors,
        }

    if request.browser_config:
        target.browser_config = {
            "engine": request.browser_config.engine.value,
            "headless": request.browser_config.headless,
            "viewport": {
                "width": request.browser_config.viewport_width,
                "height": request.browser_config.viewport_height,
            },
            "user_agent": request.browser_config.user_agent,
            "javascript_enabled": request.browser_config.javascript_enabled,
            "wait_for_selector": request.browser_config.wait_for_selector,
            "wait_timeout": request.browser_config.wait_timeout,
            "stealth_mode": request.browser_config.stealth_mode,
        }

    if request.rate_limit:
        target.rate_limit = {
            "requests_per_second": request.rate_limit.requests_per_second,
            "requests_per_minute": request.rate_limit.requests_per_minute,
            "requests_per_hour": request.rate_limit.requests_per_hour,
            "burst_limit": request.rate_limit.burst_limit,
            "retry_attempts": request.rate_limit.retry_attempts,
            "retry_backoff": request.rate_limit.retry_backoff.value,
            "retry_delay_ms": request.rate_limit.retry_delay_ms,
        }

    if request.compliance:
        target.compliance = {
            "respect_robots_txt": request.compliance.respect_robots_txt,
            "strict_robots_compliance": request.compliance.strict_robots_compliance,
            "user_agent_string": request.compliance.user_agent_string,
            "crawl_delay_seconds": request.compliance.crawl_delay_seconds,
            "domain_allowlist": request.compliance.domain_allowlist,
            "domain_blocklist": request.compliance.domain_blocklist,
            "pii_redaction_enabled": request.compliance.pii_redaction_enabled,
            "sensitive_field_patterns": request.compliance.sensitive_field_patterns,
        }

    if request.proxy_config:
        target.proxy_config = {
            "enabled": request.proxy_config.enabled,
            "rotation_strategy": request.proxy_config.rotation_strategy.value,
            "proxy_pool_id": str(request.proxy_config.proxy_pool_id)
            if request.proxy_config.proxy_pool_id
            else None,
            "sticky_sessions": request.proxy_config.sticky_sessions,
            "session_duration_minutes": request.proxy_config.session_duration_minutes,
        }

    if request.schedule is not None:
        if request.schedule:
            target.schedule = {
                "enabled": request.schedule.enabled,
                "cron_expression": request.schedule.cron_expression,
                "timezone": request.schedule.timezone,
                "max_concurrent_jobs": request.schedule.max_concurrent_jobs,
            }
        else:
            target.schedule = None

    if request.authentication is not None:
        if request.authentication:
            target.authentication = {
                "type": request.authentication.type.value,
                "credentials_ref": request.authentication.credentials_ref,
            }
        else:
            target.authentication = None

    target.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(target)

    logger.info("Updated scraping target", target_id=str(target.id))

    return _target_to_detail(target)


@router.delete("/targets/{target_id}", status_code=204)
async def delete_target(
    target_id: UUID,
    force: bool = Query(default=False, description="Hard delete if no jobs exist"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Archive a scraping target (soft delete)."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message = "Target not found")

    job_count = db.query(ScrapingJob).filter(ScrapingJob.target_id == target_id).count()

    if force and job_count == 0:
        # Hard delete
        db.delete(target)
        logger.info("Hard deleted scraping target", target_id=str(target_id))
    else:
        # Soft delete (archive)
        if job_count > 0:
            target.status = TargetStatus.ARCHIVED.value
        else:
            db.delete(target)
        logger.info("Archived scraping target", target_id=str(target_id))

    return None


@router.post("/targets/{target_id}/validate", response_model=ValidateTargetResponse)
async def validate_target(
    target_id: UUID,
    request: ValidateTargetRequest,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Validate target configuration without executing."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message = "Target not found")

    errors = []
    warnings = []
    robots_check = None

    # Validate URL
    test_url = request.test_url or target.url
    try:
        validate_url_safety(test_url, allowlist_domains=(target.compliance or {}).get("domain_allowlist"))
    except URLSafetyError as exc:
        errors.append(
            ValidationError(
                field="url", message=f"URL blocked by compliance policy ({exc.reason_code})"
            )
        )

    # Validate extraction schema
    if request.validate_schema and target.extraction_config.get("extraction_schema"):
        schema = target.extraction_config.get("extraction_schema")
        if not isinstance(schema, dict):
            errors.append(
                ValidationError(
                    field="extraction_schema",
                    message="Extraction schema must be a valid JSON object",
                )
            )

    # Check robots.txt
    if request.validate_robots_txt:
        from urllib.parse import urlparse

        from ..compliance.robots_checker import RobotsChecker
        parsed = urlparse(test_url)
        checker = RobotsChecker(tenant_id=str(org_id))
        domain = parsed.netloc
        allowed, reason, rules = await checker.check_url(domain, test_url)
        robots_check = {"allowed": allowed, "crawl_delay": rules.get("crawl_delay") if rules else None}
        if not allowed:
            warnings.append(
                ValidationWarning(field="robots_txt", message=reason or "URL is disallowed by robots.txt")
            )

    valid = len(errors) == 0

    return ValidateTargetResponse(
        valid=valid, errors=errors, warnings=warnings, robots_txt_check=robots_check
    )


@router.post("/targets/{target_id}/execute", response_model=ExecuteTargetResponse, status_code=202)
async def execute_target(
    target_id: UUID,
    request: ExecuteTargetRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Trigger immediate execution of a target with idempotency support."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message = "Target not found")

    if target.status != TargetStatus.ACTIVE.value:
        raise HTTPException(
            status_code=409, detail=f"Target is not active (status: {target.status})"
        )

    # P0-04: Idempotency check with atomic SET NX to prevent race condition
    if request.idempotency_key:
        idempotency_key = f"idempotency:{org_id}:{target_id}:{request.idempotency_key}"
        from ..shared.database import redis_client
        if redis_client:
            # Try to set idempotency key atomically (only if not exists)
            # This prevents race condition where multiple requests create duplicate jobs
            job_id_placeholder = f"placeholder:{uuid4()}"
            set_result = redis_client.set(idempotency_key, job_id_placeholder, nx=True, ex=86400)
            
            if set_result is None:
                # Key already exists - return existing job
                existing_job_id = redis_client.get(idempotency_key)
                if existing_job_id and not existing_job_id.startswith("placeholder:"):
                    logger.info(
                        "Idempotency key hit, returning existing job",
                        idempotency_key=request.idempotency_key,
                        job_id=existing_job_id,
                    )
                    # Verify job exists and is recent (within 24h)
                    existing_job = db.query(ScrapingJob).get(UUID(existing_job_id))
                    if existing_job and existing_job.tenant_id == org_id:
                        from ..metrics.prometheus_metrics import get_metrics
                        metrics = get_metrics()
                        if metrics and metrics.config.enabled:
                            metrics.increment_idempotency_key_hit()
                        return ExecuteTargetResponse(
                            job_id=UUID(existing_job_id),
                            status=existing_job.status,
                            estimated_start_time=existing_job.started_at,
                            queue_position=None,
                            queue_position_metadata=None,
                        )
                    else:
                        # Job not found or tenant mismatch, clear stale key
                        redis_client.delete(idempotency_key)
                else:
                    # Placeholder from another concurrent request - wait and retry or proceed
                    # For simplicity, we'll clear and proceed (could be improved with retry logic)
                    redis_client.delete(idempotency_key)
            else:
                # Successfully claimed idempotency key
                from ..metrics.prometheus_metrics import get_metrics
                metrics = get_metrics()
                if metrics and metrics.config.enabled:
                    metrics.increment_idempotency_key_miss()

    # Create configuration snapshot
    configuration = {
        "target_id": str(target.id),
        "target_name": target.name,
        "url": target.url,
        "target_type": target.target_type,
        "extraction_config": target.extraction_config,
        "browser_config": target.browser_config,
        "rate_limit": target.rate_limit,
        "compliance": target.compliance,
        "proxy_config": target.proxy_config,
        "authentication": target.authentication,
        "override_config": request.override_config,
    }

    # Create job
    correlation_id = str(uuid4())
    job = create_scraping_job(
        tenant_id=org_id,
        target_id=target_id,
        created_by=user_id,
        configuration=configuration,
        priority=request.priority,
        triggered_by=TriggeredBy.API,
        correlation_id=correlation_id,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # P0-04: Update idempotency key with actual job ID if provided
    if request.idempotency_key:
        idempotency_key = f"idempotency:{org_id}:{target_id}:{request.idempotency_key}"
        from ..shared.database import redis_client
        if redis_client:
            redis_client.setex(idempotency_key, 86400, str(job.id))  # 24h TTL

    # Initialize pipeline stages
    for stage in PipelineStage:
        stage_detail = JobStageDetail(
            job_id=job.id, tenant_id=org_id, stage=stage.value, status="PENDING"
        )
        db.add(stage_detail)


    # Queue job
    job.status = JobStatus.QUEUED.value

    # Start background processing with tenant context envelope
    process_scraping_job.delay(str(job.id), str(job.tenant_id))

    logger.info("Queued scraping job", job_id=str(job.id), target_id=str(target_id))

    return ExecuteTargetResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        queue_position=db.query(ScrapingJob)
        .filter(
            ScrapingJob.tenant_id == org_id,
            ScrapingJob.status == JobStatus.QUEUED.value,
            ScrapingJob.created_at <= job.created_at,
        )
        .count(),
        queue_position_metadata={
            "calculation": "count_queued_jobs_created_before_or_at_current_job",
            "scope": "organization",
        },
        estimated_start_time=None,
    )


# =============================================================================
# API ENDPOINTS - Crawl Decisions (HTTPX Fast Path)
# =============================================================================


@router.get("/targets/{target_id}/decisions", response_model=list[CrawlDecisionSummary])
async def get_target_decisions(
    target_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get recent crawl decisions for a target's jobs.

    Returns the most recent crawl decisions across all jobs
    for this target, showing routing choices and outcomes.
    """
    # Verify target exists and belongs to org
    target = db.query(ScrapingTarget).filter(
        ScrapingTarget.id == target_id,
        ScrapingTarget.tenant_id == org_id
    ).first()

    if not target:
        raise NotFoundError(message = "Target not found")

    # Get decisions for all jobs of this target
    jobs = db.query(ScrapingJob).filter(ScrapingJob.target_id == target_id).all()
    job_ids = [str(j.id) for j in jobs]

    repo = CrawlDecisionRepository(db)
    all_decisions = []

    for job_id in job_ids[:5]:  # Limit to recent 5 jobs
        decisions = await repo.get_by_job(job_id, limit=20)
        all_decisions.extend(decisions)

    # Sort by created_at desc and limit
    all_decisions.sort(key=lambda d: d.created_at, reverse=True)
    all_decisions = all_decisions[:limit]

    return [
        CrawlDecisionSummary(
            decision_id=UUID(d.decision_id),
            url=d.url,
            router_decision=d.router_decision,
            router_rule=d.router_rule,
            final_path=d.final_path,
            fallback_reason=d.fallback_reason,
            fetch_time_ms=d.fetch_time_ms,
            created_at=d.created_at,
        )
        for d in all_decisions
    ]


@router.get("/jobs/{job_id}/router-report", response_model=RouterQualityReportResponse)
async def get_job_router_report(
    job_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get routing quality report for a specific job.

    Provides metrics on routing accuracy, fallback rates,
    and performance characteristics for analysis.
    """
    # Verify job exists and belongs to org
    job = db.query(ScrapingJob).filter(
        ScrapingJob.id == job_id,
        ScrapingJob.tenant_id == org_id
    ).first()

    if not job:
        raise NotFoundError(message = "Job not found")

    repo = CrawlDecisionRepository(db)
    report = await repo.get_router_quality_report(str(job_id))

    return RouterQualityReportResponse(
        job_id=UUID(report.job_id),
        total_urls=report.total_urls,
        fast_path_count=report.fast_path_count,
        browser_path_count=report.browser_path_count,
        fallback_count=report.fallback_count,
        fallback_rate=report.fallback_rate,
        quality_gate_accuracy=report.quality_gate_accuracy,
        top_router_rules=report.top_router_rules,
        avg_fetch_time_ms=report.avg_fetch_time_ms,
        slowest_url=report.slowest_url,
        fastest_url=report.fastest_url,
    )


@router.get("/domains/{domain}/fallback-stats", response_model=DomainFallbackStatsResponse)
async def get_domain_fallback_stats(
    domain: str,
    days: int = Query(default=7, ge=1, le=30),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get fallback statistics for a specific domain.

    Shows how often the router falls back to browser for this
    domain, helping identify SPA-heavy sites or routing issues.
    """
    from datetime import timedelta

    # Verify org has crawled this domain (basic authorization check)
    has_access = db.query(CrawlDecision).filter(
        CrawlDecision.domain == domain,
        CrawlDecision.tenant_id == org_id
    ).first()

    if not has_access:
        # Check if any target URL matches this domain
        has_target = db.query(ScrapingTarget).filter(
            ScrapingTarget.tenant_id == org_id,
            ScrapingTarget.url.ilike(f"%{domain}%")
        ).first()

        if not has_target:
            raise AuthorizationError(message = "No access to this domain")

    since = datetime.now(UTC) - timedelta(days=days)
    repo = CrawlDecisionRepository(db)
    stats = await repo.get_fallback_stats(domain, since=since)

    return DomainFallbackStatsResponse(
        domain=stats.domain,
        total_decisions=stats.total_decisions,
        fast_count=stats.fast_count,
        browser_count=stats.browser_count,
        fallback_count=stats.fallback_count,
        fallback_rate=stats.fallback_rate,
        top_fallback_reasons=stats.top_fallback_reasons,
        avg_fast_duration_ms=stats.avg_fast_duration_ms,
        avg_browser_duration_ms=stats.avg_browser_duration_ms,
    )


# =============================================================================
# API ENDPOINTS - ScrapingJob
# =============================================================================


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    target_id: UUID | None = Query(None),
    status: list[JobStatus] | None = Query(None),
    triggered_by: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    priority_min: int | None = Query(None, ge=1, le=10),
    priority_max: int | None = Query(None, ge=1, le=10),
    has_errors: bool | None = Query(None),
    sort_by: str = Query(
        default="created_at", regex="^(created_at|started_at|completed_at|priority)$"
    ),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List all scraping jobs with filtering and pagination."""
    query = db.query(ScrapingJob).filter(ScrapingJob.tenant_id == org_id)

    if target_id:
        query = query.filter(ScrapingJob.target_id == target_id)

    if status:
        status_values = [s.value for s in status]
        query = query.filter(ScrapingJob.status.in_(status_values))

    if triggered_by:
        query = query.filter(ScrapingJob.triggered_by == triggered_by)

    if date_from:
        query = query.filter(ScrapingJob.created_at >= date_from)

    if date_to:
        query = query.filter(ScrapingJob.created_at <= date_to)

    if priority_min is not None:
        query = query.filter(ScrapingJob.priority >= priority_min)

    if priority_max is not None:
        query = query.filter(ScrapingJob.priority <= priority_max)

    if has_errors is not None:
        if has_errors:
            query = query.filter(ScrapingJob.errors.any())
        else:
            query = query.filter(~ScrapingJob.errors.any())

    # Aggregation
    total = query.count()
    total_pages = (total + limit - 1) // limit

    status_counts = (
        db.query(ScrapingJob.status, func.count(ScrapingJob.id))
        .filter(ScrapingJob.tenant_id == org_id)
        .group_by(ScrapingJob.status)
        .all()
    )

    by_status = {status: count for status, count in status_counts}

    # Apply sorting
    sort_column = getattr(ScrapingJob, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    offset = (page - 1) * limit
    jobs = query.offset(offset).limit(limit).all()

    return JobListResponse(
        data=[
            JobSummary(
                id=j.id,
                target_id=j.target_id,
                status=j.status,
                priority=j.priority,
                progress_percent_complete=j.progress_percent_complete,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
            )
            for j in jobs
        ],
        aggregation={
            "by_status": by_status,
            "total_execution_time_ms": sum(j.resources_compute_time_ms for j in jobs),
            "total_records_extracted": sum(j.results_extracted_record_count for j in jobs),
        },
        pagination={"page": page, "limit": limit, "total": total, "total_pages": total_pages},
    )


@router.get("/jobs/{job_id}", response_model=ScrapingJobDetail)
async def get_job(
    job_id: UUID, org_id: UUID = Depends(get_tenant_id), db: Session = Depends(get_db_from_context_sync)
):
    """Get detailed job information including execution stages."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message = "Job not found")

    stages = (
        db.query(JobStageDetail)
        .filter(JobStageDetail.job_id == job_id)
        .order_by(JobStageDetail.created_at)
        .all()
    )

    errors = (
        db.query(JobError)
        .filter(JobError.job_id == job_id)
        .order_by(JobError.occurred_at.desc())
        .all()
    )

    return ScrapingJobDetail(
        id=job.id,
        tenant_id=job.tenant_id,
        target_id=job.target_id,
        configuration=job.configuration,
        status=job.status,
        priority=job.priority,
        scheduled_at=job.scheduled_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        estimated_duration_ms=job.estimated_duration_ms,
        progress=JobProgressDetail(
            total_pages=job.progress_total_pages,
            processed_pages=job.progress_processed_pages,
            failed_pages=job.progress_failed_pages,
            current_url=job.progress_current_url,
            current_stage=job.progress_stage,
            percent_complete=job.progress_percent_complete,
        ),
        results=JobResultsDetail(
            raw_content_count=job.results_raw_content_count,
            extracted_record_count=job.results_extracted_record_count,
            storage_bytes_used=job.results_storage_bytes_used,
            output_location=job.results_output_location,
        ),
        resources=ResourceUsageDetail(
            browser_sessions_used=job.resources_browser_sessions_used,
            proxy_requests_made=job.resources_proxy_requests_made,
            llm_tokens_consumed=job.resources_llm_tokens_consumed,
            compute_time_ms=job.resources_compute_time_ms,
        ),
        triggered_by=job.triggered_by,
        correlation_id=job.correlation_id,
        created_at=job.created_at,
        created_by=job.created_by,
        stages=[
            JobStageDetailResponse(
                stage=s.stage,
                status=s.status,
                started_at=s.started_at,
                completed_at=s.completed_at,
                duration_ms=s.duration_ms,
                error_message=s.error_message,
            )
            for s in stages
        ],
        errors=[
            JobErrorResponse(
                id=e.id,
                stage=e.stage,
                error_code=e.error_code,
                error_message=e.error_message,
                url=e.url,
                retryable=e.retryable,
                retry_count=e.retry_count,
                occurred_at=e.occurred_at,
                resolved_at=e.resolved_at,
            )
            for e in errors
        ],
    )


@router.delete("/jobs/{job_id}", status_code=202)
async def cancel_job(
    job_id: UUID, org_id: UUID = Depends(get_tenant_id), db: Session = Depends(get_db_from_context_sync)
):
    """Cancel a running or queued job."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message = "Job not found")

    # Can only cancel jobs that haven't completed
    terminal_states = [
        JobStatus.COMPLETED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
        JobStatus.PARTIAL_SUCCESS.value,
    ]

    if job.status in terminal_states:
        raise HTTPException(status_code=409, detail=f"Job already in terminal state: {job.status}")

    job.status = JobStatus.CANCELLED.value
    job.completed_at = datetime.now(UTC)

    logger.info("Cancelled scraping job", job_id=str(job_id))

    return cancel_jobResult.model_validate({"status": "CANCELLED", "job_id": str(job_id)})


@router.get("/jobs/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(
    job_id: UUID, org_id: UUID = Depends(get_tenant_id), db: Session = Depends(get_db_from_context_sync)
):
    """Get real-time job progress."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message = "Job not found")

    return JobProgressResponse(
        job_id=job.id,
        status=job.status,
        progress=JobProgressDetail(
            total_pages=job.progress_total_pages,
            processed_pages=job.progress_processed_pages,
            failed_pages=job.progress_failed_pages,
            current_url=job.progress_current_url,
            current_stage=job.progress_stage,
            percent_complete=job.progress_percent_complete,
        ),
        last_update=datetime.now(UTC),
    )


@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    format: str = Query(default="json", regex="^(json|csv|ndjson)$"),
    include_raw: bool = Query(default=False),
    fields: list[str] | None = Query(None),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get extracted data results for a job."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message = "Job not found")

    query = db.query(ExtractedData).filter(
        ExtractedData.job_id == job_id, ExtractedData.tenant_id == org_id
    )

    total = query.count()
    offset = (page - 1) * limit
    data = query.offset(offset).limit(limit).all()

    return get_job_resultsResult.model_validate({
        "job_id": str(job_id),
        "format": format,
        "total_records": total,
        "data": [
            {
                "id": str(d.id),
                "raw_content_id": str(d.raw_content_id),
                "extraction_method": d.extraction_method,
                "confidence": float(d.extraction_confidence_score)
                if d.extraction_confidence_score
                else None,
                "data": d.data,
                "created_at": d.created_at.isoformat(),
            }
            for d in data
        ],
        "page": page,
        "limit": limit,
    })


@router.post("/jobs/{job_id}/retry", status_code=202)
async def retry_job(
    job_id: UUID,
    request: RetryJobRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retry a failed or partially successful job."""
    original_job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not original_job:
        raise NotFoundError(message = "Job not found")

    if original_job.status not in [JobStatus.FAILED.value, JobStatus.PARTIAL_SUCCESS.value]:
        raise HTTPException(
            status_code=409, detail="Only failed or partially successful jobs can be retried"
        )

    # Create new job with same configuration
    correlation_id = f"retry:{job_id}:{uuid4()}"
    new_job = create_scraping_job(
        tenant_id=org_id,
        target_id=original_job.target_id,
        created_by=user_id,
        configuration=original_job.configuration,
        priority=original_job.priority,
        triggered_by=TriggeredBy.MANUAL,
        correlation_id=correlation_id,
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Initialize stages
    for stage in PipelineStage:
        stage_detail = JobStageDetail(
            job_id=new_job.id, tenant_id=org_id, stage=stage.value, status="PENDING"
        )
        db.add(stage_detail)


    # Queue new job
    new_job.status = JobStatus.QUEUED.value

    process_scraping_job.delay(str(new_job.id), str(new_job.tenant_id))

    logger.info("Created retry job", original_job_id=str(job_id), new_job_id=str(new_job.id))

    return retry_jobResult.model_validate({
        "original_job_id": str(job_id),
        "new_job_id": str(new_job.id),
        "status": JobStatus.QUEUED.value,
    })


# =============================================================================
# UTILITY FUNCTIONS - Skill Output Response Builders
# =============================================================================


def _source_corpus_to_response(corpus: SourceCorpus) -> SourceCorpusResponse:
    """Convert a SourceCorpus DB model to its API response."""
    return SourceCorpusResponse(
        id=corpus.id,
        tenant_id=corpus.tenant_id,
        company_id=corpus.company_id,
        company_name=corpus.company_name,
        corpus_type=corpus.corpus_type,
        source_groups=corpus.source_groups or [],
        candidate_concepts=corpus.candidate_concepts or [],
        provenance=corpus.provenance or [],
        extraction_status=corpus.extraction_status,
        created_at=corpus.created_at,
        updated_at=corpus.updated_at,
    )


def _account_packet_to_response(packet: AccountIntelligencePacket) -> AccountIntelligencePacketResponse:
    """Convert an AccountIntelligencePacket DB model to its API response."""
    return AccountIntelligencePacketResponse(
        id=packet.id,
        tenant_id=packet.tenant_id,
        account_id=packet.account_id,
        account_name=packet.account_name,
        packet_type=packet.packet_type,
        company_profile=packet.company_profile or {},
        observed_signals=packet.observed_signals or [],
        likely_pain_areas=packet.likely_pain_areas or [],
        likely_stakeholders=packet.likely_stakeholders or [],
        source_references=packet.source_references or [],
        confidence_summary=packet.confidence_summary or {},
        next_recommended_events=packet.next_recommended_events or [],
        created_at=packet.created_at,
        updated_at=packet.updated_at,
    )


# =============================================================================
# API ENDPOINTS - Source Intelligence Skills
# =============================================================================


def _create_skill_job(
    db: Session,
    org_id: UUID,
    user_id: UUID,
    target_id: UUID,
    job_type: ScrapingJobType,
    entity_name: str,
    entity_id: str | None,
    priority: int,
    override_config: dict[str, Any] | None,
) -> ScrapingJob:
    """Create and queue a skill-aware scraping job."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )
    if not target:
        raise NotFoundError(message = "Target not found")

    if target.status != TargetStatus.ACTIVE.value:
        raise HTTPException(
            status_code=409, detail=f"Target is not active (status: {target.status})"
        )

    skill = get_skill(job_type.value)
    if not skill:
        raise ValidationError(message = str(f"Unknown job_type: {job_type.value}"))

    configuration = {
        "target_id": str(target.id),
        "target_name": target.name,
        "url": target.url,
        "target_type": target.target_type,
        "job_type": job_type.value,
        "company_name" if job_type == ScrapingJobType.LICENSING_COMPANY_INTAKE else "account_name": entity_name,
        "company_id" if job_type == ScrapingJobType.LICENSING_COMPANY_INTAKE else "account_id": entity_id,
        "extraction_config": target.extraction_config,
        "browser_config": target.browser_config,
        "rate_limit": target.rate_limit,
        "compliance": target.compliance,
        "proxy_config": target.proxy_config,
        "authentication": target.authentication,
        "override_config": override_config,
    }

    job = create_scraping_job(
        tenant_id=org_id,
        target_id=target_id,
        created_by=user_id,
        configuration=configuration,
        priority=priority,
        triggered_by=TriggeredBy.API,
        correlation_id=str(uuid4()),
    )
    job.job_type = job_type.value
    job.skill_name = skill.skill_name
    job.target_entity_id = entity_id
    job.target_entity_type = skill.config.target_entity_type
    job.output_contract = skill.output_contract
    job.downstream_events = skill.downstream_events

    db.add(job)
    db.commit()
    db.refresh(job)

    # Initialize pipeline stages
    for stage in PipelineStage:
        stage_detail = JobStageDetail(
            job_id=job.id, tenant_id=org_id, stage=stage.value, status="PENDING"
        )
        db.add(stage_detail)

    job.status = JobStatus.QUEUED.value
    process_scraping_job.delay(str(job.id), str(job.tenant_id))

    logger.info(
        "Queued skill-aware job",
        job_id=str(job.id),
        job_type=job_type.value,
        skill_name=skill.skill_name,
    )
    return job


@router.post("/jobs/licensing-company-intake", response_model=SkillJobResponse, status_code=202)
async def create_licensing_company_intake_job(
    request: CreateLicensingCompanyIntakeRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a skill-aware job for licensing company ontology intake."""
    job = _create_skill_job(
        db=db,
        org_id=org_id,
        user_id=user_id,
        target_id=request.target_id,
        job_type=ScrapingJobType.LICENSING_COMPANY_INTAKE,
        entity_name=request.company_name,
        entity_id=request.company_id,
        priority=request.priority,
        override_config=request.override_config,
    )

    queue_position = (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.tenant_id == org_id,
            ScrapingJob.status == JobStatus.QUEUED.value,
            ScrapingJob.created_at <= job.created_at,
        )
        .count()
    )

    return SkillJobResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        job_type=job.job_type,
        skill_name=job.skill_name or "",
        queue_position=queue_position,
        queue_position_metadata={
            "calculation": "count_queued_jobs_created_before_or_at_current_job",
            "scope": "organization",
        },
    )


@router.post("/jobs/prospect-research", response_model=SkillJobResponse, status_code=202)
async def create_prospect_research_job(
    request: CreateProspectResearchRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a skill-aware job for prospect research."""
    job = _create_skill_job(
        db=db,
        org_id=org_id,
        user_id=user_id,
        target_id=request.target_id,
        job_type=ScrapingJobType.PROSPECT_RESEARCH,
        entity_name=request.account_name,
        entity_id=request.account_id,
        priority=request.priority,
        override_config=request.override_config,
    )

    queue_position = (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.tenant_id == org_id,
            ScrapingJob.status == JobStatus.QUEUED.value,
            ScrapingJob.created_at <= job.created_at,
        )
        .count()
    )

    return SkillJobResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        job_type=job.job_type,
        skill_name=job.skill_name or "",
        queue_position=queue_position,
        queue_position_metadata={
            "calculation": "count_queued_jobs_created_before_or_at_current_job",
            "scope": "organization",
        },
    )


@router.get("/corpuses/{corpus_id}", response_model=SourceCorpusResponse)
async def get_source_corpus(
    corpus_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve a SourceCorpus by ID."""
    corpus = (
        db.query(SourceCorpus)
        .filter(SourceCorpus.id == corpus_id, SourceCorpus.tenant_id == org_id)
        .first()
    )
    if not corpus:
        raise NotFoundError(message = "Corpus not found")
    return _source_corpus_to_response(corpus)


@router.get("/intelligence-packets/{packet_id}", response_model=AccountIntelligencePacketResponse)
async def get_account_intelligence_packet(
    packet_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve an AccountIntelligencePacket by ID."""
    packet = (
        db.query(AccountIntelligencePacket)
        .filter(AccountIntelligencePacket.id == packet_id, AccountIntelligencePacket.tenant_id == org_id)
        .first()
    )
    if not packet:
        raise NotFoundError(message = "Intelligence packet not found")
    return _account_packet_to_response(packet)


@router.get("/jobs/{job_id}/skill-output")
async def get_job_skill_output(
    job_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve the skill-specific output for a completed job."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )
    if not job:
        raise NotFoundError(message = "Job not found")

    if not job.skill_name:
        raise NotFoundError(message = "Job has no skill output")

    if job.output_contract == "SourceCorpus":
        corpus = (
            db.query(SourceCorpus)
            .filter(SourceCorpus.job_id == job_id, SourceCorpus.tenant_id == org_id)
            .first()
        )
        if not corpus:
            raise NotFoundError(message = "SourceCorpus not yet available")
        return {
            "output_contract": "SourceCorpus",
            "data": _source_corpus_to_response(corpus).model_dump(),
        }

    if job.output_contract == "AccountIntelligencePacket":
        packet = (
            db.query(AccountIntelligencePacket)
            .filter(AccountIntelligencePacket.job_id == job_id, AccountIntelligencePacket.tenant_id == org_id)
            .first()
        )
        if not packet:
            raise NotFoundError(message = "AccountIntelligencePacket not yet available")
        return {
            "output_contract": "AccountIntelligencePacket",
            "data": _account_packet_to_response(packet).model_dump(),
        }

    raise ValidationError(message = str(f"Unknown output_contract: {job.output_contract}"))


# =============================================================================
# API ENDPOINTS - Source Corpora (internal, tenant-scoped)
# =============================================================================

_MAX_LIST_LIMIT = 100
_DEFAULT_LIST_LIMIT = 20


def _corpus_to_summary(corpus: SourceCorpus) -> SourceCorpusSummary:
    source_count = sum(
        g.get("count", 0) for g in (corpus.source_groups or [])
    )
    return SourceCorpusSummary(
        id=corpus.id,
        company_name=corpus.company_name,
        company_id=corpus.company_id,
        corpus_type=corpus.corpus_type,
        source_count=source_count,
        extraction_status=corpus.extraction_status,
        created_at=corpus.created_at,
    )


def _packet_to_summary(packet: AccountIntelligencePacket) -> AccountIntelligencePacketSummary:
    signals = packet.observed_signals or []
    high_conf = sum(1 for s in signals if s.get("confidence") == "high")
    return AccountIntelligencePacketSummary(
        id=packet.id,
        account_name=packet.account_name,
        account_id=packet.account_id,
        packet_type=packet.packet_type,
        observed_signal_count=len(signals),
        high_confidence_signal_count=high_conf,
        created_at=packet.created_at,
    )


@router.get("/source-corpora", response_model=SourceCorpusListResponse)
async def list_source_corpora(
    company_id: str | None = Query(default=None),
    job_id: UUID | None = Query(default=None),
    extraction_status: str | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIST_LIMIT, ge=1, le=_MAX_LIST_LIMIT),
    cursor: str | None = Query(default=None, description="ISO-8601 created_at of last seen item for cursor pagination"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List SourceCorpus records for the authenticated tenant.

    Returns summary objects only — provenance arrays are excluded.
    Tenant isolation is enforced from auth context; no cross-tenant query params accepted.
    """

    q = db.query(SourceCorpus).filter(SourceCorpus.tenant_id == org_id)

    if company_id:
        q = q.filter(SourceCorpus.company_id == company_id)
    if job_id:
        q = q.filter(SourceCorpus.job_id == job_id)
    if extraction_status:
        q = q.filter(SourceCorpus.extraction_status == extraction_status)
    if created_after:
        q = q.filter(SourceCorpus.created_at >= created_after)
    if created_before:
        q = q.filter(SourceCorpus.created_at <= created_before)
    if cursor:
        try:
            from datetime import datetime as _dt
            cursor_dt = _dt.fromisoformat(cursor)
            q = q.filter(SourceCorpus.created_at < cursor_dt)
        except ValueError:
            raise ValidationError(message = "Invalid cursor format; expected ISO-8601 datetime")

    total = q.count()
    items = q.order_by(SourceCorpus.created_at.desc()).limit(limit).all()

    next_cursor = None
    if len(items) == limit and items:
        next_cursor = items[-1].created_at.isoformat()

    return SourceCorpusListResponse(
        items=[_corpus_to_summary(c) for c in items],
        total=total,
        limit=limit,
        next_cursor=next_cursor,
    )


@router.get("/source-corpora/{corpus_id}", response_model=SourceCorpusResponse)
async def get_source_corpus_detail(
    corpus_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve a SourceCorpus by ID including full provenance.

    Returns 404 for cross-tenant access.
    """
    corpus = (
        db.query(SourceCorpus)
        .filter(SourceCorpus.id == corpus_id, SourceCorpus.tenant_id == org_id)
        .first()
    )
    if not corpus:
        raise NotFoundError(message = "SourceCorpus not found")
    return _source_corpus_to_response(corpus)


@router.get("/account-intelligence-packets", response_model=AccountIntelligencePacketListResponse)
async def list_account_intelligence_packets(
    account_id: str | None = Query(default=None),
    job_id: UUID | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIST_LIMIT, ge=1, le=_MAX_LIST_LIMIT),
    cursor: str | None = Query(default=None, description="ISO-8601 created_at of last seen item for cursor pagination"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List AccountIntelligencePacket records for the authenticated tenant.

    Returns summary objects only — source_references arrays are excluded.
    Tenant isolation is enforced from auth context; no cross-tenant query params accepted.
    """
    q = db.query(AccountIntelligencePacket).filter(
        AccountIntelligencePacket.tenant_id == org_id
    )

    if account_id:
        q = q.filter(AccountIntelligencePacket.account_id == account_id)
    if job_id:
        q = q.filter(AccountIntelligencePacket.job_id == job_id)
    if created_after:
        q = q.filter(AccountIntelligencePacket.created_at >= created_after)
    if created_before:
        q = q.filter(AccountIntelligencePacket.created_at <= created_before)
    if cursor:
        try:
            from datetime import datetime as _dt
            cursor_dt = _dt.fromisoformat(cursor)
            q = q.filter(AccountIntelligencePacket.created_at < cursor_dt)
        except ValueError:
            raise ValidationError(message = "Invalid cursor format; expected ISO-8601 datetime")

    total = q.count()
    items = q.order_by(AccountIntelligencePacket.created_at.desc()).limit(limit).all()

    next_cursor = None
    if len(items) == limit and items:
        next_cursor = items[-1].created_at.isoformat()

    return AccountIntelligencePacketListResponse(
        items=[_packet_to_summary(p) for p in items],
        total=total,
        limit=limit,
        next_cursor=next_cursor,
    )


@router.get("/account-intelligence-packets/{packet_id}", response_model=AccountIntelligencePacketResponse)
async def get_account_intelligence_packet_detail(
    packet_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve an AccountIntelligencePacket by ID including full source references.

    Returns 404 for cross-tenant access.
    """
    packet = (
        db.query(AccountIntelligencePacket)
        .filter(
            AccountIntelligencePacket.id == packet_id,
            AccountIntelligencePacket.tenant_id == org_id,
        )
        .first()
    )
    if not packet:
        raise NotFoundError(message = "AccountIntelligencePacket not found")
    return _account_packet_to_response(packet)


# =============================================================================
# API ENDPOINTS - Content
# =============================================================================


@router.get("/content/raw/{content_id}", response_model=RawContentResponse)
async def get_raw_content(
    content_id: UUID,
    include_html: bool = Query(default=True),
    include_screenshot: bool = Query(default=False),
    include_har: bool = Query(default=False),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve raw content by ID."""
    content = (
        db.query(RawContent)
        .filter(RawContent.id == content_id, RawContent.tenant_id == org_id)
        .first()
    )

    if not content:
        raise NotFoundError(message = "Content not found")

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


@router.get("/content/extracted/{extracted_data_id}", response_model=ExtractedDataResponse)
async def get_extracted_data(
    extracted_data_id: UUID,
    format: str = Query(default="json", regex="^(json|markdown|flattened)$"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retrieve extracted data by ID."""
    data = (
        db.query(ExtractedData)
        .filter(ExtractedData.id == extracted_data_id, ExtractedData.tenant_id == org_id)
        .first()
    )

    if not data:
        raise NotFoundError(message = "Extracted data not found")

    return ExtractedDataResponse(
        id=data.id,
        job_id=data.job_id,
        raw_content_id=data.raw_content_id,
        extraction_method=data.extraction_method,
        extraction_confidence_score=float(data.extraction_confidence_score)
        if data.extraction_confidence_score
        else 0.0,
        data=data.data,
        validation={
            "schema_valid": data.validation_schema_valid,
            "errors": data.validation_errors,
            "data_quality_score": float(data.validation_data_quality_score)
            if data.validation_data_quality_score
            else 0.0,
        },
        post_processing={
            "pii_redaction_applied": data.post_pii_redaction_applied,
            "redacted_fields": data.post_redacted_fields,
            "normalized_fields": data.post_normalized_fields,
            "enriched_fields": data.post_enriched_fields,
        },
        created_at=data.created_at,
    )


@router.get("/content")
async def list_content(
    job_id: UUID | None = Query(None),
    domain: str | None = Query(None),
    processing_status: str | None = Query(None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
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
    items = query.order_by(RawContent.created_at.desc()).offset(offset).limit(limit).all()

    return list_contentResult.model_validate({
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
    })


# =============================================================================
# API ENDPOINTS - Compliance
# =============================================================================


@router.get("/compliance/logs")
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
    logs = query.order_by(ComplianceLog.created_at.desc()).offset(offset).limit(limit).all()

    return list_compliance_logsResult.model_validate({
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
    })


@router.get("/compliance/summary", response_model=ComplianceSummaryResponse)
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
    average_delay_ms = int(sum(delay_values) / len(delay_values)) if delay_values else None

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
                "reason": "No delay_ms values found in compliance rate_limit_event logs"
                if average_delay_ms is None
                else None,
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


@router.get("/health", response_model=HealthCheckResponse)
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
        logger.error("health_check_database_failed", error_code="DB_HEALTH_ERROR", error=str(e))
        components["database"] = ComponentHealth(status="unhealthy", message="Database connection failed")

    # Queue check (Redis)
    try:
        from ..shared.database import redis_client

        redis_client.ping()
        components["queue"] = ComponentHealth(status="healthy", latency_ms=0)
    except Exception:
        components["queue"] = ComponentHealth(status="degraded", message="Redis not available")

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

    queued_jobs = db.query(ScrapingJob).filter(ScrapingJob.status == JobStatus.QUEUED.value).count()

    started_jobs = db.query(ScrapingJob).all()
    wait_times_ms = [
        int((job.started_at - job.created_at).total_seconds() * 1000)
        for job in started_jobs
        if job.started_at and job.created_at
    ]
    average_wait_time_ms = int(sum(wait_times_ms) / len(wait_times_ms)) if wait_times_ms else None

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
            "reason": "No started jobs available to calculate queue wait time"
            if average_wait_time_ms is None
            else None,
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


@router.get("/metrics")
async def metrics_endpoint(request: Request):
    """Prometheus-compatible metrics endpoint."""
    metrics = get_metrics()

    if not metrics:
        return Response(
            content="Metrics collection is disabled", status_code=503, media_type="text/plain"
        )

    try:
        metrics_data = metrics.get_metrics()
        return Response(content=metrics_data, media_type="text/plain; version=0.0.4; charset=utf-8")
    except Exception as e:
        return Response(
            content=f"Error generating metrics: {e}", status_code=500, media_type="text/plain"
        )


@router.post("/admin/cleanup")
async def trigger_cleanup(
    days: int = Query(default=30, ge=1, le=365),
    org_id: UUID = Depends(get_tenant_id),
):
    """Trigger content cleanup for old data.

    SECURITY: Tenant-scoped cleanup - only deletes content for the requesting tenant.
    """
    cleanup_old_content.delay(days, str(org_id))
    return trigger_cleanupResult.model_validate({
        "message": f"Cleanup initiated for content older than {days} days",
        "status": "processing",
    })


# =============================================================================
# API ENDPOINTS - Proxy Pools
# =============================================================================


@router.post("/proxy-pools", response_model=ProxyPoolResponse)
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


def _target_to_detail(target: ScrapingTarget) -> ScrapingTargetDetail:
    """Convert ScrapingTarget to ScrapingTargetDetail response."""
    return ScrapingTargetDetail(
        id=target.id,
        tenant_id=target.tenant_id,
        name=target.name,
        url=target.url,
        target_type=target.target_type,
        status=target.status,
        created_at=target.created_at,
        updated_at=target.updated_at,
        last_success_at=target.last_success_at,
        success_count=target.success_count,
        error_count=target.error_count,
        average_execution_time_ms=target.average_execution_time_ms,
        tags=target.tags or [],
        description=target.description,
        url_pattern=target.url_pattern,
        crawl_path=target.extraction_config.get("crawl_path", "browser") if target.extraction_config else "browser",
        extraction_config=target.extraction_config or {},
        browser_config=target.browser_config or {},
        schedule=target.schedule,
        rate_limit=target.rate_limit or {},
        compliance=target.compliance or {},
        proxy_config=target.proxy_config or {},
        authentication=target.authentication,
        created_by=target.created_by,
        last_error_at=target.last_error_at,
    )


# Include the router in the main app
app.include_router(router)


# Legacy compatibility routes (redirect to new endpoints)
@app.get("/health")
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
        logger.error("health_check_database_failed", error_code="DB_HEALTH_ERROR", error=str(e))
        dependencies.append({"name": "database", "status": "unhealthy", "error": "Database connection failed"})
        overall_status = "degraded"
    finally:
        db.close()

    # Redis dependency
    try:
        if redis_client is None:
            dependencies.append(
                {"name": "redis", "status": "degraded", "error": "Redis client not configured"}
            )
            overall_status = "degraded"
        else:
            redis_client.ping()
            dependencies.append({"name": "redis", "status": "healthy", "error": None})
    except Exception as e:
        logger.error("health_check_redis_failed", error_code="REDIS_HEALTH_ERROR", error=str(e))
        dependencies.append({"name": "redis", "status": "degraded", "error": "Redis connection failed"})
        overall_status = "degraded"

    return legacy_health_checkResult.model_validate({
        "status": overall_status,
        "note": "Legacy endpoint; use /api/v1/ingestion/health for full schema response",
        "dependencies": dependencies,
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
