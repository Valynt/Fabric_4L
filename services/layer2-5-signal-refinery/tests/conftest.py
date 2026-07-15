"""pytest configuration and shared fixtures for L2.5 Signal Refinery tests.

Uses in-memory SQLite (aiosqlite) for fast, isolated tests.
DATABASE_URL is overridden before any application code imports the engine.

Fixture hierarchy:
  engine      (session-scoped)  → tables created once per test session
  connection  (function-scoped) → single connection, outer transaction begun
  db          (function-scoped) → session bound to that connection; rolled back after test
  client      (function-scoped) → httpx.AsyncClient; all requests share the same
                                   connection so writes from one request are visible
                                   to the next within the same test, then rolled back
                                   when the test ends
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Override DATABASE_URL before any application code imports the engine
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["JWT_SECRET"] = "test-secret-32-chars-long-ok-yes"
os.environ["TESTING"] = "true"
# P0-008: Dev auth bypass flags removed — no longer needed

from layer2_5_signal_refinery import database as db_module  # noqa: E402
from layer2_5_signal_refinery.api.main import create_app  # noqa: E402
from layer2_5_signal_refinery.models.db_models import Base  # noqa: E402
from value_fabric.shared.identity.context import (  # noqa: E402
    RequestContext,
    set_request_context,
)
from value_fabric.shared.testing.governance import (  # noqa: E402
    patch_governance_middleware_for_tests,
)

# ---------------------------------------------------------------------------
# Shared test tenant IDs
# ---------------------------------------------------------------------------

TENANT_A = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
TENANT_B = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
ACCOUNT_A = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
ACCOUNT_B = uuid.UUID("dddddddd-0000-0000-0000-000000000004")


# ---------------------------------------------------------------------------
# Engine (session-scoped)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_module._engine = eng
    yield eng
    await eng.dispose()


# ---------------------------------------------------------------------------
# Connection (function-scoped) — outer transaction that is always rolled back
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def connection(engine) -> AsyncGenerator[AsyncConnection, None]:
    """Open a single connection with an outer transaction for the whole test.

    All sessions created within the test bind to this connection so that
    writes from one request are visible to subsequent requests in the same
    test. The outer transaction is rolled back when the test ends, leaving
    the database clean for the next test.
    """
    async with engine.connect() as conn:
        await conn.begin()
        yield conn
        await conn.rollback()


# ---------------------------------------------------------------------------
# DB session (function-scoped, bound to the test connection)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db(connection) -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession(bind=connection, expire_on_commit=False)
    yield session
    await session.close()


# ---------------------------------------------------------------------------
# HTTP client helpers
# ---------------------------------------------------------------------------


def _make_client_fixture(tenant_id: uuid.UUID):
    """Return a function-scoped AsyncClient fixture bound to the test connection."""

    @pytest_asyncio.fixture
    async def _client(connection) -> AsyncGenerator[AsyncClient, None]:
        app = create_app()
        patch_governance_middleware_for_tests(app)

        from layer2_5_signal_refinery import database as db_mod

        async def _test_db():
            # Bind each request's session to the shared test connection so
            # writes are visible across requests within the same test.
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                yield session
                await session.flush()
            finally:
                await session.close()

        app.dependency_overrides[db_mod.get_db_from_context] = _test_db
        
        @app.middleware("http")
        async def _inject_test_request_context(request, call_next):
            ctx = RequestContext(
                tenant_id=str(tenant_id),
                user_id="test-user",
                roles=["admin"],
                auth_source="jwt_claim",
            )
            request.state.governance_context = ctx
            set_request_context(ctx)
            try:
                return await call_next(request)
            finally:
                set_request_context(None)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            yield c

    return _client


client = _make_client_fixture(TENANT_A)
client_b = _make_client_fixture(TENANT_B)


# ---------------------------------------------------------------------------
# Shared signal factory
# ---------------------------------------------------------------------------


def make_signal_payload(
    account_id: str | None = None,
    signal_type: str = "pain",
    content: str = "Test signal content",
    confidence: float = 0.8,
) -> dict:
    return {
        "account_id": account_id or str(ACCOUNT_A),
        "type": signal_type,
        "content": content,
        "confidence": confidence,
        "trust_score": 0.7,
        "lifecycle_state": "extracted",
        "evidence": [
            {
                "id": str(uuid.uuid4()),
                "source_ref": "doc://test/source-1",
                "excerpt": "Relevant excerpt from source document.",
                "confidence": 0.85,
                "relevance_score": 0.9,
            }
        ],
        "provenance": {
            "extractor": "ai",
            "method": "llm_extraction",
            "model": "gpt-4o",
            "run_id": "run-test-001",
            "source_system": "layer2_extraction",
            "extracted_at": "2026-05-14T12:00:00Z",
        },
        "source_refs": ["doc://test/source-1"],
    }
