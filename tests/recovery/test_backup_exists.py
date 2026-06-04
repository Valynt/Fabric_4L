from __future__ import annotations

from pathlib import Path

from .conftest import ROOT, assert_contains_all, read_text


def test_backup_cronjobs_and_scripts_exist() -> None:
    required_paths = [
        "scripts/ops/postgres_backup.py",
        "scripts/ops/test_postgres_backup_restore.sh",
        "k8s/base/postgres-backup-cronjob.yaml",
        "k8s/base/neo4j-backup-cronjob.yaml",
        "docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md",
        "docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md",
    ]
    missing = [path for path in required_paths if not (ROOT / path).exists()]
    assert not missing, f"missing backup/restore source-of-truth assets: {missing}"


def test_postgres_backup_cronjob_has_restore_readiness_controls() -> None:
    cronjob = read_text("k8s/base/postgres-backup-cronjob.yaml")
    assert_contains_all(
        cronjob,
        [
            "kind: CronJob",
            "name: postgres-backup",
            'schedule: "0 2 * * *"',
            "concurrencyPolicy: Forbid",
            "ENABLE_WALG_BACKUP",
            "restore validation",
            "restore evidence",
            "postgres-secret",
            "wal-g-config",
        ],
        label="postgres backup CronJob",
    )


def test_neo4j_backup_cronjob_has_schedule_and_secret_reference() -> None:
    cronjob = read_text("k8s/base/neo4j-backup-cronjob.yaml")
    assert_contains_all(
        cronjob,
        [
            "kind: CronJob",
            "name: neo4j-backup",
            'schedule: "0 3 * * *"',
            "concurrencyPolicy: Forbid",
            "neo4j-admin database dump",
            "neo4j-credentials",
        ],
        label="neo4j backup CronJob",
    )


def test_rpo_rto_and_runbooks_are_documented() -> None:
    dr_runbook = read_text("docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md")
    postgres_runbook = read_text("docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md")
    assert_contains_all(
        dr_runbook,
        [
            "RTO/RPO Targets",
            "1 hour",
            "4 hours",
            "8 hours",
            "Partial Tenant Restore",
            "Full Environment Restore",
            "CI / Scheduled Restore Verification Evidence",
        ],
        label="DR runbook",
    )
    assert_contains_all(
        postgres_runbook,
        [
            "RTO / RPO Targets",
            "Managed PostgreSQL",
            "point-in-time restore",
            "artifacts/postgres-backup-restore/",
        ],
        label="PostgreSQL backup runbook",
    )


def test_restore_verification_workflow_exists() -> None:
    workflow = Path(".github/workflows/restore-verification.yml")
    assert (ROOT / workflow).exists(), "restore verification workflow must publish scheduled evidence"
