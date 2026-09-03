"""pytest configuration and shared fixtures for Layer 7 Billing tests.

Uses an in-memory SQLite database (via aiosqlite) for fast, isolated tests.
The DATABASE_URL is overridden before any imports touch the engine.

Fixture hierarchy:
  engine (function-scoped) →  fresh in-memory DB per test
  db     (function-scoped) →  session with a nested transaction rolled back after each test

This conftest.py is isolated from the root conftest.py to avoid mandatory dependency
checks for layer1/layer3/layer4 packages that are not needed for layer7-billing tests.
"""

import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

# Add service src to path
SERVICE_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = SERVICE_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Add shared package to path (needed for value_fabric.shared imports)
SHARED_SRC = REPO_ROOT / "packages" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.middleware import GovernanceMiddleware

# Override DATABASE_URL before any application code imports the engine
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET"] = "test-jwt-secret-must-be-32-characters-long"
os.environ["JWT_ISSUER"] = "value-fabric-internal"
os.environ["JWT_AUDIENCE"] = "value-fabric-services"
os.environ["TESTING"] = "true"
os.environ["ALLOW_LEGACY_TEST_TENANT_IDS"] = "true"


@pytest.fixture(scope="function")
async def engine():
    """Create a fresh in-memory database engine for each test."""
    from layer7_billing.models import Base

    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session with transaction rollback for isolation.

    Note: SQLite does not support PostgreSQL's set_config() for tenant context.
    Tenant isolation in SQLite tests is handled at the application layer,
    not the database layer. For production-like tenant isolation tests,
    use PostgreSQL with RLS policies.
    """
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

        # Rollback to isolate test changes
        await session.rollback()


def billing_context(tenant_id: str, roles: list[str] | None = None) -> RequestContext:
    """Return a RequestContext for testing with specified tenant and roles."""
    return RequestContext(
        tenant_id=tenant_id,
        user_id="test-user-001",
        org_id="test-org-001",
        roles=roles or ["billing:read", "billing:write"],
        permissions=[],
        auth_source="mock",
        tenant_role="admin",
        isolation_tier="shared",
        request_id="test",
    )


def mint_token(tenant_id: str = "tenant-a", roles: list[str] | None = None) -> str:
    """Return a signed JWT accepted by the test app's GovernanceMiddleware."""
    import time
    import jwt as pyjwt
    now = int(time.time())
    payload = {
        "tenant_id": tenant_id,
        "sub": "test-user-001",
        "roles": roles if roles is not None else ["billing:read", "billing:write"],
        "iss": os.environ["JWT_ISSUER"],
        "aud": os.environ["JWT_AUDIENCE"],
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def auth_headers(tenant_id: str = "tenant-a", roles: list[str] | None = None) -> dict[str, str]:
    """Return headers dict with a valid Bearer token for the given tenant and roles."""
    token = mint_token(tenant_id=tenant_id, roles=roles)
    return {"Authorization": f"Bearer {token}"}




@pytest.fixture(autouse=True)
def active_tenant_kill_switch(monkeypatch):
    """Keep lightweight Layer 7 tests focused on auth/RBAC outcomes, not Redis availability."""
    from value_fabric.shared.tenant_kill_switch import (
        TenantKillSwitch,
        TenantSuspensionStatus,
    )

    async def active_status(self, tenant_id):
        return TenantSuspensionStatus.ACTIVE

    monkeypatch.setattr(TenantKillSwitch, "check_status", active_status)

@pytest.fixture(autouse=True)
def bypass_redis_rate_limiter(monkeypatch):
    """Disable Redis-backed rate limiting for tests; CI tenant isolation gate has no Redis."""
    from value_fabric.shared.identity.rate_limiter import RedisRateLimiter, RateLimitResult

    async def _allow(*args, **kwargs):
        return RateLimitResult(
            allowed=True,
            remaining=100,
            reset_at=0.0,
            retry_after=None,
        )

    monkeypatch.setattr(RedisRateLimiter, "check", _allow)


@pytest.fixture(autouse=True)
def override_db_dependency():
    """Override get_db_from_context to prevent real PostgreSQL connections in all tests."""
    from unittest.mock import AsyncMock
    from layer7_billing.api.main import app
    from layer7_billing.database import get_db_from_context

    mock_session = AsyncMock()

    async def mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db_from_context] = mock_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_repo(monkeypatch):
    """Mock repository functions to enable arg assertions."""
    from unittest.mock import AsyncMock
    mock = AsyncMock()
    mock.upsert_plan = AsyncMock(return_value={"plan_id": "p1", "tenant_id": "t1", "name": "P1", "entitlements": []})
    mock.get_plan_entitlements = AsyncMock(return_value=["feature1"])
    mock.insert_usage_event = AsyncMock(return_value=True)
    mock.increment_aggregate = AsyncMock(return_value=None)
    mock.get_usage_aggregates = AsyncMock(return_value={"api_calls": 100.0})
    mock.list_invoices = AsyncMock(return_value=[])
    mock.get_payment_state = AsyncMock(return_value={"state_key": "current", "state": "paid", "payload": {}})
    monkeypatch.setattr("layer7_billing.api.main.repository", mock)
    return mock


@pytest.fixture
def mock_governance_middleware(monkeypatch):
    """Mock GovernanceMiddleware to inject a fallback context for unit tests."""
    async def mock_dispatch(self, request, call_next):
        request.state.governance_context = billing_context("test-tenant")
        return await call_next(request)
    monkeypatch.setattr(GovernanceMiddleware, "dispatch", mock_dispatch)


@pytest.fixture
async def isolated_client():
    """Async HTTP client for the Layer 7 billing app."""
    from layer7_billing.api.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
