"""Contract checks for retention/deletion implementation artifacts.

These tests avoid runtime service dependencies and validate source-level
retention guarantees referenced by compliance documentation.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
L1_CONFIG = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/shared/config.py"
L1_CLEANUP = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/shared/tasks/cleanup.py"


def test_retention_defaults_declared_in_settings():
    text = L1_CONFIG.read_text()
    assert "retention_days: int = Field(default=30" in text
    assert "audit_log_retention_years: int = Field(default=7" in text


def test_cleanup_task_default_and_delete_semantics_present():
    text = L1_CLEANUP.read_text()
    assert "def cleanup_old_content(days: int = 30," in text
    assert 'RawContent.processing_status != "DELETED"' in text
    assert 'processing_status": "DELETED"' in text
