"""
pytest configuration and shared fixtures for Layer 5 Ground Truth tests.

Uses an in-memory SQLite database (via aiosqlite) for fast, isolated tests.
The DATABASE_URL is overridden before any imports touch the engine.

Fixture hierarchy:
  engine (function-scoped) →  fresh in-memory DB per test; prevents fixture-level
                               commits from leaking across tests via savepoint escape
  db     (function-scoped) →  session with a nested transaction rolled back after each test
  client (function-scoped) →  httpx.AsyncClient wrapping the FastAPI app
"""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def pytest_collection_modifyitems(config, items):
    """Skip tests marked requires_postgres when no PostgreSQL is available."""
    postgres_url = os.getenv("POSTGRES_TEST_URL") or os.getenv("DATABASE_URL", "")
    run_postgres_tests = os.getenv("RUN_POSTGRES_TESTS", "").strip().lower() == "true"
    if not run_postgres_tests or not postgres_url.lower().startswith("postgres"):
        skip_pg = pytest.mark.skip(reason="requires_postgres: no live PostgreSQL instance")
        for item in items:
            if item.get_closest_marker("requires_postgres"):
                item.add_marker(skip_pg)

# Override DATABASE_URL before any application code imports the engine
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["DATABASE_URL_SYNC"] = "sqlite:///:memory:"
os.environ["LAYER3_SYNC_ENABLED"] = "false"
os.environ["AUTO_ADVANCE_TO_VALIDATED"] = "true"
os.environ["MIN_CONFIDENCE_FOR_VALIDATED"] = "0.5"
os.environ["MIN_SOURCES_FOR_VALIDATED"] = "2"
os.environ["JWT_FALLBACK_TO_QUERY_PARAM"] = "true"
os.environ["SERVICE_AUTH_SECRET"] = "test-service-auth-secret-that-is-32-chars-long-ok"
os.environ["ALLOW_INSECURE_DEV_AUTH_BYPASS"] = "true"
os.environ["JWT_SECRET"] = "test-jwt-secret-that-is-at-least-32-chars"

from layer5_ground_truth import database as db_module  # noqa: E402
from layer5_ground_truth.api.main import create_app  # noqa: E402
from layer5_ground_truth.models import Base  # noqa: E402
# ---------------------------------------------------------------------------
# Shared test organization ID
# ---------------------------------------------------------------------------

TEST_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# Organization ID fixture for model registry tests
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant_id() -> str:
    """Return test organization ID as string for model registry tests."""
    return str(TEST_ORG_ID)


# ---------------------------------------------------------------------------
# Engine — created once per session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def engine():
    """Create a function-scoped async engine backed by SQLite in-memory.

    Each test gets its own fresh database so that commits made by fixtures
    (e.g. sample_model_version calling db.commit()) cannot leak data into
    subsequent tests.  The session-scoped approach was unsafe because
    begin_nested() + rollback only protects against explicit test writes;
    fixture-level commits escape the savepoint and persist for the rest of
    the session.
    """
    from sqlalchemy import event as sa_event

    _engine = create_async_engine(TEST_DB_URL, echo=False, future=True)

    # Enable SQLite foreign key enforcement so ON DELETE CASCADE works in tests.
    @sa_event.listens_for(_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Patch the module-level engine so the app uses our test engine.
    db_module._engine = _engine
    db_module._session_factory = async_sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    # Create all tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()


# ---------------------------------------------------------------------------
# Database session — rolled back after each test
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session that is rolled back after each test.

    Uses a nested transaction (SAVEPOINT) so the outer transaction can
    be rolled back cleanly regardless of what the test does.

    Tenant context is pre-set to TEST_ORG_ID so the flush enforcement
    guard does not reject writes made directly through the test session.
    """
    factory = db_module.get_session_factory()
    async with factory() as session:
        # Establish tenant context so _enforce_tenant_context_before_flush passes.
        db_module._mark_session_tenant_context(session, str(TEST_ORG_ID))
        # Begin a nested transaction (SAVEPOINT)
        await session.begin_nested()
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an httpx.AsyncClient that overrides the get_db dependency
    to use the test session.
    """
    from layer5_ground_truth.api.auth import TokenClaims, get_current_user
    from layer5_ground_truth.database import get_db, get_db_from_context

    app = create_app()

    async def override_get_db():
        yield db

    async def override_get_db_from_context():
        yield db

    def override_get_current_user():
        """Return test user with tenant_id for auth bypass."""
        return TokenClaims(
            tenant_id=TEST_ORG_ID,
            user_id="test-user",
            roles=["admin"],
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_from_context] = override_get_db_from_context
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "X-Tenant-ID": str(TEST_ORG_ID),
            "X-Service-Auth": os.environ["SERVICE_AUTH_SECRET"],
        },
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Async client alias and auth headers for model registry tests
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_client(client) -> AsyncGenerator[AsyncClient, None]:
    """Alias for client fixture - model registry tests expect async_client."""
    yield client


@pytest.fixture
def auth_headers() -> dict:
    """Return request headers for API tests.

    Auth is handled via dependency overrides in the test client fixture;
    no Authorization header is needed (and an invalid one would trigger
    GovernanceMiddleware JWT validation failures).
    """
    return {
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Convenience factories
# ---------------------------------------------------------------------------

def make_truth_payload(**overrides) -> dict:
    """Return a minimal valid TruthObjectCreate payload."""
    base = {
        "claim": "Manual invoice reconciliation costs 20 hours per month",
        "claim_type": "efficiency_gain",
        "confidence": 0.85,
        "value": {"amount": 20, "unit": "hours", "period": "month"},
        "applies_to": {"opportunity_id": "opp-test-001"},
    }
    base.update(overrides)
    return base


def make_source_payload(**overrides) -> dict:
    """Return a minimal valid TruthSourceCreate payload."""
    base = {
        "source_type": "call_transcript",
        "source_url": "https://example.com/call/123",
        "source_title": "Discovery call with CFO",
        "excerpt": "We spend about 20 hours a month on invoice reconciliation",
        "confidence_contribution": 0.8,
    }
    base.update(overrides)
    return base


@pytest_asyncio.fixture
async def tenant_aware_client(db) -> AsyncGenerator[AsyncClient, None]:
    """Client fixture that allows per-request tenant switching via X-Test-Tenant."""
    from fastapi import Header
    from layer5_ground_truth.api.auth import TokenClaims, get_current_user
    from layer5_ground_truth.database import get_db_from_context

    app = create_app()

    async def override_get_db_from_context():
        yield db

    # Use Header() parameters instead of Request injection — FastAPI recognises
    # Header() in dependency overrides but does NOT auto-inject Request objects.
    async def override_get_current_user(
        x_test_tenant: str | None = Header(default=None, alias="X-Test-Tenant"),
        x_test_actor: str | None = Header(default=None, alias="X-Test-Actor"),
    ) -> TokenClaims:
        tenant_raw = x_test_tenant or str(TEST_ORG_ID)
        return TokenClaims(
            tenant_id=uuid.UUID(tenant_raw),
            user_id=x_test_actor or "test-user",
            roles=["admin"],
        )

    app.dependency_overrides[get_db_from_context] = override_get_db_from_context
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "X-Tenant-ID": str(TEST_ORG_ID),
            "X-Service-Auth": os.environ["SERVICE_AUTH_SECRET"],
        },
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
