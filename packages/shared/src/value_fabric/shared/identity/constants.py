"""Constants, allowlists, and path helpers for the governance middleware."""

from __future__ import annotations

import os
import re

# Header names for service-to-service authentication (F-1 P0 fix)
TENANT_ID_HEADER = "X-Tenant-ID"
SERVICE_AUTH_HEADER = "X-Service-Auth"
MIN_SERVICE_SECRET_LENGTH = 32  # Minimum entropy for shared secrets

SESSION_COOKIE_NAME = "vf_session"

ERR_AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
ERR_AUTH_SERVICE_UNAVAILABLE = "AUTH_SERVICE_UNAVAILABLE"
ERR_AUTH_CONTEXT_INVALID = "AUTH_CONTEXT_INVALID"

_LEGACY_TEST_TENANT_ID_RE = re.compile(r"^tenant-[a-z0-9]+(?:-[a-z0-9]+)*$")

# Paths that bypass the gateway identity middleware because they perform their
# own authentication (e.g., health probes, external IdP bootstrap routes).
EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST: frozenset[str] = frozenset(
    {
        "/health",
        "/health/detailed",
        "/health/live",
        "/live",
        "/ready",
        "/readiness",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/v1/billing/webhook",
        "/v1/repo-audit/webhook/github",
        "/internal/webhooks/clerk",
        "/v1/auth/health",
        "/v1/auth/clerk/health",
        "/v1/auth/login",
        "/v1/auth/signup",
        "/v1/auth/accept-invite",
        "/v1/auth/clerk/tenant",
        "/",
        "/robots.txt",
    }
)

DEFAULT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
_RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_WINDOW_SECONDS = _RATE_LIMIT_WINDOW_SECONDS


def _is_external_auth_bootstrap_path(path: str) -> bool:
    """Return True if the path bypasses the gateway middleware but has its own auth."""
    return (
        path in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        or path.startswith("/docs")
        or path.startswith("/redoc")
        or path.startswith("/internal/webhooks/")
    )
