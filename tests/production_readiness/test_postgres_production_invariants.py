from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.postgres_only
@pytest.mark.requires_postgres
@pytest.mark.production_db_invariant
def test_postgres_invariant_suite_uses_postgresql_url() -> None:
    """Guardrail: production DB invariants are not allowed to run only on SQLite."""
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    parsed = urlparse(database_url)

    assert parsed.scheme.startswith("postgresql"), (
        "gate-database-live requires TEST_DATABASE_URL or DATABASE_URL to point at PostgreSQL. "
        f"Got scheme {parsed.scheme!r}. SQLite/local compatibility belongs in pure unit tests only."
    )


@pytest.mark.postgres_only
@pytest.mark.requires_postgres
@pytest.mark.production_db_invariant
def test_postgres_invariant_suite_has_live_connection_contract() -> None:
    """This suite is the required home for RLS, migrations, constraints, indexes, hooks, and transaction semantics."""
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""

    assert (
        database_url and "sqlite" not in database_url.lower()
    ), "Production-readiness DB invariants must use a live PostgreSQL URL; SQLite is only for pure unit tests."


@pytest.mark.asyncio
@pytest.mark.postgres_only
@pytest.mark.requires_postgres
@pytest.mark.production_db_invariant
async def test_postgres_transaction_local_tenant_context_round_trip() -> None:
    """PostgreSQL-backed coverage for RLS tenant hooks and transaction-local semantics."""
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    parsed = urlparse(database_url)
    assert parsed.scheme.startswith(
        "postgresql"
    ), "PostgreSQL URL required for production DB transaction semantics."

    engine = create_async_engine(
        database_url, pool_pre_ping=True, pool_size=1, max_overflow=0
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": "11111111-1111-4111-8111-111111111111"},
            )
            value = await conn.scalar(
                text("SELECT current_setting('app.tenant_id', true)")
            )
            assert value == "11111111-1111-4111-8111-111111111111"

        async with engine.begin() as conn:
            value = await conn.scalar(
                text("SELECT current_setting('app.tenant_id', true)")
            )
            assert value in (
                None,
                "",
            ), "SET LOCAL tenant context must not leak across transactions."
    finally:
        await engine.dispose()


async def _fetch_scalar(database_url: str, sql: str) -> int | bool | None:
    engine = create_async_engine(
        database_url, pool_pre_ping=True, pool_size=1, max_overflow=0
    )
    try:
        async with engine.begin() as conn:
            return await conn.scalar(text(sql))
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.postgres_only
@pytest.mark.requires_postgres
@pytest.mark.production_db_invariant
async def test_postgres_migrations_have_applied_alembic_version() -> None:
    """PostgreSQL-backed migration readiness: Alembic state must exist on the target DB."""
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    parsed = urlparse(database_url)
    assert parsed.scheme.startswith(
        "postgresql"
    ), "PostgreSQL URL required for migration readiness."

    has_alembic_version = await _fetch_scalar(
        database_url,
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_name = 'alembic_version'
        )
        """,
    )
    assert (
        has_alembic_version is True
    ), "Production-readiness DB must expose applied Alembic migration state."


@pytest.mark.asyncio
@pytest.mark.postgres_only
@pytest.mark.requires_postgres
@pytest.mark.production_db_invariant
async def test_postgres_catalog_has_rls_constraints_and_indexes() -> None:
    """PostgreSQL-backed RLS, constraint, and index readiness via PostgreSQL catalogs."""
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    parsed = urlparse(database_url)
    assert parsed.scheme.startswith(
        "postgresql"
    ), "PostgreSQL URL required for catalog readiness."

    rls_table_count = await _fetch_scalar(
        database_url,
        """
        SELECT COUNT(*)
        FROM pg_class cls
        JOIN pg_namespace ns ON ns.oid = cls.relnamespace
        WHERE cls.relkind = 'r'
          AND cls.relrowsecurity = true
          AND ns.nspname NOT IN ('pg_catalog', 'information_schema')
        """,
    )
    constraint_count = await _fetch_scalar(
        database_url,
        """
        SELECT COUNT(*)
        FROM pg_constraint c
        JOIN pg_namespace ns ON ns.oid = c.connamespace
        WHERE ns.nspname NOT IN ('pg_catalog', 'information_schema')
        """,
    )
    index_count = await _fetch_scalar(
        database_url,
        """
        SELECT COUNT(*)
        FROM pg_indexes
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        """,
    )

    assert (
        int(rls_table_count or 0) > 0
    ), "Production-readiness DB must have RLS-enabled tenant tables."
    assert (
        int(constraint_count or 0) > 0
    ), "Production-readiness DB must have application constraints."
    assert (
        int(index_count or 0) > 0
    ), "Production-readiness DB must have application indexes."
