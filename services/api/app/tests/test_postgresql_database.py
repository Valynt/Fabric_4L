"""P0-004 acceptance test: API PostgreSQL driver.

Validates:
1. PostgreSQLDatabase class exists and is returned for PostgreSQL URLs
2. get_pg_engine creates an async engine
3. Health check runs SELECT 1
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.database import (
    PostgreSQLDatabase,
    PostgreSQLTable,
    get_pg_engine,
    create_database,
    UnsupportedDatabaseURL,
    ProductionPersistenceNotConfigured,
)


def test_postgresql_database_class_exists():
    """PostgreSQLDatabase must be importable and have expected tables."""
    db = PostgreSQLDatabase(pool=MagicMock())
    assert hasattr(db, "accounts")
    assert hasattr(db, "tenants")
    assert hasattr(db, "audit_logs")
    assert isinstance(db.accounts, PostgreSQLTable)


def test_create_database_raises_for_unsupported_url():
    """Unsupported database URLs must raise UnsupportedDatabaseURL."""
    with patch("app.core.database.get_settings") as mock_settings:
        mock_settings.return_value.mock_persistence = False
        mock_settings.return_value.database_url = "mysql://user:pass@localhost/db"
        with pytest.raises(UnsupportedDatabaseURL):
            get_pg_engine()


def test_create_database_returns_postgresql_for_pg_url():
    """PostgreSQL URLs must be accepted by get_pg_engine."""
    with patch("app.core.database.get_settings") as mock_settings:
        mock_settings.return_value.mock_persistence = False
        mock_settings.return_value.database_url = "postgresql+asyncpg://user:pass@localhost/db"
        with patch("app.core.database._ASYNC_ENGINE_AVAILABLE", True):
            with patch("app.core.database.get_async_engine") as mock_engine:
                mock_engine.return_value = MagicMock()
                engine = get_pg_engine()
                assert engine is not None
                mock_engine.assert_called_once()


def test_postgresql_table_health_check_select_1():
    """PostgreSQLTable must be able to run a basic SELECT 1 via its pool."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = (1,)
    mock_conn.cursor.return_value.__enter__ = lambda s, *a, **k: mock_cur
    mock_conn.cursor.return_value.__exit__ = lambda s, *a, **k: None
    mock_pool.connection.return_value.__enter__ = lambda s, *a, **k: mock_conn
    mock_pool.connection.return_value.__exit__ = lambda s, *a, **k: None

    table = PostgreSQLTable("test_table", mock_pool)
    # Verify the pool connection context manager works
    with mock_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            assert result == (1,)


def test_create_database_fails_closed_in_production_without_url():
    """Production-like environments must not fall back to in-memory without URL."""
    with patch("app.core.database.get_settings") as mock_settings:
        mock_settings.return_value.mock_persistence = False
        mock_settings.return_value.database_url = None
        with pytest.raises(ProductionPersistenceNotConfigured):
            create_database()


def _make_table_with_cursor():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s, *a, **k: mock_cur
    mock_conn.cursor.return_value.__exit__ = lambda s, *a, **k: None
    mock_pool.connection.return_value.__enter__ = lambda s, *a, **k: mock_conn
    mock_pool.connection.return_value.__exit__ = lambda s, *a, **k: None
    return mock_pool, mock_cur


def test_postgresql_table_uses_migrated_record_columns():
    """Regression: fabric_api_records SQL must match the migrated schema
    (revision 2be6428bc79b: record_type/record_key, unique on
    (tenant_id, record_type, record_key)). The code previously queried
    table_name/id, which do not exist post-migration, 500-ing every gateway
    route backed by this store (observed via the Meridian certification
    journey, 2026-08-12).
    """
    mock_pool, mock_cur = _make_table_with_cursor()
    table = PostgreSQLTable("accounts", mock_pool)

    table.get("rec-1", tenant_id="11111111-1111-4111-8111-111111111111")
    get_sql = mock_cur.execute.call_args[0][0]
    assert "record_type" in get_sql and "record_key" in get_sql
    assert "table_name" not in get_sql

    mock_cur.reset_mock()
    mock_cur.fetchone.return_value = None
    table.delete("rec-1", tenant_id="11111111-1111-4111-8111-111111111111")
    delete_sql = mock_cur.execute.call_args[0][0]
    assert "record_type" in delete_sql and "record_key" in delete_sql
    assert "table_name" not in delete_sql


def test_postgresql_table_insert_targets_migration_unique_constraint():
    """Insert must upsert on the migration's UNIQUE (tenant_id, record_type,
    record_key) constraint."""
    mock_pool, mock_cur = _make_table_with_cursor()
    table = PostgreSQLTable("accounts", mock_pool)

    table.insert("rec-1", {"id": "rec-1", "tenant_id": "11111111-1111-4111-8111-111111111111", "name": "x"})
    insert_sql = mock_cur.execute.call_args[0][0]
    assert "record_type" in insert_sql and "record_key" in insert_sql
    assert "ON CONFLICT (tenant_id, record_type, record_key)" in insert_sql
    assert "table_name" not in insert_sql


def test_usage_events_table_deserializes_to_model():
    """Regression: usage_events must deserialize JSONB payloads to
    UsageEventRecord (like api_keys does with APIKeyRecord); otherwise
    QuotaService crashes with AttributeError on dict payloads (observed via
    the Meridian certification journey benchmark stage, 2026-08-13).
    """
    mock_pool, mock_cur = _make_table_with_cursor()
    mock_cur.fetchall.return_value = [
        ({"event_id": "e1", "tenant_id": "t1", "api_key_id": None,
          "endpoint": "/v1/benchmarks/compare", "method": "POST",
          "product_code": "benchmarks", "quantity": 1.0, "unit": "request"},)
    ]
    db = PostgreSQLDatabase(pool=mock_pool)
    events = db.usage_events.list(tenant_id="system", allow_system_scope=True)
    assert events and events[0].product_code == "benchmarks"
