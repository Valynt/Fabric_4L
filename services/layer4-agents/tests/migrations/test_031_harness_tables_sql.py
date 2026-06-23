from __future__ import annotations

"""Structural validation of migration 031 SQL artifact.

Reads migrations/sql/031_harness_tables.sql from disk and asserts that the
generated DDL contains all required tables, tenant columns, indexes, FK
relationships, RLS policies, and unique constraints.

No live database is required — this test validates the pre-generated SQL file.
If the file is missing, the test fails with a clear message directing the
developer to regenerate it.
"""


from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Locate the SQL artifact
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent  # services/layer4-agents/
_SQL_FILE = _REPO_ROOT / "migrations" / "sql" / "031_harness_tables.sql"


@pytest.fixture(scope="module")
def sql() -> str:
    """Load the SQL artifact once for all tests in this module."""
    if not _SQL_FILE.exists():
        pytest.fail(
            f"Migration SQL artifact not found: {_SQL_FILE}\n"
            "Regenerate with:\n"
            "  cd services/layer4-agents\n"
            "  PYTHONPATH=.:<shared_src> LAYER4_DATABASE_URL=... "
            "LAYER1/2/3/5_API_URL=... ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT=true "
            "uv run alembic upgrade 030:031 --sql > migrations/sql/031_harness_tables.sql"
        )
    return _SQL_FILE.read_text()


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

EXPECTED_TABLES = [
    "harness_runs",
    "harness_human_gates",
    "harness_checkpoints",
    "harness_tool_contracts",
    "harness_trace_events",
]


@pytest.mark.parametrize("table", EXPECTED_TABLES)
def test_table_exists(sql: str, table: str) -> None:
    """Each harness table appears in a CREATE TABLE statement."""
    assert f"CREATE TABLE {table}" in sql, (
        f"Expected 'CREATE TABLE {table}' in migration SQL"
    )


# ---------------------------------------------------------------------------
# Tenant columns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("table", EXPECTED_TABLES)
def test_tenant_id_column_present(sql: str, table: str) -> None:
    """Every harness table has a tenant_id column definition."""
    # Find the CREATE TABLE block for this table and check tenant_id appears
    # before the next CREATE TABLE or end of file.
    start = sql.find(f"CREATE TABLE {table}")
    assert start != -1, f"Table {table} not found"
    # Find end of this CREATE TABLE block (next CREATE TABLE or COMMIT)
    next_create = sql.find("CREATE TABLE", start + 1)
    block = sql[start:next_create] if next_create != -1 else sql[start:]
    assert "tenant_id" in block, (
        f"Expected tenant_id column in CREATE TABLE {table}"
    )


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

EXPECTED_INDEXES = [
    # harness_runs
    "ix_harness_runs_tenant_status",
    "ix_harness_runs_tenant_state",
    "ix_harness_runs_trace_id",
    # harness_human_gates
    "ix_harness_human_gates_run_tenant",
    "ix_harness_human_gates_tenant_status",
    # harness_checkpoints
    "ix_harness_checkpoints_run_tenant",
    "ix_harness_checkpoints_tenant_state",
    "ix_harness_checkpoints_input_hash",
    # harness_tool_contracts
    "ix_harness_tool_contracts_tenant_layer",
    "ix_harness_tool_contracts_tenant_risk",
    # harness_trace_events
    "ix_harness_trace_events_run_tenant",
    "ix_harness_trace_events_tenant_type",
    "ix_harness_trace_events_trace_id",
]


@pytest.mark.parametrize("index_name", EXPECTED_INDEXES)
def test_index_exists(sql: str, index_name: str) -> None:
    """Each required index appears in a CREATE INDEX statement."""
    assert index_name in sql, (
        f"Expected index '{index_name}' in migration SQL"
    )


# ---------------------------------------------------------------------------
# Foreign key relationships
# ---------------------------------------------------------------------------

FK_CHILD_TABLES = [
    "harness_human_gates",
    "harness_checkpoints",
    "harness_trace_events",
]


@pytest.mark.parametrize("child_table", FK_CHILD_TABLES)
def test_foreign_key_to_harness_runs(sql: str, child_table: str) -> None:
    """Child tables reference harness_runs via FOREIGN KEY / REFERENCES."""
    start = sql.find(f"CREATE TABLE {child_table}")
    assert start != -1, f"Table {child_table} not found"
    next_create = sql.find("CREATE TABLE", start + 1)
    block = sql[start:next_create] if next_create != -1 else sql[start:]
    assert "harness_runs" in block, (
        f"Expected REFERENCES harness_runs in CREATE TABLE {child_table}"
    )


# ---------------------------------------------------------------------------
# RLS policies
# ---------------------------------------------------------------------------


def test_rls_enabled_for_all_tables(sql: str) -> None:
    """ENABLE ROW LEVEL SECURITY appears once per harness table (5 times)."""
    count = sql.count("ENABLE ROW LEVEL SECURITY")
    assert count == len(EXPECTED_TABLES), (
        f"Expected {len(EXPECTED_TABLES)} ENABLE ROW LEVEL SECURITY statements, "
        f"found {count}"
    )


@pytest.mark.parametrize("table", EXPECTED_TABLES)
def test_tenant_isolation_policy_per_table(sql: str, table: str) -> None:
    """tenant_isolation_policy is created for each harness table."""
    # The policy block references the table name
    assert f"ON {table}" in sql, (
        f"Expected RLS policy ON {table} in migration SQL"
    )


def test_tenant_isolation_policy_uses_app_tenant_id(sql: str) -> None:
    """RLS policy uses current_setting('app.tenant_id', true) for isolation."""
    assert "current_setting('app.tenant_id', true)" in sql, (
        "Expected RLS policy to use current_setting('app.tenant_id', true)"
    )


def test_admin_bypass_policy_present(sql: str) -> None:
    """admin_bypass_policy is present for privileged roles."""
    assert "admin_bypass_policy" in sql


# ---------------------------------------------------------------------------
# Unique constraint
# ---------------------------------------------------------------------------


def test_unique_constraint_tool_contracts(sql: str) -> None:
    """harness_tool_contracts has the (tenant_id, tool_id) unique constraint."""
    assert "uq_harness_tool_contracts_tenant_tool" in sql, (
        "Expected unique constraint uq_harness_tool_contracts_tenant_tool"
    )


# ---------------------------------------------------------------------------
# Transaction boundaries
# ---------------------------------------------------------------------------


def test_sql_wrapped_in_transaction(sql: str) -> None:
    """SQL artifact is wrapped in BEGIN / COMMIT."""
    assert sql.strip().startswith("BEGIN"), "SQL should start with BEGIN"
    assert "COMMIT" in sql, "SQL should contain COMMIT"


def test_alembic_version_updated(sql: str) -> None:
    """Migration updates alembic_version to '031'."""
    assert "version_num='031'" in sql, (
        "Expected alembic_version update to '031'"
    )
