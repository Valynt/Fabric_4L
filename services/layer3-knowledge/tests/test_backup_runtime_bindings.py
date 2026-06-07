from src.backup.backup_manager import BackupConfig as ServiceBackupConfig
from src.backup.backup_manager import BackupManager as ServiceBackupManager
from src.backup.backup_manager import LocalStorage as ServiceLocalStorage
from src.backup.backup_manager import BackupConfig, BackupManager, LocalStorage


def test_backup_manager_uses_concrete_storage(tmp_path):
    config = BackupConfig(backup_directory=str(tmp_path))
    manager = BackupManager(config)
    assert isinstance(manager.storage, LocalStorage)


def test_service_backup_forwarder_exports_canonical_symbols():
    assert ServiceBackupConfig is BackupConfig
    assert ServiceBackupManager is BackupManager
    assert ServiceLocalStorage is LocalStorage
