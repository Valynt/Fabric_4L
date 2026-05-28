from __future__ import annotations

"""Smoke/integration checks for Layer 5 migration-to-runtime schema alignment.

These tests fail closed on schema drift that would break tenant-scoped queries
or degrade expected query plans on high-traffic list/summary/evaluation paths.
"""


from pathlib import Path

from layer5_ground_truth.models.model_registry import (
    ModelDeployment,
    ModelEvaluation,
    ModelVersion,
)
from layer5_ground_truth.models.truth_object import TruthObject, TruthSource, ValidationEvent

VERSIONS_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "layer5_ground_truth"
    / "migrations"
    / "versions"
)


HIGH_TRAFFIC_INDEXES: dict[str, set[str]] = {
    "truth_objects": {
        "ix_truth_objects_tenant_status",
        "ix_truth_objects_active",
        "ix_truth_objects_tenant_claim_type",
    },
    "validation_events": {
        "ix_validation_events_tenant_status",
    },
    "model_versions": {
        "ix_model_versions_tenant_provider_name",
        "ix_model_versions_tenant_default",
    },
    "model_evaluations": {
        "ix_model_evaluations_tenant_benchmark",
        "ix_model_evaluations_tenant_model",
    },
    "model_deployments": {
        "ix_model_deployments_tenant_env_default",
        "ix_model_deployments_tenant_env_status",
    },
    "truth_sources": {
        "ix_truth_sources_tenant_type",
    },
}


def _table_index_names(model: type) -> set[str]:
    return {index.name for index in model.__table__.indexes if index.name}


def _migration_text() -> str:
    migration_chunks: list[str] = []
    for migration_file in sorted(VERSIONS_DIR.glob("*.py")):
        if migration_file.name.startswith("__"):
            continue
        migration_chunks.append(migration_file.read_text(encoding="utf-8"))
    return "\n".join(migration_chunks)


def test_runtime_tables_use_tenant_id_and_not_organization_id() -> None:
    """Runtime SQLAlchemy schema must reflect post-migration tenant naming."""
    for model in [
        TruthObject,
        TruthSource,
        ValidationEvent,
        ModelVersion,
        ModelDeployment,
        ModelEvaluation,
    ]:
        column_names = {column.name for column in model.__table__.columns}
        assert "tenant_id" in column_names, f"{model.__name__} missing tenant_id"
        assert "organization_id" not in column_names, (
            f"{model.__name__} still has legacy organization_id"
        )


def test_high_traffic_indexes_exist_in_runtime_metadata() -> None:
    """List/summary/evaluation query paths require specific composite indexes."""
    model_by_table = {
        "truth_objects": TruthObject,
        "truth_sources": TruthSource,
        "validation_events": ValidationEvent,
        "model_versions": ModelVersion,
        "model_deployments": ModelDeployment,
        "model_evaluations": ModelEvaluation,
    }

    for table_name, expected_indexes in HIGH_TRAFFIC_INDEXES.items():
        runtime_indexes = _table_index_names(model_by_table[table_name])
        missing = expected_indexes - runtime_indexes
        assert not missing, f"{table_name} missing runtime indexes: {sorted(missing)}"


def test_migrations_encode_tenant_id_and_required_indexes() -> None:
    """Migrations must carry tenant_id evolution and create required indexes."""
    all_migrations = _migration_text()

    # Critical migration guards for legacy organization_id -> tenant_id evolution.
    assert (VERSIONS_DIR / "004_rename_org_to_tenant.py").exists()
    assert "new_column_name='tenant_id'" in all_migrations

    # Every required high-traffic index must have migration coverage.
    # Some legacy truth_* index names are carried forward from org naming.
    index_aliases = {
        "ix_truth_objects_tenant_status": {"ix_truth_objects_tenant_status", "ix_truth_objects_org_status"},
        "ix_truth_sources_tenant_type": {"ix_truth_sources_tenant_type", "ix_truth_sources_org_type"},
    }

    for expected_index in sorted({idx for indexes in HIGH_TRAFFIC_INDEXES.values() for idx in indexes}):
        acceptable_names = index_aliases.get(expected_index, {expected_index})
        assert any(name in all_migrations for name in acceptable_names), (
            f"Missing migration coverage for required index: {expected_index}"
        )


def test_tenant_scoped_query_predicates_match_indexed_paths() -> None:
    """Fail closed if service query predicates drift from tenant-indexed patterns."""
    truth_service = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "layer5_ground_truth"
        / "services"
        / "truth_service.py"
    ).read_text(encoding="utf-8")
    freshness_service = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "layer5_ground_truth"
        / "services"
        / "freshness_monitor.py"
    ).read_text(encoding="utf-8")

    # High-traffic list/summary paths must remain tenant-scoped.
    assert "TruthObject.tenant_id == tenant_id" in truth_service
    assert "TruthObject.status == status.value" in truth_service
    assert "TruthObject.claim_type == claim_type.value" in truth_service

    # Freshness list/summary/evaluation-adjacent monitoring paths must stay scoped.
    assert "TruthObject.tenant_id == tenant_id" in freshness_service
    assert "TruthObject.deleted_at.is_(None)" in freshness_service
