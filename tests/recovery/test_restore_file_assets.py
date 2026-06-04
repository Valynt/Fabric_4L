from __future__ import annotations

from .conftest import assert_contains_all, read_text


def test_object_storage_restore_is_part_of_dry_run_evidence(restore_dry_run_evidence: dict) -> None:
    object_storage = restore_dry_run_evidence["restore_validations"]["object_storage"]
    assert object_storage["file_asset_restore_required"] is True
    assert object_storage["metadata_references_required"] is True
    assert {"S3", "GCS", "MinIO-compatible S3"}.issubset(set(object_storage["storage_backends"]))


def test_file_asset_restore_scope_is_documented() -> None:
    runbook = read_text("docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md")
    compose = read_text("docker-compose.dev.yml")
    assert_contains_all(
        runbook,
        [
            "Object Storage and File Asset Restore",
            "S3",
            "MinIO-compatible",
            "metadata references",
            "files and customer-uploaded assets",
        ],
        label="file asset restore runbook",
    )
    assert_contains_all(
        compose,
        [
            "MinIO S3-compatible object storage",
            "minio",
            "9000",
        ],
        label="local object storage",
    )
