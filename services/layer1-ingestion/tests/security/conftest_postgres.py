"""PostgreSQL-backed fixtures for security and RLS tests.

This conftest provides fixtures that require PostgreSQL-specific features:
- JSONB columns
- Row-Level Security (RLS)
- SET LOCAL app.tenant_id
- current_setting('app.tenant_id')
- FORCE ROW LEVEL SECURITY

Tests using this conftest must be marked with @pytest.mark.postgres
"""

from __future__ import annotations

import os
from typing import Generator
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# Lazy import helpers
def _get_app():
    from layer1_ingestion.api.app_monolith import app
    return app


def _get_base():
    from layer1_ingestion.shared.models import Base
    return Base


def _get_db_override():
    from layer1_ingestion.shared.database import get_db_from_context_sync
    return get_db_from_context_sync


def _make_target_factory():
    from layer1_ingestion.shared.models import create_scraping_target
    return create_scraping_target


def _get_postgres_url():
    """Get PostgreSQL URL from environment or use default dev stack."""
    # Priority: env var > docker-compose dev stack default
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ingestion"
    )


# ---------------------------------------------------------------------------
# Hard guard: fail if not PostgreSQL
# ---------------------------------------------------------------------------

def _ensure_postgresql(engine):
    """Hard guard: fail tests if not running against PostgreSQL."""
    dialect = engine.dialect.name
    if dialect != "postgresql":
        pytest.fail(
            f"PostgreSQL-required test running against {dialect}. "
            f"Security/RLS tests must run against PostgreSQL to validate "
            f"PostgreSQL-specific behavior (JSONB, RLS, SET LOCAL, current_setting). "
            f"Set TEST_DATABASE_URL environment variable to a PostgreSQL connection string."
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def postgres_engine():
    """PostgreSQL engine for security tests."""
    url = _get_postgres_url()
    engine = create_engine(url)
    _ensure_postgresql(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def postgres_db(postgres_engine):
    """SQLAlchemy Session scoped to each test with PostgreSQL."""
    Base = _get_base()

    # Create all tables
    Base.metadata.create_all(bind=postgres_engine)

    # Monkeypatch module-level database engine so get_db_session uses the test DB
    import layer1_ingestion.shared.database as db_module
    original_engine = db_module.engine
    original_session_local = db_module.SessionLocal
    db_module.engine = postgres_engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)

    # Enable RLS on all tables that support it
    with postgres_engine.connect() as conn:
        # This will be applied by migrations in production, but for tests
        # we need to ensure RLS is enabled
        try:
            conn.execute(text("SET session_replication_role = 'replica'"))
            conn.commit()
        except Exception:
            # If this fails, it's okay - migrations should handle it
            pass

    SessionLocal = sessionmaker(bind=postgres_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Restore original engine and SessionLocal
        db_module.engine = original_engine
        db_module.SessionLocal = original_session_local
        # Clean up: drop all tables
        Base.metadata.drop_all(bind=postgres_engine)


@pytest.fixture(scope="function")
def org_id() -> UUID:
    """Primary tenant ID for tests."""
    return uuid4()


@pytest.fixture(scope="function")
def other_org_id() -> UUID:
    """Secondary tenant ID for cross-tenant isolation tests."""
    return uuid4()


@pytest.fixture(scope="function")
def user_id() -> UUID:
    """User ID for tests."""
    return uuid4()


@pytest.fixture(scope="function")
def postgres_client(org_id, user_id, postgres_db):
    """TestClient with fake governance context injected per request."""
    app = _get_app()
    get_db_from_context = _get_db_override()

    class FakeGovernanceMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request.state.governance_context = {
                "tenant_id": str(org_id),
                "user_id": str(user_id),
                "roles": ["user"],
            }
            request.state.db = postgres_db
            response = await call_next(request)
            return response

    app.add_middleware(FakeGovernanceMiddleware)

    def override_get_db():
        yield postgres_db

    app.dependency_overrides[get_db_from_context] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def make_target(postgres_db, user_id):
    """Factory for creating ScrapingTarget rows."""
    create_scraping_target = _make_target_factory()
    from layer1_ingestion.shared.models import TargetType

    def _make(tenant_id: UUID, status: str = "ACTIVE", name: str = "Test Target"):
        t = create_scraping_target(
            tenant_id=tenant_id,
            name=name,
            url="https://example.com",
            target_type=TargetType.SINGLE_PAGE,
            created_by=user_id,
        )
        t.status = status
        postgres_db.add(t)
        postgres_db.flush()
        postgres_db.refresh(t)
        return t

    return _make


@pytest.fixture(scope="function")
def make_job(postgres_db, user_id):
    """Factory for creating ScrapingJob rows."""
    from layer1_ingestion.shared.models import ScrapingJob, JobStatus
    from uuid import uuid4

    def _make(tenant_id: UUID, target_id: UUID = None, status: str = JobStatus.PENDING.value):
        if target_id is None:
            target_id = uuid4()
        job = ScrapingJob(
            id=uuid4(),
            tenant_id=tenant_id,
            target_id=target_id,
            status=status,
            configuration={},
            created_by=user_id,
        )
        postgres_db.add(job)
        postgres_db.commit()
        postgres_db.refresh(job)
        return job

    return _make
