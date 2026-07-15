from __future__ import annotations

import re
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "api"
    / "migrations"
    / "versions"
    / "6f3b9c2d4a91_force_fabric_api_records_rls.py"
)


def _migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _create_policy_sql() -> str:
    source = _migration_source()
    match = re.search(
        r"CREATE POLICY fabric_api_records_tenant_isolation.*?;",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match is not None
    return match.group(0)


def test_fabric_api_records_migration_forces_rls() -> None:
    source = _migration_source()

    assert "ALTER TABLE fabric_api_records ENABLE ROW LEVEL SECURITY" in source
    assert "ALTER TABLE fabric_api_records FORCE ROW LEVEL SECURITY" in source


def test_fabric_api_records_policy_scopes_reads_to_session_tenant() -> None:
    policy_sql = _create_policy_sql()

    assert "USING (tenant_id = current_setting('app.tenant_id', true))" in policy_sql
    assert " admin" not in policy_sql.lower()
    assert "internal" not in policy_sql.lower()
    assert "system" not in policy_sql.lower()


def test_fabric_api_records_policy_blocks_cross_tenant_inserts_and_updates() -> None:
    policy_sql = _create_policy_sql()

    assert "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))" in policy_sql
