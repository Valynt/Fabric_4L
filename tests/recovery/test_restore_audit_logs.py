from __future__ import annotations

from .conftest import assert_contains_all, read_text


def test_audit_log_restore_is_part_of_dry_run_evidence(restore_dry_run_evidence: dict) -> None:
    audit_logs = restore_dry_run_evidence["restore_validations"]["audit_logs"]
    assert audit_logs["audit_events_required"] is True
    assert audit_logs["append_only_validation_required"] is True
    assert audit_logs["tenant_scoped_query_validation_required"] is True


def test_audit_log_restore_scope_is_documented_and_tested() -> None:
    runbook = read_text("docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md")
    backend_test = read_text("tests/backend_integrated/test_tenant_isolation_security_persistence.py")
    assert_contains_all(
        runbook,
        [
            "Audit Log Restore",
            "audit_events",
            "append-only",
            "tenant-scoped",
            "hash-chain",
        ],
        label="audit restore runbook",
    )
    assert_contains_all(
        backend_test,
        [
            "test_audit_logs_do_not_leak_foreign_tenant_data",
            "/v1/audit/logs",
        ],
        label="audit tenant isolation test",
    )
