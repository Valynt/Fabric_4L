"""
Shared fixtures for services/api tests.

Provides:
  - mint_token(tenant_id, subject) — create a signed JWT for test requests
  - auth_headers(tenant_id, subject) — Authorization header dict
  - TENANT_ALPHA / TENANT_BETA — stable tenant IDs for isolation tests
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets

import pytest
import jwt

import app.services.agent_orchestrator as _orch_mod
from app.core import database as _db_mod
from app.core.config import get_settings

# Use the same default secret the app uses in test/dev environments
TEST_SECRET = "fabric-4l-dev-secret-key-change-in-production"
TEST_ALGORITHM = "HS256"
TEST_ISSUER = "value-fabric-internal"
TEST_AUDIENCE = "value-fabric-services"

TENANT_ALPHA = "11111111-1111-4111-8111-111111111111"
TENANT_BETA = "22222222-2222-4222-8222-222222222222"

# Default to in-memory persistence with demo seed data and mock LLM for all
# unit/integration tests. Tests that need production-like behaviour must
# override these env vars explicitly.
import os as _os
_os.environ.setdefault("MOCK_PERSISTENCE", "true")
_os.environ.setdefault("SEED_DEMO_DATA", "true")
_os.environ.setdefault("LLM_PROVIDER", "mock")


def _clear_singletons() -> None:
    """Reset all lazy singletons and the settings cache to a blank state."""
    _db_mod._LazyDB._instance = None
    _orch_mod._LazyOrchestrator._instance = None
    _orch_mod._orchestrator = None
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_lazy_db() -> None:
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
    }
    return jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALGORITHM)


def auth_headers(
    tenant_id: str = TENANT_ALPHA,
    subject: str = "test-user-001",
) -> dict[str, str]:
    """Return headers dict with a valid Bearer token for the given tenant."""
    token = mint_token(tenant_id=tenant_id, subject=subject)
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
