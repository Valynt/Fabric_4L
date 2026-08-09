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
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# Lazy import helpers
def _get_app():
    from layer1_ingestion.api.main import app
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

def _apply_rls_policies(engine):
    """Apply production RLS DDL to test database.
    
    Mirrors migration 017: enables RLS and creates tenant isolation policies
    using tenant_id.  Must run after Base.metadata.create_all().
    """
    tables = [
        "scraping_targets",
        "scraping_jobs",
        "raw_content",
        "extracted_data",
        "compliance_logs",
        "proxy_pools",
        "job_stage_details",
        "job_errors",
        "crawl_decisions",
    ]
    with engine.connect() as conn:
        for table in tables:
            conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"))
            conn.execute(text(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}"))
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
            conn.execute(text(f"""
                CREATE POLICY tenant_isolation_policy ON {table}
                    FOR ALL
                    TO PUBLIC
                    USING (
                        tenant_id::text = current_setting('app.tenant_id', true)
                    )
                    WITH CHECK (
                        tenant_id::text = current_setting('app.tenant_id', true)
                    )
            """))
            conn.execute(text(f"""
                CREATE POLICY admin_bypass_policy ON {table}
                    FOR ALL
                    TO admin_role, system_role
                    USING (current_setting('app.tenant_id', true) = '')
            """))
        conn.commit()


def _create_test_role(engine):
    """Create a non-superuser role for RLS enforcement tests."""
    with engine.connect() as conn:
        conn.execute(text("""
            DO $$ BEGIN
                CREATE ROLE test_app_role WITH LOGIN PASSWORD 'test';
            EXCEPTION WHEN duplicate_object THEN
                ALTER ROLE test_app_role WITH LOGIN PASSWORD 'test';
            END $$;
        """))
        conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO test_app_role"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO test_app_role"))
        conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO test_app_role"))
        conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO test_app_role"))
        conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO test_app_role"))
        conn.commit()


def _drop_test_role(engine):
    """Drop the test role created for RLS enforcement tests."""
    with engine.connect() as conn:
        conn.execute(text("DROP OWNED BY test_app_role"))
        conn.execute(text("DROP ROLE IF EXISTS test_app_role"))
        conn.commit()


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

    # Apply real RLS policies (matches production migration 017)
    _apply_rls_policies(postgres_engine)

    # Create non-superuser role for RLS enforcement
    _create_test_role(postgres_engine)

    # Build an engine that enforces RLS by connecting as a non-superuser role.
    rls_engine = create_engine(_get_postgres_url(), poolclass=NullPool)

    def _set_role(dbapi_conn, connection_record):
        with dbapi_conn.cursor() as cur:
            cur.execute("SET ROLE test_app_role")

    event.listen(rls_engine, "connect", _set_role)

    # Monkeypatch module-level database engine so get_db_session uses the RLS engine
    import layer1_ingestion.shared.database as db_module
    original_engine = db_module.engine
    original_session_local = db_module.SessionLocal
    db_module.engine = rls_engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rls_engine)

    # Superuser session for test data creation (bypasses RLS)
    SessionLocal_super = sessionmaker(bind=postgres_engine)
    session = SessionLocal_super()
    try:
        yield session
    finally:
        session.close()
        # Restore original engine and SessionLocal
        db_module.engine = original_engine
        db_module.SessionLocal = original_session_local
        rls_engine.dispose()
        # Drop test role and fast cleanup
        _drop_test_role(postgres_engine)
        with postgres_engine.connect() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            conn.commit()


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
            # Create a dummy target to satisfy foreign key constraint
            from layer1_ingestion.shared.models import ScrapingTarget
            target = ScrapingTarget(
                tenant_id=tenant_id,
                name="Test Target",
                url="https://example.com",
                target_type="SINGLE_PAGE",
                status="ACTIVE",
                created_by=user_id,
            )
            postgres_db.add(target)
            postgres_db.flush()
            postgres_db.refresh(target)
            target_id = target.id
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
