"""Contract test: Layer 5 uses tenant_id consistently across models, auth, and migrations.

This test enforces that the organization_id → tenant_id migration (004) is
complete and that no code path or RLS policy reverts to the old column name.
"""

import dataclasses
import inspect
from pathlib import Path

import pytest

from layer5_ground_truth import models
from layer5_ground_truth.api.auth import TokenClaims


class TestTenantIdConsistency:
    """Verify tenant_id is the canonical multi-tenancy column in Layer 5."""

    def test_sqlalchemy_models_use_tenant_id(self) -> None:
        """Every tenant-scoped model must have tenant_id, not organization_id."""
        tenant_scoped_models = []
        for name, cls in inspect.getmembers(models, inspect.isclass):
            if not hasattr(cls, "__table__"):
                continue
            column_names = {c.name for c in cls.__table__.columns}
            # Only check models that have a tenant-scoped column
            if "tenant_id" in column_names or "organization_id" in column_names:
                tenant_scoped_models.append((name, column_names))

        assert tenant_scoped_models, "No tenant-scoped models found"

        for name, column_names in tenant_scoped_models:
            assert (
                "organization_id" not in column_names
            ), f"{name} still has organization_id column — migration 004 incomplete"
            assert (
                "tenant_id" in column_names
            ), f"{name} missing tenant_id column — migration 004 incomplete"

    def test_auth_token_claims_use_tenant_id(self) -> None:
        """TokenClaims must expose tenant_id, not organization_id."""
        fields = {f.name for f in dataclasses.fields(TokenClaims)}
        assert "tenant_id" in fields, "TokenClaims missing tenant_id field"
        assert "organization_id" not in fields, "TokenClaims still has organization_id field"

    def test_migrations_do_not_reference_organization_id_in_policies(self) -> None:
        """No migration file may create RLS policies referencing organization_id.

        Migration 002 originally used organization_id before migration 004 renamed
        the column to tenant_id, and migration 006 fixes those policies. This test
        prevents regressions in migrations that run after the rename.
        """
        migrations_dir = (
            Path(__file__).parent.parent
            / "src"
            / "layer5_ground_truth"
            / "migrations"
            / "versions"
        )
        assert migrations_dir.exists(), f"Migrations directory not found: {migrations_dir}"

        for migration_file in sorted(migrations_dir.glob("*.py")):
            if migration_file.name.startswith("__"):
                continue
            content = migration_file.read_text(encoding="utf-8")
            # Allow organization_id in the rename migration itself (004)
            if "rename_org_to_tenant" in migration_file.name:
                continue
            # Migration 002 predates the rename and is fixed by migration 006
            if migration_file.name == "002_add_rls_policies.py":
                continue
            # Any other migration must not create policies with organization_id
            if "organization_id" in content and "CREATE POLICY" in content:
                pytest.fail(
                    f"{migration_file.name} creates a policy referencing organization_id"
                )

    def test_migration_006_exists(self) -> None:
        """Migration 006 must exist to fix RLS policies after 004 rename."""
        migrations_dir = (
            Path(__file__).parent.parent
            / "src"
            / "layer5_ground_truth"
            / "migrations"
            / "versions"
        )
        fix_migration = migrations_dir / "006_fix_rls_org_to_tenant.py"
        assert fix_migration.exists(), (
            "Migration 006_fix_rls_org_to_tenant.py missing — "
            "RLS policies from 002 are broken after 004 rename"
        )
