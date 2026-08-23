"""Fixtures for pipeline integration tests.

Provides a PostgreSQL-backed session so pipeline tasks like _fail_job()
read and write the same database as test setup, eliminating SQLite/PostgreSQL
split-brain failures.
"""

from __future__ import annotations

import os
from typing import Generator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool


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
            f"Pipeline integration tests must run against PostgreSQL. "
            f"Set TEST_DATABASE_URL environment variable to a PostgreSQL connection string."
        )


@pytest.fixture(scope="function")
def postgres_engine():
    """PostgreSQL engine for pipeline tests."""
    url = _get_postgres_url()
    engine = create_engine(url, poolclass=NullPool)
    _ensure_postgresql(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db(postgres_engine):
    """PostgreSQL session for pipeline tests.

    Creates tables, applies RLS policies, and monkeypatches
    layer1_ingestion.shared.database so _fail_job() uses the same DB.
    Overrides the root SQLite db fixture for tests/pipeline/.
    """
    from layer1_ingestion.shared.models import Base
    from layer1_ingestion.shared.database import get_db_session

    # Create tables
    Base.metadata.create_all(bind=postgres_engine)

    # Apply RLS policies (mirrors migration 017/018)
    tables = [
        "scraping_targets", "scraping_jobs", "raw_content",
        "extracted_data", "compliance_logs", "proxy_pools",
        "job_stage_details", "job_errors", "crawl_decisions",
    ]
    with postgres_engine.connect() as conn:
        conn.execute(text("""
            DO $$ BEGIN
                CREATE ROLE admin_role;
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
        conn.execute(text("""
            DO $$ BEGIN
                CREATE ROLE system_role;
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))

        for table in tables:
            conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}"))
            conn.execute(text(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}"))
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
            conn.execute(text(f"""
                CREATE POLICY tenant_isolation_policy ON {table}
                    FOR ALL
                    TO PUBLIC
                    USING (tenant_id::text = current_setting('app.tenant_id', true))
                    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
            """))
            conn.execute(text(f"""
                CREATE POLICY admin_bypass_policy ON {table}
                    FOR ALL
                    TO admin_role, system_role
                    USING (current_setting('app.tenant_id', true) = '')
            """))
        conn.commit()

    # Create test role for RLS
    with postgres_engine.connect() as conn:
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

    # Build RLS-enforced engine
    rls_engine = create_engine(_get_postgres_url(), poolclass=NullPool)

    def _set_role(dbapi_conn, _):
        with dbapi_conn.cursor() as cur:
            cur.execute("SET ROLE test_app_role")

    event.listen(rls_engine, "connect", _set_role)

    # Monkeypatch get_db_session to use test engine
    import layer1_ingestion.shared.database as db_module
    original_engine = db_module.engine
    original_session_local = db_module.SessionLocal
    db_module.engine = rls_engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rls_engine)

    # Yield superuser session for test data creation
    SessionLocal_super = sessionmaker(bind=postgres_engine)
    session = SessionLocal_super()
    try:
        yield session
    finally:
        session.close()
        # Restore
        db_module.engine = original_engine
        db_module.SessionLocal = original_session_local
        rls_engine.dispose()
        # Cleanup
        with postgres_engine.connect() as conn:
            conn.execute(text("DROP OWNED BY test_app_role"))
            conn.execute(text("DROP ROLE IF EXISTS test_app_role"))
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            conn.commit()


@pytest.fixture(scope="function")
def make_target(db, user_id):
    """Factory for creating ScrapingTarget rows in PostgreSQL."""
    from layer1_ingestion.shared.models import (
        ScrapingTarget, TargetType, SourceCategory
    )

    def _make(tenant_id: UUID, status: str = "ACTIVE", **kwargs) -> object:
        target = ScrapingTarget(
            tenant_id=tenant_id,
            name=kwargs.get("name", "Test Target"),
            url=kwargs.get("url", "https://example.com"),
            target_type=kwargs.get("target_type", TargetType.SINGLE_PAGE),
            created_by=kwargs.get("created_by", user_id),
            source_category=kwargs.get("source_category", SourceCategory.GENERAL),
            extraction_config=kwargs.get("extraction_config", {"method": "llm"}),
        )
        target.status = status
        db.add(target)
        db.flush()
        db.refresh(target)
        return target

    return _make
