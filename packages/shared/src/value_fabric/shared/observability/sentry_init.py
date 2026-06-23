# ---------------------------------------------------------------------------
# PATCH-009: Sentry Backend Integration (P1)
# Production-grade error tracking with PII scrubbing for enterprise SaaS.
# ---------------------------------------------------------------------------

"""Centralized Sentry initialization for all Value Fabric services.

Usage::

    from value_fabric.shared.observability.sentry_init import init_sentry
    init_sentry()

Environment variables:
    SENTRY_DSN          -- Sentry project DSN (required for activation)
    ENVIRONMENT         -- deployment stage (default: "development")
    SENTRY_SAMPLE_RATE  -- event sampling rate 0.0-1.0
                           (default: 0.1 for prod, 1.0 for dev)
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Sensitive keys that must never leave the perimeter
_PII_KEYS: frozenset[str] = frozenset({
    "tenant_id",
    "email",
    "api_key",
    "jwt",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "session",
    "x-api-key",
    "x-tenant-id",
})


def _scrub_event(event: dict[str, Any], hint: Any) -> dict[str, Any] | None:
    """Recursively remove PII from a Sentry event before transmission."""
    if not isinstance(event, dict):
        return event

    scrubbed: dict[str, Any] = {}
    for key, value in event.items():
        if key.lower() in _PII_KEYS:
            scrubbed[key] = "[REDACTED]"
        elif isinstance(value, dict):
            scrubbed[key] = _scrub_event(value, hint)
        elif isinstance(value, list):
            scrubbed[key] = [
                _scrub_event(item, hint) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            scrubbed[key] = value
    return scrubbed


def init_sentry(
    *,
    service_name: str | None = None,
    release: str | None = None,
) -> bool:
    """Initialize Sentry SDK if SENTRY_DSN is configured. No-op otherwise."""
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        logger.debug("SENTRY_DSN not set; Sentry is disabled.")
        return False

    environment = os.environ.get("ENVIRONMENT", "development").lower()
    sample_rate_env = os.environ.get("SENTRY_SAMPLE_RATE", "")
    if sample_rate_env:
        sample_rate = float(sample_rate_env)
    else:
        sample_rate = 0.1 if environment == "production" else 1.0

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            release=release,
            environment=environment,
            sample_rate=sample_rate,
            traces_sample_rate=sample_rate,
            profiles_sample_rate=min(sample_rate, 0.1),
            before_send=_scrub_event,
            before_send_transaction=_scrub_event,
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            send_default_pii=False,
            max_breadcrumbs=50,
            attach_stacktrace=True,
            include_source_context=True,
            in_app_include=["value_fabric", "app"],
        )
        if service_name:
            sentry_sdk.set_tag("service", service_name)
        logger.info(
            "Sentry initialized: env=%s sample_rate=%s",
            environment,
            sample_rate,
        )
        return True
    except ImportError:
        logger.warning(
            "sentry-sdk is not installed; install with: pip install sentry-sdk[fastapi]"
        )
        return False
    except Exception as exc:
        logger.error("Failed to initialize Sentry: %s", exc)
        return False
