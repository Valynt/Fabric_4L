"""Shared fixtures for security tests.

Copied from tests.api.conftest to avoid import path issues.
"""

from __future__ import annotations

from typing import Generator
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# Lazy import helpers
def _get_app():
    from value_fabric.layer1.api.app_monolith import app
    return app


def _get_base():
    from value_fabric.layer1.shared.models import Base
    return Base


def _get_db_override():
    from value_fabric.layer1.shared.database import get_db_from_context_sync
    return get_db_from_context_sync


def _make_target_factory():
    from value_fabric.layer1.shared.models import create_scraping_target
    return create_scraping_target


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def engine():
    """In-memory SQLite engine for each test."""
    return create_engine("sqlite:///:memory:")


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
            request.state.governance_context = {
                "tenant_id": str(org_id),
                "user_id": str(user_id),
                "roles": ["user"],
            }
            request.state.db = db
            response = await call_next(request)
            return response

    app.add_middleware(FakeGovernanceMiddleware)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db_from_context] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def make_target(db):
    """Factory for creating ScrapingTarget rows."""
    create_scraping_target = _make_target_factory()

    def _make(tenant_id: UUID, status: str = "ACTIVE", name: str = "Test Target"):
        return create_scraping_target(
            db,
            tenant_id=tenant_id,
            name=name,
            url="https://example.com",
            status=status,
        )

    return _make
