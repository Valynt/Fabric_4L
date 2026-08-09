"""Pytest configuration for Layer 1 Ingestion tests."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

# Patch SQLite dialect to understand PostgreSQL JSONB (used by models)
# so that in-memory SQLite engines work in tests.
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402


def _visit_jsonb(self, type_, **kw):
    return self.visit_JSON(type_, **kw)


SQLiteTypeCompiler.visit_JSONB = _visit_jsonb

# Stub optional heavy deps before any imports that transitively require them
try:
    import opentelemetry  # noqa: F401
except ImportError:
    pass


def _make_pkg(name: str) -> ModuleType:
    m = types.ModuleType(name)
    m.__path__ = []
    spec = importlib.util.spec_from_loader(name, loader=None)
    spec.submodule_search_locations = []
    m.__spec__ = spec
    sys.modules[name] = m
    return m

# Idempotently ensure opentelemetry stubs exist (another conftest may have created a partial stub)
_otel = sys.modules.get("opentelemetry") or _make_pkg("opentelemetry")
if not hasattr(_otel, "trace"):
    _otel.trace = _make_pkg("opentelemetry.trace")
_otel.trace.Span = getattr(_otel.trace, "Span", type("Span", (), {}))
_otel.trace.SpanContext = getattr(_otel.trace, "SpanContext", type("SpanContext", (), {}))
_otel.trace.Status = getattr(_otel.trace, "Status", type("Status", (), {}))
_otel.trace.StatusCode = getattr(_otel.trace, "StatusCode", type("StatusCode", (), {}))

_otel_sdk = sys.modules.get("opentelemetry.sdk") or _make_pkg("opentelemetry.sdk")
if not hasattr(_otel_sdk, "resources"):
    _otel_sdk.resources = _make_pkg("opentelemetry.sdk.resources")
_otel_sdk.resources.Resource = getattr(_otel_sdk.resources, "Resource", type("Resource", (), {}))

if not hasattr(_otel_sdk, "trace"):
    _otel_sdk.trace = _make_pkg("opentelemetry.sdk.trace")
_otel_sdk.trace.TracerProvider = getattr(_otel_sdk.trace, "TracerProvider", type("TracerProvider", (), {}))

_otel_sdk_trace_exp = sys.modules.get("opentelemetry.sdk.trace.export") or _make_pkg("opentelemetry.sdk.trace.export")
_otel_sdk_trace_exp.BatchSpanProcessor = getattr(_otel_sdk_trace_exp, "BatchSpanProcessor", type("BatchSpanProcessor", (), {}))
_otel_sdk_trace_exp.ConsoleSpanExporter = getattr(_otel_sdk_trace_exp, "ConsoleSpanExporter", type("ConsoleSpanExporter", (), {}))

_otel_grpc = sys.modules.get("opentelemetry.exporter.otlp.proto.grpc.trace_exporter") or _make_pkg("opentelemetry.exporter.otlp.proto.grpc.trace_exporter")
_otel_grpc.OTLPSpanExporter = getattr(
    _otel_grpc,
    "OTLPSpanExporter",
    type("OTLPSpanExporter", (), {"__init__": lambda self, **kwargs: None}),
)

try:
    import psycopg2  # noqa: F401
except ImportError:
    sys.modules["psycopg2"] = MagicMock()

# Add src directory to Python path for imports
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add parent directory (services) so shared.* packages are importable
shared_root = str(Path(__file__).parent.parent.parent)
if shared_root not in sys.path:
    sys.path.insert(0, shared_root)

# Ensure PYTHONPATH includes src for subprocesses
os.environ["PYTHONPATH"] = src_path + os.pathsep + shared_root + os.pathsep + os.environ.get("PYTHONPATH", "")
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'


# ---------------------------------------------------------------------------
# Shared test fixtures (moved from tests/api/conftest.py so tests/unit/
# and tests/pipeline/ can access them)
# ---------------------------------------------------------------------------

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


def _get_app():
    # Patch rate limiting before app import so tests don't get 429 from Redis.
    from value_fabric.shared.identity import middleware as governance_middleware
    from value_fabric.shared.identity.middleware import GovernanceMiddleware

    async def _mock_check_rate_limit(self, request, ctx):
        mock_result = type("_MockResult", (), {"allowed": True, "remaining": 100, "reset_at": 0, "retry_after": None})
        return mock_result()

    async def _mock_enforce_tenant_status_method(self, ctx):
        return None

    async def _mock_enforce_tenant_status_function(ctx, **kwargs):
        return None

    GovernanceMiddleware._check_rate_limit = _mock_check_rate_limit
    GovernanceMiddleware._enforce_tenant_status = _mock_enforce_tenant_status_method
    governance_middleware.enforce_tenant_status = _mock_enforce_tenant_status_function
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


@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite engine shared across the test session."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    base = _get_base()
    base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def _postgres_engine():
    """PostgreSQL engine for integration tests marked with ``postgres``."""
    eng = create_engine(
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ingestion",
    )
    base = _get_base()
    base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(request, engine) -> Generator[Session, None, None]:
    """Per-test DB session that rolls back after each test.

    Uses PostgreSQL for tests marked with ``postgres``; SQLite otherwise.
    """
    if "postgres" in request.keywords:
        postgres_engine = request.getfixturevalue("_postgres_engine")
        connection = postgres_engine.connect()
    else:
        connection = engine.connect()
    transaction = connection.begin()
    testing_session = sessionmaker(bind=connection, expire_on_commit=False)
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

    app.dependency_overrides[get_db] = lambda: db

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


def pytest_runtest_setup(item):
    """Skip tests that require PostgreSQL if no PostgreSQL instance is available."""
    if "postgres" in item.keywords or "requires_postgres" in item.keywords:
        from sqlalchemy import create_engine, text
        try:
            engine = create_engine(
                "postgresql+psycopg2://postgres:postgres@localhost:5432/ingestion",
                connect_args={"connect_timeout": 2},
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            pytest.skip("PostgreSQL not available; skipping postgres test")
