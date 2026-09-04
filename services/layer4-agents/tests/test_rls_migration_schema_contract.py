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


def test_revision_015_declares_event_name_index_once() -> None:
    source = (MIGRATIONS / "015_add_usage_events_table.py").read_text(encoding="utf-8")

    assert 'sa.Column("event_name", sa.String(100), nullable=False, index=True)' in source
    assert 'op.create_index(\n        "ix_billing_usage_events_event_name"' not in source


def test_revision_015_recent_index_uses_only_immutable_expressions() -> None:
    source = (MIGRATIONS / "015_add_usage_events_table.py").read_text(encoding="utf-8")

    assert "CREATE INDEX ix_billing_usage_events_recent" in source
    assert "WHERE created_at > NOW()" not in source


def test_revision_018_only_targets_billing_tables_created_by_revision_017() -> None:
    path = MIGRATIONS / "018_add_rls_to_billing_tables.py"
    assert set(_literal_list(path, "RLS_TABLES")) == {
        "billing_customers",
        "billing_subscriptions",
        "billing_usage_events",
        "billing_webhook_events",
    }


def test_revision_018_public_policy_requires_an_exact_tenant_match() -> None:
    source = (MIGRATIONS / "018_add_rls_to_billing_tables.py").read_text(encoding="utf-8")
    public_policy = source.split("CREATE POLICY tenant_isolation_policy", maxsplit=1)[1].split(
        "CREATE POLICY admin_bypass_policy", maxsplit=1
    )[0]
    normalized_policy = " ".join(public_policy.split())
    strict_tenant_match = "tenant_id::text = current_setting('app.tenant_id', true)"

    assert f"USING ( {strict_tenant_match} )" in normalized_policy
    assert f"WITH CHECK ( {strict_tenant_match} )" in normalized_policy
    assert "tenant_id IS NULL" not in public_policy


def test_revision_019_does_not_recreate_account_tenant_ownership() -> None:
    source = (MIGRATIONS / "019_add_account_enrichment_columns.py").read_text(encoding="utf-8")
    assert 'op.add_column(\n        "accounts",\n        sa.Column("tenant_id"' not in source
    assert 'op.create_index("ix_accounts_tenant_id"' not in source
    assert "CREATE POLICY accounts_tenant_isolation" not in source
    assert 'op.drop_column("accounts", "tenant_id")' not in source


def test_revision_020_adds_tenant_identity_before_late_table_rls() -> None:
    source = (MIGRATIONS / "020_tenant_safe_crm_sync_constraints.py").read_text(encoding="utf-8")
    assert 'op.add_column(\n        "account_sync_status"' in source
    assert 'sa.Column("tenant_id"' in source


def test_revisions_022_and_023_do_not_target_unowned_usage_events_table() -> None:
    revision_022 = (MIGRATIONS / "022_add_missing_foreign_key_constraints.py").read_text(
        encoding="utf-8"
    )
    revision_023 = (MIGRATIONS / "023_add_covering_indexes.py").read_text(encoding="utf-8")

    assert "usage_events" not in revision_022
    assert "usage_events" not in revision_023
    assert "except Exception" not in revision_022


def test_revision_023_indexes_match_columns_created_by_prior_revisions() -> None:
    source = (MIGRATIONS / "023_add_covering_indexes.py").read_text(encoding="utf-8")

    assert "INCLUDE (display_name, role, created_at, last_login_at)" in source
    assert "INCLUDE (display_name, email, last_login_at, status)" in source
    assert "ON audit_events (tenant_id, resource_type, resource_id, timestamp DESC)" in source
    assert "INCLUDE (action, user_id, details, outcome)" in source
    assert "ON feature_flags (tenant_id, flag_key, enabled)" in source
    assert "INCLUDE (description, updated_by, created_at, updated_at)" in source
    for stale_column in ("entity_type", "entity_id", "actor_id", "changes", "is_enabled"):
        assert stale_column not in source


def test_revision_036_widens_alembic_version_before_long_revision_ids() -> None:
    source = (MIGRATIONS / "036_add_billing_customer_sync_state.py").read_text(encoding="utf-8")

    widen = 'ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)'
    assert widen in source
    assert source.index(widen) < source.index('op.add_column("billing_customers"')


def test_revision_041_does_not_recreate_revision_027_tenant_index() -> None:
    revision_027 = (MIGRATIONS / "027_add_tenant_id_to_business_case_records.py").read_text(
        encoding="utf-8"
    )
    revision_041 = (
        MIGRATIONS / "041_add_business_case_records_tenant_indexes.py"
    ).read_text(encoding="utf-8")

    assert '"ix_business_case_records_tenant_id"' in revision_027
    assert '"ix_business_case_records_tenant_id"' not in revision_041
    assert '"ix_business_case_records_tenant_status"' in revision_041


def test_current_head_adds_strict_rls_for_late_tenant_scoped_tables() -> None:
    path = MIGRATIONS / "045_harden_late_tenant_tables.py"
    assert path.exists()
    source = path.read_text(encoding="utf-8")
    assert set(_literal_list(path, "RLS_TABLES")) == {
        "account_sync_status",
        "billing_plan_versions",
        "model_promotion_log",
    }
    assert 'op.add_column(\n        "model_promotion_log"' in source
    assert "UPDATE model_promotion_log AS promotion" in source
    assert 'op.alter_column("model_promotion_log", "tenant_id", nullable=False)' in source
    assert "uq_model_versions_id_tenant_id" in source
    assert "fk_model_promotion_log_model_tenant" in source
    assert '["model_version_id", "tenant_id"]' in source
    assert '["id", "tenant_id"]' in source
    assert "MIGRATION_REVIEW_REQUIRED" in source
    assert "tenant_id::text = current_setting('app.tenant_id', true)" in source
    assert "tenant_id IS NULL OR" not in source
    assert "CREATE POLICY global_plan_read_policy ON billing_plan_versions" in source
    assert "FOR SELECT" in source
