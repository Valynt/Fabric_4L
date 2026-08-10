"""Pydantic schemas for target-related API operations."""
from datetime import datetime
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
    extraction_schema: dict[str, Any] | None = None
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
    extraction_config: dict[str, Any]
    browser_config: dict[str, Any]
    schedule: dict[str, Any] | None
    rate_limit: dict[str, Any]
    compliance: dict[str, Any]
    proxy_config: dict[str, Any]
    authentication: dict[str, Any] | None
    created_by: UUID
    last_error_at: datetime | None = None


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
    errors: list[ValidationErrorDetail]
    warnings: list[ValidationWarning]
    robots_txt_check: dict[str, Any] | None = None
    schema_validation: dict[str, Any] | None = None
    browser_test: dict[str, Any] | None = None


# Cloud metadata endpoints that must never be targeted by callbacks.
_SSRF_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "169.254.169.254",  # AWS / Azure / GCP instance metadata
        "169.254.170.2",  # AWS ECS Task metadata endpoint
        "100.100.100.200",  # Alibaba Cloud instance metadata
        "192.0.0.254",  # Oracle Cloud instance metadata
        "fd00:ec2::254",  # AWS EC2 IPv6 instance metadata
        "metadata.google.internal",  # GCP metadata domain
        "metadata.internal",  # GCP/internal alias
    }
)


def _validate_callback_url_no_ssrf(value: str | None) -> str | None:
    """Block SSRF-prone callback URLs (private IPs, localhost, non-HTTPS)."""
    if value is None:
        return None
    import ipaddress
    from urllib.parse import urlparse

    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ValueError("callback_url must use HTTPS scheme")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("callback_url must have a valid hostname")
    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):  # nosec B104
        raise ValueError("callback_url must not point to localhost")
    if hostname_lower in _SSRF_BLOCKED_HOSTNAMES:
        raise ValueError("callback_url must not point to cloud metadata endpoints")
    if hostname_lower.endswith(".metadata"):
        raise ValueError("callback_url must not point to cloud metadata endpoints")
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_unspecified
        ):
            raise ValueError(
                "callback_url must not point to private or reserved IP addresses"
            )
    return value


class ExecuteTargetRequest(BaseModel):
    """Request to execute a target."""

    priority: int = Field(default=5, ge=1, le=10)
    override_config: dict[str, Any] | None = None
    callback_url: str | None = None
    webhook_events: list[str] | None = None
    idempotency_key: str | None = Field(default=None, max_length=255)

    @field_validator("callback_url")
    @classmethod
    def _check_callback_url(cls, v: str | None) -> str | None:
        return _validate_callback_url_no_ssrf(v)


class ExecuteTargetResponse(BaseModel):
    """Response from target execution."""

    job_id: UUID
    status: str
    estimated_start_time: datetime | None = None
    queue_position: int | None = None
    queue_position_metadata: dict[str, Any] | None = None
