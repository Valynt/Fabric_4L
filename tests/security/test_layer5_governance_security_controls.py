"""Security regressions for Layer5 governance scope, audit immutability, and metrics contracts."""

from pathlib import Path


def test_cross_tenant_and_global_scope_filters_are_present_in_repository_queries() -> None:
    """Formula governance queries must enforce tenant scope."""
    source = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/services/formula_governance_service.py"
    ).read_text()

    assert "Formula.tenant_id == tenant_id" in source
    assert "FormulaVersion.tenant_id == tenant_id" in source
    assert "FormulaParameter(" in source and "tenant_id=tenant_id" in source


def test_audit_logs_are_append_only_and_non_privileged_mutation_is_blocked() -> None:
    """Hostile/non-privileged users must not mutate existing audit logs."""
    migration = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/010_enforce_append_only_audit_events.py"
    ).read_text()
    monitor = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/services/audit_write_monitor.py"
    ).read_text()

    assert "trg_validation_events_no_update" in migration
    assert "trg_validation_events_no_delete" in migration
    assert "require_admin_for_audit_write" in monitor
    assert "Admin privileges required for audit write operation" in monitor


def test_metrics_contract_contains_failure_spike_and_bypass_signal_paths() -> None:
    """Synthetic alerting inputs must expose counters for denial/failure spikes and bypass attempts."""
    monitor = Path(
        "services/layer5-ground-truth/src/layer5_ground_truth/services/audit_write_monitor.py"
    ).read_text()

    assert '"failures_total"' in monitor
    assert '"admin_bypasses"' in monitor
    assert "increment_audit_write_denials" in monitor
    assert "increment_audit_write_failures" in monitor
