"""Target API config serialization helpers."""

from __future__ import annotations

from typing import Any

from ..shared.models import ScrapingTarget
from .schemas.target_schemas import (
    AuthenticationInput,
    BrowserConfigInput,
    ComplianceInput,
    CreateTargetRequest,
    ExtractionConfigInput,
    ProxyConfigInput,
    RateLimitInput,
    ScheduleInput,
    UpdateTargetRequest,
)


def build_extraction_config(
    config: ExtractionConfigInput,
    *,
    crawl_path: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "method": config.method.value,
        "llm_provider": config.llm_provider.value if config.llm_provider else None,
        "extraction_schema": config.extraction_schema,
        "visual_hints": config.visual_hints,
        "max_depth": config.max_depth,
        "follow_links": config.follow_links,
        "link_selectors": config.link_selectors,
    }
    if crawl_path is not None:
        payload["crawl_path"] = crawl_path
    return payload


def build_browser_config(config: BrowserConfigInput) -> dict[str, Any]:
    return {
        "engine": config.engine.value,
        "headless": config.headless,
        "viewport": {
            "width": config.viewport_width,
            "height": config.viewport_height,
        },
        "user_agent": config.user_agent,
        "javascript_enabled": config.javascript_enabled,
        "wait_for_selector": config.wait_for_selector,
        "wait_timeout": config.wait_timeout,
        "stealth_mode": config.stealth_mode,
    }


def build_schedule_config(config: ScheduleInput | None) -> dict[str, Any] | None:
    if config is None:
        return None
    return {
        "enabled": config.enabled,
        "cron_expression": config.cron_expression,
        "timezone": config.timezone,
        "max_concurrent_jobs": config.max_concurrent_jobs,
    }


def build_rate_limit_config(config: RateLimitInput) -> dict[str, Any]:
    return {
        "requests_per_second": config.requests_per_second,
        "requests_per_minute": config.requests_per_minute,
        "requests_per_hour": config.requests_per_hour,
        "burst_limit": config.burst_limit,
        "retry_attempts": config.retry_attempts,
        "retry_backoff": config.retry_backoff.value,
        "retry_delay_ms": config.retry_delay_ms,
    }


def build_compliance_config(config: ComplianceInput) -> dict[str, Any]:
    return {
        "respect_robots_txt": config.respect_robots_txt,
        "strict_robots_compliance": config.strict_robots_compliance,
        "user_agent_string": config.user_agent_string,
        "crawl_delay_seconds": config.crawl_delay_seconds,
        "domain_allowlist": config.domain_allowlist,
        "domain_blocklist": config.domain_blocklist,
        "pii_redaction_enabled": config.pii_redaction_enabled,
        "sensitive_field_patterns": config.sensitive_field_patterns,
    }


def build_proxy_config(config: ProxyConfigInput) -> dict[str, Any]:
    return {
        "enabled": config.enabled,
        "rotation_strategy": config.rotation_strategy.value,
        "proxy_pool_id": str(config.proxy_pool_id) if config.proxy_pool_id else None,
        "sticky_sessions": config.sticky_sessions,
        "session_duration_minutes": config.session_duration_minutes,
    }


def build_authentication_config(
    config: AuthenticationInput | None,
) -> dict[str, Any] | None:
    if config is None:
        return None
    return {
        "type": config.type.value,
        "credentials_ref": config.credentials_ref,
    }


def build_create_target_configs(request: CreateTargetRequest) -> dict[str, Any]:
    return {
        "extraction_config": build_extraction_config(
            request.extraction_config,
            crawl_path=request.crawl_path.value,
        ),
        "browser_config": build_browser_config(request.browser_config),
        "schedule": build_schedule_config(request.schedule),
        "rate_limit": build_rate_limit_config(request.rate_limit),
        "compliance": build_compliance_config(request.compliance),
        "proxy_config": build_proxy_config(request.proxy_config),
        "authentication": build_authentication_config(request.authentication),
    }


def apply_target_config_updates(
    target: ScrapingTarget,
    request: UpdateTargetRequest,
) -> None:
    if request.crawl_path is not None:
        if target.extraction_config is None:
            target.extraction_config = {}
        target.extraction_config["crawl_path"] = request.crawl_path.value

    if request.extraction_config:
        target.extraction_config = build_extraction_config(request.extraction_config)

    if request.browser_config:
        target.browser_config = build_browser_config(request.browser_config)

    if request.rate_limit:
        target.rate_limit = build_rate_limit_config(request.rate_limit)

    if request.compliance:
        target.compliance = build_compliance_config(request.compliance)

    if request.proxy_config:
        target.proxy_config = build_proxy_config(request.proxy_config)

    if request.schedule is not None:
        target.schedule = build_schedule_config(request.schedule)

    if request.authentication is not None:
        target.authentication = build_authentication_config(request.authentication)

