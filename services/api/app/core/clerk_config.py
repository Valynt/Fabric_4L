"""Clerk-specific authentication configuration for the API gateway.

This module is intentionally separate from ``app.core.config`` so that
Clerk webhook/JWT settings can be loaded, cached, and reset independently
without affecting the rest of the application.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class ClerkSettings:
    """Clerk configuration required by webhook and JWT flows."""

    webhook_secret: str | None = None
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    authorized_parties: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class AuthSettings:
    """Authentication settings exposed by ``get_auth_settings``."""

    auth_provider: str = "legacy"
    clerk: ClerkSettings | None = None


def _parse_env_list(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(part.strip() for part in value.split(",") if part.strip())


@lru_cache(maxsize=1)
def get_auth_settings() -> AuthSettings:
    """Return cached Clerk/auth settings derived from environment variables."""
    webhook_secret = os.getenv("CLERK_WEBHOOK_SECRET") or None
    jwt_issuer = os.getenv("CLERK_ISSUER") or None
    jwt_audience = os.getenv("CLERK_JWT_AUDIENCE") or None
    authorized_parties = _parse_env_list(os.getenv("CLERK_AUTHORIZED_PARTIES"))
    auth_provider = (os.getenv("AUTH_PROVIDER") or "legacy").lower()

    # Only expose ClerkSettings when at least the webhook secret is present.
    # This mirrors the legacy behaviour: the webhook endpoint is silent until
    # explicitly configured.
    if webhook_secret:
        clerk = ClerkSettings(
            webhook_secret=webhook_secret,
            jwt_issuer=jwt_issuer,
            jwt_audience=jwt_audience,
            authorized_parties=authorized_parties,
        )
    else:
        clerk = None

    return AuthSettings(auth_provider=auth_provider, clerk=clerk)


def reset_auth_settings_cache() -> None:
    """Clear the cached auth settings; tests use this to re-read env vars."""
    get_auth_settings.cache_clear()
