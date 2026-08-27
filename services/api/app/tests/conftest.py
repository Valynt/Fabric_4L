"""
Shared fixtures for services/api tests.

Provides:
  - mint_token(tenant_id, subject) — create a signed JWT for test requests
  - auth_headers(tenant_id, subject) — Authorization header dict
  - TENANT_ALPHA / TENANT_BETA — stable tenant IDs for isolation tests
"""

# Test configuration must precede application imports; see the setup below.
# ruff: noqa: E402

from __future__ import annotations

import os as _os

# ---------------------------------------------------------------------------
# RB-2 FIX: Override environment detection keys unconditionally.
#
# These assignments MUST appear before any app import because the app modules
# call get_settings() at module-import time (e.g. accounts.py line 37 calls
# get_redis_client() which calls get_settings()). If APP_ENV=production is
# inherited from the CI shell and ENVIRONMENT is not set, _detect_environment()
# returns "production" and validate_production_safety() raises RuntimeError
# before any test body executes.
#
# Using direct assignment (not setdefault) ensures the override wins regardless
# of what the CI shell has inherited. All three keys are set for belt-and-
# suspenders coverage of the full detection loop in config._detect_environment.
# ---------------------------------------------------------------------------
_os.environ["ENVIRONMENT"] = "development"
_os.environ["APP_ENV"] = "development"
_os.environ["ENV"] = "development"
_os.environ["DEBUG"] = "false"

# A fixed test-only key keeps import-time settings initialization deterministic.
# It must be configured before importing app modules now that Settings fails
# closed when SECRET_KEY is absent.
TEST_SECRET = "fabric-dev-secret-key-32bytes-ok"
_os.environ["SECRET_KEY"] = TEST_SECRET

import secrets
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest

import app.services.agent_orchestrator as _orch_mod
from app.core import database as _db_mod
from app.core.config import get_settings
from app.routers import accounts as _accounts_mod

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
_os.environ["JWT_SECRET"] = TEST_SECRET
_os.environ.setdefault("JWT_ALGORITHM", TEST_ALGORITHM)
_os.environ.setdefault("JWT_ISSUER", TEST_ISSUER)
_os.environ.setdefault("JWT_AUDIENCE", TEST_AUDIENCE)
# Disable bcrypt in tests to avoid 72-byte password limit issues in passlib
_os.environ.setdefault("USE_BCRYPT", "false")
# Allow unauthenticated access to /metrics in development test runs.
# This flag is validated and rejected in production-like environments.
# NOTE: test_tenant_isolation.py overrides this to "false" to ensure real
# authorization enforcement is tested (not the dev bypass path).
_os.environ.setdefault("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")


def _clear_singletons() -> None:
    """Reset all lazy singletons and the settings cache to a blank state."""
    _db_mod._LazyDB._instance = None
    _db_mod._pg_engine = None
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


@pytest.fixture(autouse=True)
def _reset_rate_limiter_loop_binding() -> None:
    """Drop the async Redis client bound to a prior TestClient event loop.

    The ``TenantRateLimiter`` singleton is created at application import time.
    Its ``redis.asyncio`` client is bound to the event loop of the first
    ``TestClient`` that exercises it. When subsequent tests open their own
    ``TestClient`` contexts, the stale client throws ``Event loop is closed``.
    Resetting the client before each test forces lazy reconnection on the
    current test's loop.
    """
    from app.main import app as _app

    def _drop() -> None:
        limiter = getattr(getattr(_app, "state", None), "rate_limiter", None)
        if limiter is None:
            return
        try:
            old_client = getattr(limiter, "redis", None)
            limiter.redis = None
            if old_client is not None:
                # Closing a client bound to a closed loop can raise; swallow.
                try:
                    import asyncio

                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        asyncio.create_task(old_client.close())
                except RuntimeError:
                    pass
        except Exception:
            pass

    _drop()
    yield
    _drop()


@pytest.fixture(autouse=True)
def _reset_idempotency_store() -> None:
    """Clear in-memory idempotency records so tests do not replay across runs."""
    from app.main import app as _app

    for service in [
        getattr(getattr(_app, "state", None), "idempotency_service", None),
        getattr(_accounts_mod, "_idempotency_service", None),
    ]:
        if service is None:
            continue
        store = getattr(service, "_store", None)
        if store is not None:
            records = getattr(store, "_records", None)
            if records is not None:
                records.clear()
            fallback = getattr(store, "_fallback", None)
            if fallback is not None:
                fallback_records = getattr(fallback, "_records", None)
                if fallback_records is not None:
                    fallback_records.clear()
    yield


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
