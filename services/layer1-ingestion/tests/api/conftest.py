"""Shared fixtures for API-level tests.

Provides:
  - `app_with_db`: FastAPI app wired to an in-memory SQLite DB
  - `client`: TestClient with a fake governance_context injected per request
  - `db`: SQLAlchemy Session scoped to each test
  - `org_id` / `other_org_id` / `user_id`: UUID fixtures
  - `make_target`: factory for ScrapingTarget rows
"""

from __future__ import annotations

import types
from typing import Generator
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# ---------------------------------------------------------------------------
# Lazy import helpers — avoid importing app_monolith at module level so that
# the root conftest stubs are applied first.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fake governance context
# ---------------------------------------------------------------------------

class _FakeCtx:
    """Minimal duck-type of GovernanceContext for tests."""

    def __init__(self, tenant_id: UUID, user_id: UUID):
        self.tenant_id = tenant_id
        self.user_id = str(user_id)
        self.roles: list[str] = ["admin"]


class _InjectGovernanceMiddleware(BaseHTTPMiddleware):
    """Injects a fake governance_context onto request.state for every request."""

    def __init__(self, app: ASGIApp, tenant_id: UUID, user_id: UUID):
        super().__init__(app)
        self._tenant_id = tenant_id
        self._user_id = user_id

    async def dispatch(self, request: Request, call_next):
        request.state.governance_context = _FakeCtx(self._tenant_id, self._user_id)
        return await call_next(request)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite engine shared across the test session."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base = _get_base()
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine) -> Generator[Session, None, None]:
    """Per-test DB session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(bind=connection)
    session = TestingSession()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def org_id() -> UUID:
    return uuid4()


@pytest.fixture()
def other_org_id() -> UUID:
    return uuid4()


@pytest.fixture()
def user_id() -> UUID:
    return uuid4()


@pytest.fixture()
def client(db: Session, org_id: UUID, user_id: UUID):
    """TestClient with governance context injected and DB overridden."""
    app = _get_app()
    get_db = _get_db_override()

    # Override the DB dependency to use the test session
    app.dependency_overrides[get_db] = lambda: db

    # Add middleware that injects governance_context
    # We wrap the app in a new ASGI app with the middleware applied
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as _TC

    # Build a thin wrapper app that injects the context then delegates
    wrapped = _InjectGovernanceMiddleware(app, tenant_id=org_id, user_id=user_id)

    with _TC(wrapped) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def make_target(db: Session):
    """Factory: create a ScrapingTarget row in the test DB."""
    factory = _make_target_factory()

    def _make(tenant_id: UUID, status: str = "ACTIVE", **kwargs) -> object:
        t = factory(
            tenant_id=tenant_id,
            name=kwargs.get("name", "Test Target"),
            url=kwargs.get("url", "https://example.com"),
            source_category=kwargs.get("source_category", "general"),
            extraction_config=kwargs.get("extraction_config", {"method": "llm"}),
        )
        t.status = status
        db.add(t)
        db.flush()
        db.refresh(t)
        return t

    return _make
