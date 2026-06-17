"""
Shared fixtures for services/api tests.

Provides:
  - mint_token(tenant_id, subject) — create a signed JWT for test requests
  - auth_headers(tenant_id, subject) — Authorization header dict
  - TENANT_ALPHA / TENANT_BETA — stable tenant IDs for isolation tests
"""

from __future__ import annotations

import os as _os
import secrets
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest

import app.services.agent_orchestrator as _orch_mod
from app.core import database as _db_mod
from app.core.config import get_settings

# Use the same default secret the app uses in test/dev environments
# Shortened to stay under bcrypt's 72-byte limit when combined with JWT payload
# Must be at least 32 bytes for HMAC-SHA256 security
TEST_SECRET = "fabric-dev-secret-key-32bytes-ok"
TEST_ALGORITHM = "HS256"
TEST_ISSUER = "value-fabric-internal"
TEST_AUDIENCE = "value-fabric-services"

TENANT_ALPHA = "11111111-1111-4111-8111-111111111111"
TENANT_BETA = "22222222-2222-4222-8222-222222222222"

# Default to in-memory persistence with demo seed data and Layer 4 delegated LLM for all
# unit/integration tests. Tests that need production-like behaviour must
# override these env vars explicitly.
_os.environ.setdefault("MOCK_PERSISTENCE", "true")
_os.environ.setdefault(
    "SEED_DEMO_DATA", "false"
)  # Disable seeding to avoid tenant context issues
_os.environ.setdefault("LLM_PROVIDER", "layer4")
_os.environ.setdefault("SECRET_KEY", TEST_SECRET)
_os.environ.setdefault("JWT_SECRET", TEST_SECRET)
_os.environ.setdefault("JWT_ALGORITHM", TEST_ALGORITHM)
_os.environ.setdefault("JWT_ISSUER", TEST_ISSUER)
_os.environ.setdefault("JWT_AUDIENCE", TEST_AUDIENCE)
# Disable bcrypt in tests to avoid 72-byte password limit issues in passlib
_os.environ.setdefault("USE_BCRYPT", "false")


def _clear_singletons() -> None:
    """Reset all lazy singletons and the settings cache to a blank state."""
    _db_mod._LazyDB._instance = None
    _orch_mod._LazyOrchestrator._instance = None
    _orch_mod._orchestrator = None
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_lazy_db() -> Iterator[None]:
    """Reset singletons and settings cache before and after each test.

    Clears _LazyDB, _LazyOrchestrator, the module-level _orchestrator global,
    and the get_settings LRU cache so tests that mutate env vars or persistence
    config cannot bleed state into subsequent tests.
    """
    _clear_singletons()
    yield
    _clear_singletons()


def mint_token(
    tenant_id: str = TENANT_ALPHA,
    subject: str = "test-user-001",
    expires_delta: timedelta = timedelta(hours=1),
    extra_claims: dict[str, object] | None = None,
) -> str:
    """Return a signed JWT accepted by the test app."""
    expire = datetime.now(UTC) + expires_delta
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "iss": TEST_ISSUER,
        "aud": TEST_AUDIENCE,
        "iat": int(datetime.now(UTC).timestamp()),
        "nbf": int(datetime.now(UTC).timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_urlsafe(16),
        "account_ids": ["*"],
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALGORITHM)


def auth_headers(
    tenant_id: str = TENANT_ALPHA,
    subject: str = "test-user-001",
    extra_claims: dict[str, object] | None = None,
) -> dict[str, str]:
    """Return headers dict with a valid Bearer token for the given tenant."""
    token = mint_token(tenant_id=tenant_id, subject=subject, extra_claims=extra_claims)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


@pytest.fixture
def alpha_headers() -> dict[str, str]:
    return auth_headers(TENANT_ALPHA)


@pytest.fixture
def beta_headers() -> dict[str, str]:
    return auth_headers(TENANT_BETA)
