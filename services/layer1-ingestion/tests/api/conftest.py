"""Shared fixtures for API-level tests.

Provides:
  - `app_with_db`: FastAPI app wired to an in-memory SQLite DB
  - `client`: TestClient with a fake governance_context injected per request
  - `db`: SQLAlchemy Session scoped to each test
  - `org_id` / `other_org_id` / `user_id`: UUID fixtures
  - `make_target`: factory for ScrapingTarget rows
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from value_fabric.shared.identity.context import RequestContext

# ---------------------------------------------------------------------------
# Lazy import helpers — avoid importing app_monolith at module level so that
# the root conftest stubs are applied first.
# ---------------------------------------------------------------------------


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
    from value_fabric.layer1.shared.models import SourceCategory, TargetType, create_scraping_target

    return create_scraping_target, TargetType, SourceCategory


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


# ---------------------------------------------------------------------------
# Fake governance context
# ---------------------------------------------------------------------------


class _InjectGovernanceMiddleware(BaseHTTPMiddleware):
    """Injects a fake governance_context onto request.state for every request."""

    def __init__(self, app: ASGIApp, tenant_id: UUID, user_id: UUID):
        super().__init__(app)
        self._tenant_id = tenant_id
        self._user_id = user_id

    async def dispatch(self, request: Request, call_next):
        request.state.governance_context = RequestContext(
            tenant_id=self._tenant_id,
            user_id=str(self._user_id),
            roles=["admin"],
            source="jwt",
        )
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
    base = _get_base()
    base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine) -> Generator[Session, None, None]:
    """Per-test DB session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    testing_session = sessionmaker(bind=connection)
    session = testing_session()
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

    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "GovernanceMiddleware":
            middleware.kwargs["rate_limiter"] = None
    app.middleware_stack = None

    # Add middleware that injects governance_context
    # We wrap the app in a new ASGI app with the middleware applied
    from fastapi.testclient import TestClient

    # Build a thin wrapper app that injects the context then delegates
    wrapped = _InjectGovernanceMiddleware(app, tenant_id=org_id, user_id=user_id)

    with TestClient(wrapped) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def make_target(db: Session):
    """Factory: create a ScrapingTarget row in the test DB."""
    factory, target_type_enum, source_category_enum = _make_target_factory()

    def _make(tenant_id: UUID, status: str = "ACTIVE", **kwargs) -> object:
        source_category_value = kwargs.get("source_category", source_category_enum.GENERAL)
        if isinstance(source_category_value, str):
            source_category_value = source_category_enum[source_category_value.upper()]
        t = factory(
            tenant_id=tenant_id,
            name=kwargs.get("name", "Test Target"),
            url=kwargs.get("url", "https://example.com"),
            target_type=kwargs.get("target_type", target_type_enum.SINGLE_PAGE),
            created_by=kwargs.get("created_by", uuid4()),
            source_category=source_category_value,
            extraction_config=kwargs.get("extraction_config", {"method": "llm"}),
        )
        t.status = status
        db.add(t)
        db.flush()
        db.refresh(t)
        return t

    return _make
