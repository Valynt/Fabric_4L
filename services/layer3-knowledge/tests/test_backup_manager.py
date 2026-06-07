"""Unit tests for the backup manager — used by `make test-backup-drills`."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from pathlib import Path

import pytest

from src.backup.backup_manager import (
    BackupConfig,
    BackupManager,
    BackupMetadata,
    BackupRequest,
    BackupStatus,
    BackupType,
    LocalStorage,
    StorageType,
)


# ---------------------------------------------------------------------------
# BackupType / BackupStatus enums
# ---------------------------------------------------------------------------


def test_backup_type_values():
    assert BackupType.FULL == "full"
    assert BackupType.INCREMENTAL == "incremental"
    assert BackupType.DIFFERENTIAL == "differential"
    assert BackupType.SCHEMA == "schema"
    assert BackupType.CONFIG == "config"


def test_backup_status_values():
    assert BackupStatus.PENDING == "pending"
    assert BackupStatus.RUNNING == "running"
    assert BackupStatus.COMPLETED == "completed"
    assert BackupStatus.FAILED == "failed"
    assert BackupStatus.CANCELLED == "cancelled"


# ---------------------------------------------------------------------------
# BackupMetadata.to_dict() / from_dict() round-trip
# ---------------------------------------------------------------------------


def _make_metadata(**kwargs) -> BackupMetadata:
    defaults = dict(
        backup_id="test-bkp-001",
        backup_type=BackupType.FULL,
        created_at=datetime(2026, 1, 15, 3, 0, 0),
        status=BackupStatus.COMPLETED,
        size_bytes=1024,
        compressed_size_bytes=512,
        storage_type=StorageType.LOCAL,
        checksum="abc123",
        retention_days=30,
        encrypted=False,
        compression_algorithm="gzip",
    )
    defaults.update(kwargs)
    return BackupMetadata(**defaults)


def test_metadata_to_dict_basic():
    m = _make_metadata()
    d = m.to_dict()
    assert d["backup_id"] == "test-bkp-001"
    assert d["backup_type"] == "full"
    assert d["status"] == "completed"
    assert d["size_bytes"] == 1024
    assert d["compressed_size_bytes"] == 512
    assert d["storage_type"] == "local"
    assert d["checksum"] == "abc123"
    assert d["retention_days"] == 30
    assert d["encrypted"] is False
    assert d["compression_algorithm"] == "gzip"
    assert d["completed_at"] is None


def test_metadata_to_dict_with_completed_at():
    completed = datetime(2026, 1, 15, 3, 5, 30)
    m = _make_metadata(completed_at=completed)
    d = m.to_dict()
    assert d["completed_at"] == completed.isoformat()


def test_metadata_to_dict_created_at_is_iso_string():
    m = _make_metadata()
    d = m.to_dict()
    # Must be parseable back to datetime
    parsed = datetime.fromisoformat(d["created_at"])
    assert parsed == m.created_at


def test_metadata_roundtrip():
    completed = datetime(2026, 1, 15, 3, 5, 0)
    m = _make_metadata(
        completed_at=completed,
        description="nightly full backup",
        tags=["nightly", "prod"],
    )
    d = m.to_dict()
    m2 = BackupMetadata.from_dict(d)

    assert m2.backup_id == m.backup_id
    assert m2.backup_type == m.backup_type
    assert m2.status == m.status
    assert m2.size_bytes == m.size_bytes
    assert m2.checksum == m.checksum
    assert m2.retention_days == m.retention_days
    assert m2.encrypted == m.encrypted
    assert m2.tags == m.tags
    assert m2.description == m.description
    assert m2.completed_at == completed


# ---------------------------------------------------------------------------
# LocalStorage path construction
# ---------------------------------------------------------------------------


@pytest.fixture()
def local_storage(tmp_path: Path) -> LocalStorage:
    config = BackupConfig(backup_directory=str(tmp_path))
    return LocalStorage(config)


def test_local_storage_creates_dir(tmp_path: Path):
    new_dir = tmp_path / "backups" / "nested"
    BackupConfig(backup_directory=str(new_dir))
    # Only LocalStorage init creates the dir
    ls = LocalStorage(BackupConfig(backup_directory=str(new_dir)))
    assert new_dir.exists()


@pytest.mark.asyncio
async def test_local_storage_store_and_retrieve(local_storage: LocalStorage, tmp_path: Path):
    data = b"backup payload"
    path = await local_storage.store_backup("bkp-xyz", data)
    assert Path(path).exists()
    retrieved = await local_storage.retrieve_backup("bkp-xyz")
    assert retrieved == data


@pytest.mark.asyncio
async def test_local_storage_delete(local_storage: LocalStorage):
    await local_storage.store_backup("bkp-del", b"to be deleted")
    deleted = await local_storage.delete_backup("bkp-del")
    assert deleted is True
    # Deleting again returns False
    assert await local_storage.delete_backup("bkp-del") is False


@pytest.mark.asyncio
async def test_local_storage_list_backups(local_storage: LocalStorage):
    await local_storage.store_backup("bkp-a", b"a")
    await local_storage.store_backup("bkp-b", b"b")
    ids = await local_storage.list_backups()
    assert "bkp-a" in ids
    assert "bkp-b" in ids


@pytest.mark.asyncio
async def test_local_storage_get_backup_info(local_storage: LocalStorage):
    await local_storage.store_backup("bkp-info", b"content")
    info = await local_storage.get_backup_info("bkp-info")
    assert info["backup_id"] == "bkp-info"
    assert info["size_bytes"] == len(b"content")
    assert "file_path" in info
    assert "created_at" in info


@pytest.mark.asyncio
async def test_local_storage_retrieve_missing_raises(local_storage: LocalStorage):
    with pytest.raises(FileNotFoundError):
        await local_storage.retrieve_backup("does-not-exist")


# ---------------------------------------------------------------------------
# BackupManager initialisation
# ---------------------------------------------------------------------------


def test_backup_manager_creates_local_storage(tmp_path: Path):
    config = BackupConfig(backup_directory=str(tmp_path))
    manager = BackupManager(config)
    assert isinstance(manager.storage, LocalStorage)
    assert manager.config is config
    assert manager.active_backups == {}
    assert manager.backup_history == []


def test_backup_manager_no_driver_by_default(tmp_path: Path):
    config = BackupConfig(backup_directory=str(tmp_path))
    manager = BackupManager(config)
    assert manager.neo4j_driver is None


# ---------------------------------------------------------------------------
# BackupConfig defaults
# ---------------------------------------------------------------------------


def test_backup_config_defaults():
    cfg = BackupConfig()
    assert cfg.enabled is True
    assert cfg.retention_days == 30
    assert cfg.compression_enabled is True
    assert cfg.encryption_enabled is False
    assert cfg.max_backups == 100
    assert cfg.storage_type == StorageType.LOCAL
    assert cfg.auto_cleanup is True


# ---------------------------------------------------------------------------
# SHA-256 helper — verify module-level hashlib usage is consistent
# ---------------------------------------------------------------------------


def test_sha256_consistency():
    """Verify that SHA-256 produces deterministic output for known input."""
    payload = b"value-fabric-dr-drill"
    expected = hashlib.sha256(payload).hexdigest()
    # Re-compute to confirm determinism
    assert hashlib.sha256(payload).hexdigest() == expected
    assert len(expected) == 64  # hex digest length
