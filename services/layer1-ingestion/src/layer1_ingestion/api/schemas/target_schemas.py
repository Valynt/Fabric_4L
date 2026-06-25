"""Pydantic schemas for target-related API operations."""
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator

from ...shared.models import (
    AuthenticationType,
    BrowserEngine,
    CrawlPath,
    ExtractionMethod,
    LLMProvider,
    ProxyRotationStrategy,
    RetryBackoff,
    ScrapingTarget,
    TargetStatus,
    TargetType,
)


def _validate_cron_expression(expr: str) -> str:
    """Parse and validate a 5-field cron expression using croniter.

    Raises ValueError with a human-readable message on any of:
    - Non-standard macros (@reboot, @yearly, etc.) — not schedulable by Celery Beat
    - Wrong field count (must be exactly 5: minute hour dom month dow)
    - Out-of-range or syntactically invalid field values
    """
    from croniter import CroniterBadCronError, croniter

    expr = expr.strip()

    # Reject @-macros — Celery Beat requires explicit 5-field expressions
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


class ExtractionConfigInput(BaseModel):
    """Extraction configuration for a target."""

    method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    llm_provider: LLMProvider | None = None
    extraction_schema: dict[str, any] | None = None
    visual_hints: bool = False
    max_depth: int | None = None
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
    crawl_path: CrawlPath = CrawlPath.BROWSER
    extraction_config: ExtractionConfigInput = Field(
        default_factory=lambda: ExtractionConfigInput()
    )
    browser_config: BrowserConfigInput = Field(
        default_factory=lambda: BrowserConfigInput()
    )
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
    crawl_path: CrawlPath | None = None
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
    source_category: str | None = None
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
    crawl_path: str
    extraction_config: dict[str, any]
    browser_config: dict[str, any]
    schedule: dict[str, any] | None
    rate_limit: dict[str, any]
    compliance: dict[str, any]
    proxy_config: dict[str, any]
    authentication: dict[str, any] | None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    last_error_at: datetime | None = None


class TargetListResponse(BaseModel):
    """List of scraping targets."""

    data: list[ScrapingTargetSummary]
    pagination: dict[str, any]


class ValidateTargetRequest(BaseModel):
    """Request to validate a target configuration."""

    test_url: str | None = None
    test_browser_connection: bool = False
    test_extraction: bool = False
    test_compliance: bool = False


class ValidationErrorDetail(BaseModel):
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
    errors: list[ValidationErrorDetail] = []
    warnings: list[ValidationWarning] = []
    test_results: dict[str, any] = {}


def _validate_callback_url_no_ssrf(value: str) -> str:
    """Validate callback URL to prevent SSRF attacks."""
    from urllib.parse import urlparse

    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Callback URL must use HTTP or HTTPS scheme")
    
    # Block private/internal IPs
    hostname = parsed.hostname or ""
    if hostname.startswith(("127.", "10.", "192.168.", "172.")):
        raise ValueError("Callback URL cannot point to private IP addresses")
    
    if hostname == "localhost":
        raise ValueError("Callback URL cannot use localhost")
    
    return value


class ExecuteTargetRequest(BaseModel):
    """Request to execute a target."""

    priority: int = Field(default=5, ge=1, le=10)
    callback_url: str | None = None
    override_config: dict[str, any] | None = None

    @field_validator("callback_url")
    @classmethod
    def validate_callback(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_callback_url_no_ssrf(v)
        return v


class ExecuteTargetResponse(BaseModel):
    """Response from target execution."""

    job_id: UUID
    status: str
    estimated_completion_time: datetime | None = None
