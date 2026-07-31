"""Regression contracts for Layer 4 tenant-RLS migration ordering."""

from __future__ import annotations

import ast
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _literal_list(path: Path, name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            value = ast.literal_eval(node.value)
            assert isinstance(value, list)
            return value
    raise AssertionError(f"{path.name} does not define {name}")


def test_revision_007_only_targets_existing_tenant_scoped_tables() -> None:
    path = MIGRATIONS / "007_add_rls_policies.py"
    source = path.read_text(encoding="utf-8")
    assert set(_literal_list(path, "RLS_TABLES")) == {
        "accounts",
        "audit_events",
        "feature_flags",
        "model_versions",
        "oidc_sessions",
    }
    assert "CREATE ROLE admin_role NOLOGIN" in source
    assert "CREATE ROLE system_role NOLOGIN" in source
    assert source.index("CREATE ROLE admin_role NOLOGIN") < source.index(
        "CREATE POLICY admin_bypass_policy"
    )


def test_revision_013_does_not_target_tables_before_tenant_columns_exist() -> None:
    path = MIGRATIONS / "013_add_missing_rls_policies.py"
    assert set(_literal_list(path, "RLS_TABLES")) == {
        "api_keys",
        "integrations",
        "tenant_isolation_tier_history",
        "users",
    }


def test_current_head_adds_strict_rls_for_late_tenant_scoped_tables() -> None:
    path = MIGRATIONS / "045_harden_late_tenant_tables.py"
    assert path.exists()
    source = path.read_text(encoding="utf-8")
    assert set(_literal_list(path, "RLS_TABLES")) == {
        "account_sync_status",
        "model_promotion_log",
    }
    assert 'op.add_column(\n        "model_promotion_log"' in source
    assert "UPDATE model_promotion_log AS promotion" in source
    assert 'op.alter_column("model_promotion_log", "tenant_id", nullable=False)' in source
    assert "tenant_id::text = current_setting('app.tenant_id', true)" in source
    assert "tenant_id IS NULL OR" not in source
