from __future__ import annotations

import json

from .conftest import ROOT, assert_contains_all, read_text


def test_restore_dry_run_evidence_contract(restore_dry_run_evidence: dict) -> None:
    evidence = restore_dry_run_evidence
    assert evidence["schema_version"] == "recovery-restore-dry-run.v1"
    assert evidence["status"] == "pass"
    assert evidence["environment_guard"]["mode"] == "dry_run"
    assert evidence["environment_guard"]["production_mutation_allowed"] is False
    assert evidence["restore_drill"]["command"] == "bash scripts/ops/test_postgres_backup_restore.sh"
    assert evidence["restore_drill"]["safe_target"] == "isolated source and restore PostgreSQL containers"
    assert evidence["missing_assets"] == []


def test_package_ops_commands_are_wired() -> None:
    package_json = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package_json["scripts"]
    assert scripts["ops:backup:verify"] == (
        "python -m pytest tests/recovery/test_backup_exists.py tests/recovery/test_restore_smoke.py"
    )
    assert scripts["ops:restore:dry-run"] == (
        "python scripts/ops/restore_dry_run.py --output-dir artifacts/recovery"
    )


def test_restore_drill_script_uses_isolated_non_production_targets() -> None:
    drill = read_text("scripts/ops/test_postgres_backup_restore.sh")
    assert_contains_all(
        drill,
        [
            "isolated source and restore PostgreSQL containers",
            "vf-pg-backup-source",
            "vf-pg-backup-restore",
            "POSTGRES_BACKUP_EVIDENCE_DIR",
            "artifacts/postgres-backup-restore",
            "source-checksums.txt",
            "restored-checksums.txt",
            "tenant_count_verified",
            "docker run --rm -i --network",
        ],
        label="PostgreSQL restore drill",
    )


def test_postgres_restore_feeds_decompressed_sql_to_psql() -> None:
    backup_script = read_text("scripts/ops/postgres_backup.py")
    assert_contains_all(
        backup_script,
        [
            "with gzip.open(dump_path, \"rb\") as gz_fh:",
            "input=gz_fh.read()",
            "psql restore failed",
        ],
        label="PostgreSQL restore stream handling",
    )
