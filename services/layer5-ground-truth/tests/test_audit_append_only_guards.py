from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def test_append_only_migration_has_update_delete_insert_guards() -> None:
    migration = SERVICE_ROOT / "src/layer5_ground_truth/migrations/versions/010_enforce_append_only_audit_events.py"
    source = migration.read_text()

    assert "BEFORE UPDATE ON validation_events" in source
    assert "BEFORE DELETE ON validation_events" in source
    assert "BEFORE INSERT ON validation_events" in source
    assert "current_user NOT IN ('system_role', 'admin_role')" in source


def test_audit_write_health_endpoint_exists() -> None:
    source = (SERVICE_ROOT / "src/layer5_ground_truth/api/main.py").read_text()
    assert '@app.get("/health/audit-writes"' in source
    assert '"audit_write_failures_total"' in source
