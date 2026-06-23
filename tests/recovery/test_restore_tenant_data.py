from __future__ import annotations

from .conftest import assert_contains_all, read_text


def test_restore_evidence_requires_per_tenant_checksum_comparison(restore_dry_run_evidence: dict) -> None:
    tenant_data = restore_dry_run_evidence["restore_validations"]["tenant_data"]
    assert tenant_data["compare_per_tenant_checksums"] is True
    assert tenant_data["tenant_count_verified"] is True
    assert tenant_data["partial_tenant_restore_required"] is True
    assert tenant_data["source_checksums"].endswith("source-checksums.txt")
    assert tenant_data["restored_checksums"].endswith("restored-checksums.txt")


def test_restore_drill_seeds_multiple_tenants_and_diffs_checksums() -> None:
    drill = read_text("scripts/ops/test_postgres_backup_restore.sh")
    assert_contains_all(
        drill,
        [
            "tenant-a",
            "tenant-b",
            "GROUP BY tenant_id",
            "ORDER BY tenant_id",
            "diff -u",
            "count(DISTINCT tenant_id)",
        ],
        label="tenant restore drill",
    )


def test_partial_tenant_restore_runbook_is_tenant_safe() -> None:
    runbook = read_text("docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md")
    assert_contains_all(
        runbook,
        [
            "Partial Tenant Restore",
            "tenant_id",
            "authenticated tenant context",
            "Do not trust request-body tenant IDs",
            "hostile cross-tenant validation",
            "audit evidence",
        ],
        label="partial tenant restore runbook",
    )
