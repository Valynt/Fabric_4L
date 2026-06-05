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
            "postgres-patroni-credentials",
            "wal-g-config",
            "aws-backup-credentials",
        ],
        label="postgres backup CronJob",
    )


def test_walg_base_manifests_do_not_commit_environment_placeholders() -> None:
    paths = [
        "k8s/base/wal-g-config.yaml",
        "k8s/base/postgres-patroni.yaml",
        "k8s/base/postgres-backup-cronjob.yaml",
    ]
    forbidden = ["REPLACE_ENV", "ACCOUNT_ID", "fabric4l-backups-REPLACE_ENV"]
    offenders: dict[str, list[str]] = {}
    for path in paths:
        text = read_text(path)
        matches = [token for token in forbidden if token in text]
        if matches:
            offenders[path] = matches
    assert not offenders, f"WAL-G base manifests contain placeholders: {offenders}"


def test_walg_destination_is_external_secret_managed() -> None:
    external_secret = read_text("k8s/external-secrets/wal-g-backup-secrets.yaml")
    config = read_text("k8s/base/wal-g-config.yaml")
    patroni = read_text("k8s/base/postgres-patroni.yaml")
    cronjob = read_text("k8s/base/postgres-backup-cronjob.yaml")

    assert_contains_all(
        external_secret,
        [
            "kind: ExternalSecret",
            "name: wal-g-backup-secrets",
            "name: aws-backup-credentials",
            "WALG_S3_PREFIX",
            "AWS_REGION",
            "role-arn",
            "value-fabric/infrastructure/wal-g",
        ],
        label="WAL-G ExternalSecret",
    )
    assert "WALG_S3_PREFIX" not in config
    assert "AWS_REGION" not in config
    assert "secretKeyRef:" in patroni
    assert "name: aws-backup-credentials" in patroni
    assert "secretRef:" in cronjob
    assert "ENABLE_WALG_BACKUP" in cronjob
    assert 'value: "false"' in cronjob


def test_walg_external_secret_is_wired_into_base_inheriting_env_overlays() -> None:
    overlays = [
        "k8s/envs/prod/kustomization.yaml",
        "k8s/envs/staging/kustomization.yaml",
    ]
    missing: list[str] = []
    for overlay in overlays:
        source = read_text(overlay)
        assert "../../base" in source, f"{overlay} must inherit the base backup CronJob"
        if "../../external-secrets/wal-g-backup-secrets.yaml" not in source:
            missing.append(overlay)
    assert not missing, f"WAL-G ExternalSecret is not wired into overlays: {missing}"


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
    workflow = Path(".github/workflows/dr-drill.yml")
    assert (ROOT / workflow).exists(), "DR drill workflow must publish scheduled restore evidence"
