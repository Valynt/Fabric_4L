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
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ---------------------------------------------------------------------------
# Lazy import helpers — avoid importing the main app at module level so that
# the root conftest stubs are applied first.
# ---------------------------------------------------------------------------

def _get_app():
    # Patch rate limiting before app import so tests don't get 429 from Redis
    from value_fabric.shared.identity.middleware import GovernanceMiddleware

    async def _mock_check_rate_limit(self, request, ctx):
        mock_result = type("_MockResult", (), {"allowed": True, "remaining": 100, "reset_at": 0, "retry_after": None})
        return mock_result()

    GovernanceMiddleware._check_rate_limit = _mock_check_rate_limit
    from value_fabric.shared.error_handling.handlers import register_exception_handlers

    from layer1_ingestion.api.main import app

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


# ---------------------------------------------------------------------------
# Fake governance context
# ---------------------------------------------------------------------------

def _make_request_context(tenant_id: UUID, user_id: UUID, roles: list[str] | None = None):
    """Build a real RequestContext for tests."""
    from value_fabric.shared.identity.context import RequestContext
    return RequestContext(
        tenant_id=tenant_id,
        user_id=str(user_id),
        roles=roles or ["admin"],
        auth_source="jwt_claim",
    )


class _InjectGovernanceMiddleware(BaseHTTPMiddleware):
    """Injects a real RequestContext onto request.state for every request."""

    def __init__(self, app: ASGIApp, tenant_id: UUID, user_id: UUID, roles: list[str] | None = None):
        super().__init__(app)
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._roles = roles or ["admin"]

    async def dispatch(self, request: Request, call_next):
        request.state.governance_context = _make_request_context(
            self._tenant_id, self._user_id, self._roles
        )
        # Pre-populate a mock rate-limit result so the real GovernanceMiddleware
        # skips its Redis rate-limit check (avoids 429 in tests).
        mock_result = type("_MockResult", (), {"allowed": True, "remaining": 100, "reset_at": 0, "retry_after": None})
        request.state.rate_limit_result = mock_result()
        request.state.rate_limit_config = type("_MockConfig", (), {"requests_per_minute": 1000, "scope": type("_Scope", (), {"value": "tenant"})})()
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

    # Add middleware that injects governance_context
    # We wrap the app in a new ASGI app with the middleware applied
    from fastapi.testclient import TestClient

    # Build a thin wrapper app that injects the context then delegates
    wrapped = _InjectGovernanceMiddleware(app, tenant_id=org_id, user_id=user_id)

    with TestClient(wrapped) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def make_target(db: Session, user_id: UUID):
    """Factory: create a ScrapingTarget row in the test DB."""
    factory = _make_target_factory()
    from layer1_ingestion.shared.models import SourceCategory, TargetType

    def _make(tenant_id: UUID, status: str = "ACTIVE", **kwargs) -> object:
        t = factory(
            tenant_id=tenant_id,
            name=kwargs.get("name", "Test Target"),
            url=kwargs.get("url", "https://example.com"),
            target_type=kwargs.get("target_type", TargetType.SINGLE_PAGE),
            created_by=kwargs.get("created_by", user_id),
            source_category=kwargs.get("source_category", SourceCategory.GENERAL),
            extraction_config=kwargs.get("extraction_config", {"method": "llm"}),
        )
        t.status = status
        db.add(t)
        db.flush()
        db.refresh(t)
        return t

    return _make


@pytest.fixture(autouse=True)
def _mock_process_scraping_job(monkeypatch, request):
    """Mock Celery task delay/apply_async so API tests don't need a broker.

    Static contract tests (``@pytest.mark.contract_static``) that parse
    source code without importing the app skip this fixture to avoid paying
    the heavy import cost of the full L1 app and SQLAlchemy stack.
    """
    if request.node.get_closest_marker("contract_static"):
        return
    import layer1_ingestion.api._batch_and_stats as _batch_mod
    import layer1_ingestion.api.job_handlers as _job_handlers_mod
    import layer1_ingestion.api.main as _main_mod
    import layer1_ingestion.api.skill_handlers as _skill_handlers_mod
    import layer1_ingestion.api.target_handlers as _target_handlers_mod

    mock_task = type("_MockTask", (), {
        "delay": lambda *a, **k: None,
        "apply_async": lambda *a, **k: None,
    })
    monkeypatch.setattr(_batch_mod, "process_scraping_job", mock_task())
    monkeypatch.setattr(_job_handlers_mod, "process_scraping_job", mock_task())
    monkeypatch.setattr(_main_mod, "process_scraping_job", mock_task())
    monkeypatch.setattr(_skill_handlers_mod, "process_scraping_job", mock_task())
    monkeypatch.setattr(_target_handlers_mod, "process_scraping_job", mock_task())
