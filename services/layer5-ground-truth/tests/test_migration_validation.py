"""
Tests for migration validation.

Validates that the new governance migrations are properly structured.
"""

from pathlib import Path


def test_migration_010_has_triggers_and_rls():
    """Migration 010 should have triggers and RLS policies."""
    migration = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/010_harden_validation_event_immutability.py"
    )
    source = migration.read_text()

    assert "BEFORE UPDATE ON validation_events" in source
    assert "BEFORE DELETE ON validation_events" in source
    assert "BEFORE UPDATE ON maturity_history" in source
    assert "BEFORE DELETE ON maturity_history" in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "CREATE POLICY" in source


def test_migration_011_adds_approval_workflow_tables():
    """Migration 011 should add approval workflow tables."""
    migration = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/011_add_approval_workflow.py"
    )
    source = migration.read_text()

    assert "approval_requests" in source
    assert "approval_decisions" in source
    assert "approval_workflows" in source
    assert "FOREIGN KEY" in source


def test_migration_012_adds_governance_entities():
    """Migration 012 should add formula, benchmark, and policy tables."""
    migration = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/012_add_governance_entities.py"
    )
    source = migration.read_text()

    assert "formulas" in source
    assert "formula_versions" in source
    assert "formula_parameters" in source
    assert "benchmark_datasets" in source
    assert "benchmark_versions" in source
    assert "benchmark_scopes" in source
    assert "policies" in source
    assert "policy_versions" in source
    assert "policy_rules" in source
    assert "policy_applications" in source


def test_migration_013_adds_assumption_registry():
    """Migration 013 should add assumption registry tables."""
    migration = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/013_add_assumption_registry.py"
    )
    source = migration.read_text()

    assert "assumptions" in source
    assert "assumption_evidence" in source
    assert "assumption_reviews" in source


def test_migration_014_adds_value_realization_ledger():
    """Migration 014 should add value realization ledger tables."""
    migration = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/014_add_value_realization_ledger.py"
    )
    source = migration.read_text()

    assert "value_realization_entries" in source
    assert "value_realization_updates" in source


def test_all_migrations_have_downgrade():
    """All migrations should have downgrade functions."""
    migration_dir = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"
    )
    migration_files = [
        "010_harden_validation_event_immutability.py",
        "011_add_approval_workflow.py",
        "012_add_governance_entities.py",
        "013_add_assumption_registry.py",
        "014_add_value_realization_ledger.py",
    ]

    for migration_file in migration_files:
        migration_path = migration_dir / migration_file
        if migration_path.exists():
            source = migration_path.read_text()
            assert "def downgrade()" in source, f"{migration_file} missing downgrade function"


def test_migration_sequence_is_correct():
    """Migrations should have correct revision sequence."""
    migrations = {
        "010_harden_validation_event_immutability.py": "009_align_truth_lifecycle_states",
        "011_add_approval_workflow.py": "010_harden_validation_event_immutability",
        "012_add_governance_entities.py": "011_add_approval_workflow",
        "013_add_assumption_registry.py": "012_add_governance_entities",
        "014_add_value_realization_ledger.py": "013_add_assumption_registry",
    }

    migration_dir = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"
    )

    for migration_file, expected_down_revision in migrations.items():
        migration_path = migration_dir / migration_file
        if migration_path.exists():
            source = migration_path.read_text()
            assert f'down_revision = "{expected_down_revision}"' in source, (
                f"{migration_file} has incorrect down_revision"
            )


def test_migrations_use_postgresql_uuid():
    """Migrations should use PostgreSQL UUID type."""
    migration_dir = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"
    )
    migration_files = [
        "011_add_approval_workflow.py",
        "012_add_governance_entities.py",
        "013_add_assumption_registry.py",
        "014_add_value_realization_ledger.py",
    ]

    for migration_file in migration_files:
        migration_path = migration_dir / migration_file
        if migration_path.exists():
            source = migration_path.read_text()
            assert "postgresql.UUID(as_uuid=True)" in source, (
                f"{migration_file} should use PostgreSQL UUID type"
            )


def test_migrations_have_tenant_id_indexes():
    """Governance tables should have tenant_id indexes."""
    migration = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/012_add_governance_entities.py"
    )
    source = migration.read_text()

    # Check for tenant_id indexes in key tables
    assert "tenant_id" in source
    assert "index=True" in source


def test_migrations_have_cascade_delete():
    """Foreign keys should have CASCADE delete for proper cleanup."""
    migration = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/012_add_governance_entities.py"
    )
    source = migration.read_text()

    assert 'ondelete="CASCADE"' in source
