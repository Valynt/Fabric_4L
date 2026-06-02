"""Shared fixtures for security tests.

Copied from tests.api.conftest to avoid import path issues.
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
    # Patch rate limiting before app import so tests don't get 429 from Redis
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    async def _mock_check_rate_limit(self, request, ctx):
        _MockResult = type("_MockResult", (), {"allowed": True, "remaining": 100, "reset_at": 0, "retry_after": None})
        return _MockResult()
    GovernanceMiddleware._check_rate_limit = _mock_check_rate_limit
    from layer1_ingestion.api.app_monolith import app
    from value_fabric.shared.error_handling.handlers import register_exception_handlers
    register_exception_handlers(app)
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
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ingestion"
    )


def _ensure_postgresql(engine):
    """Skip tests if not running against PostgreSQL."""
    dialect = engine.dialect.name
    if dialect != "postgresql":
        pytest.skip(
            f"PostgreSQL-required test running against {dialect}. "
            f"Security/RLS tests must run against PostgreSQL to validate "
            f"PostgreSQL-specific behavior (JSONB, RLS, SET LOCAL, current_setting). "
            f"Set TEST_DATABASE_URL environment variable to a PostgreSQL connection string."
        )


# ---------------------------------------------------------------------------
# SQLite Fixtures (for non-PostgreSQL tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def engine():
    """In-memory SQLite engine for each test."""
    return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@pytest.fixture(scope="function")
def db(engine):
    """SQLAlchemy Session scoped to each test."""
    Base = _get_base()
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# PostgreSQL Fixtures (for PostgreSQL-required tests)
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
    
    # Enable RLS on all tables that support it
    with postgres_engine.connect() as conn:
        try:
            conn.execute(text("SET session_replication_role = 'replica'"))
            conn.commit()
        except Exception:
            pass
    
    SessionLocal = sessionmaker(bind=postgres_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=postgres_engine)


@pytest.fixture(scope="function")
def make_job(postgres_db, user_id):
    """Factory for creating ScrapingJob rows."""
    from layer1_ingestion.shared.models import ScrapingJob, JobStatus
    from uuid import uuid4

    def _make(tenant_id: UUID, target_id: UUID = None, status: str = JobStatus.PENDING.value, created_by: UUID = None):
        if target_id is None:
            target_id = uuid4()
        if created_by is None:
            created_by = user_id
        job = ScrapingJob(
            id=uuid4(),
            tenant_id=tenant_id,
            target_id=target_id,
            status=status,
            configuration={},
            created_by=created_by,
        )
        postgres_db.add(job)
        postgres_db.commit()
        postgres_db.refresh(job)
        return job

    return _make


# ---------------------------------------------------------------------------
# Common Fixtures
# ---------------------------------------------------------------------------

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
def client(org_id, user_id, db):
    """TestClient with fake governance context injected per request."""
    app = _get_app()
    get_db_from_context = _get_db_override()

    class FakeGovernanceMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            from value_fabric.shared.identity.context import RequestContext
            request.state.governance_context = RequestContext(
                tenant_id=org_id,
                user_id=str(user_id),
                roles=["user"],
                auth_source="jwt_claim",
            )
            request.state.db = db
            # Pre-populate a mock rate-limit result so the real GovernanceMiddleware
            # skips its Redis rate-limit check (avoids 429 in tests).
            _MockResult = type("_MockResult", (), {"allowed": True, "remaining": 100, "reset_at": 0, "retry_after": None})
            request.state.rate_limit_result = _MockResult()
            request.state.rate_limit_config = type("_MockConfig", (), {"requests_per_minute": 1000, "scope": type("_Scope", (), {"value": "tenant"})})()
            response = await call_next(request)
            return response

    def override_get_db():
        yield db

    app.dependency_overrides[get_db_from_context] = override_get_db

    # Wrap app with middleware instead of mutating global app
    wrapped = FakeGovernanceMiddleware(app)
    with TestClient(wrapped) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def make_target(db, user_id):
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
        db.add(t)
        db.flush()
        db.refresh(t)
        return t

    return _make
