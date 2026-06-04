from __future__ import annotations

import json
from pathlib import Path

from scripts.ci import migration_status_report as report


def _write_revision(path: Path, revision: str, down_revision: str | None) -> None:
    parent = "None" if down_revision is None else repr(down_revision)
    path.write_text(
        f"revision = {revision!r}\ndown_revision = {parent}\nbranch_labels = None\ndepends_on = None\n",
        encoding="utf-8",
    )


def _configure_service(monkeypatch, tmp_path: Path) -> report.MigrationService:
    versions_dir = tmp_path / "svc" / "migrations" / "versions"
    versions_dir.mkdir(parents=True)
    service = report.MigrationService(
        name="svc",
        service_dir=Path("svc"),
        config_path=Path("alembic.ini"),
        versions_dir=Path("migrations/versions"),
        metadata_module="svc.models",
        default_database="valuefabric",
    )
    monkeypatch.setattr(report, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(report, "ALEMBIC_SERVICES", (service,))
    monkeypatch.setattr(report, "FILE_MANAGED_SERVICES", ())
    monkeypatch.setattr(report, "rollback_policy_status", lambda: {"status": "pass", "returncode": 0, "stdout": "", "stderr": ""})
    monkeypatch.setattr(report, "compare_metadata", lambda service, database_url: ([], None))
    monkeypatch.setattr(report, "validate_tenant_rls", lambda database_url: ({"tenant_scoped_tables": [], "policy_count": 0}, []))
    return service


def test_check_passes_when_database_is_at_head(monkeypatch, tmp_path: Path) -> None:
    _configure_service(monkeypatch, tmp_path)
    versions_dir = tmp_path / "svc" / "migrations" / "versions"
    _write_revision(versions_dir / "001_base.py", "base", None)
    _write_revision(versions_dir / "002_head.py", "head", "base")
    monkeypatch.setattr(report, "read_db_revision", lambda database_url: ("head", None))

    result = report.build_report(mode="check", database_url="postgresql://example/valuefabric")

    assert result["status"] == "pass"
    assert result["services"][0]["current_db_revision"] == "head"
    assert result["services"][0]["pending_migrations"] == []
    assert result["failures"] == []


def test_pending_migrations_are_listed(monkeypatch, tmp_path: Path) -> None:
    _configure_service(monkeypatch, tmp_path)
    versions_dir = tmp_path / "svc" / "migrations" / "versions"
    _write_revision(versions_dir / "001_base.py", "base", None)
    _write_revision(versions_dir / "002_head.py", "head", "base")
    monkeypatch.setattr(report, "read_db_revision", lambda database_url: ("base", None))

    result = report.build_report(mode="status", database_url="postgresql://example/valuefabric")

    assert result["services"][0]["pending_migrations"] == ["head"]
    assert result["services"][0]["applied_migration_history"] == ["base"]


def test_unknown_database_revision_fails_check(monkeypatch, tmp_path: Path) -> None:
    _configure_service(monkeypatch, tmp_path)
    versions_dir = tmp_path / "svc" / "migrations" / "versions"
    _write_revision(versions_dir / "001_base.py", "base", None)
    monkeypatch.setattr(report, "read_db_revision", lambda database_url: ("missing", None))

    result = report.build_report(mode="check", database_url="postgresql://example/valuefabric")

    assert result["status"] == "fail"
    assert result["services"][0]["unknown_db_revision"] is True
    assert any("not present in migration files" in failure for failure in result["failures"])


def test_metadata_drift_fails_check(monkeypatch, tmp_path: Path) -> None:
    _configure_service(monkeypatch, tmp_path)
    versions_dir = tmp_path / "svc" / "migrations" / "versions"
    _write_revision(versions_dir / "001_base.py", "base", None)
    monkeypatch.setattr(report, "read_db_revision", lambda database_url: ("base", None))
    monkeypatch.setattr(report, "compare_metadata", lambda service, database_url: (["add_table drift"], None))

    result = report.build_report(mode="check", database_url="postgresql://example/valuefabric")

    assert result["status"] == "fail"
    assert result["services"][0]["metadata_drift"] == ["add_table drift"]
    assert any("metadata/schema drift detected" in failure for failure in result["failures"])


def test_missing_rollback_metadata_fails_check(monkeypatch, tmp_path: Path) -> None:
    _configure_service(monkeypatch, tmp_path)
    versions_dir = tmp_path / "svc" / "migrations" / "versions"
    _write_revision(versions_dir / "001_base.py", "base", None)
    monkeypatch.setattr(report, "read_db_revision", lambda database_url: ("base", None))
    monkeypatch.setattr(
        report,
        "rollback_policy_status",
        lambda: {"status": "fail", "returncode": 1, "stdout": "", "stderr": "rollback missing"},
    )

    result = report.build_report(mode="check", database_url="postgresql://example/valuefabric")

    assert result["status"] == "fail"
    assert "rollback metadata policy failed" in result["failures"]


def test_tenant_rls_failure_fails_check(monkeypatch, tmp_path: Path) -> None:
    _configure_service(monkeypatch, tmp_path)
    versions_dir = tmp_path / "svc" / "migrations" / "versions"
    _write_revision(versions_dir / "001_base.py", "base", None)
    monkeypatch.setattr(report, "read_db_revision", lambda database_url: ("base", None))
    monkeypatch.setattr(
        report,
        "validate_tenant_rls",
        lambda database_url: (
            {"tenant_scoped_tables": [{"table": "accounts"}], "policy_count": 0},
            ["accounts: tenant-scoped table does not have RLS enabled"],
        ),
    )

    result = report.build_report(mode="check", database_url="postgresql://example/valuefabric")

    assert result["status"] == "fail"
    assert any("tenant-scoped table does not have RLS enabled" in failure for failure in result["failures"])


def test_status_mode_writes_artifacts_without_mutating_database(monkeypatch, tmp_path: Path) -> None:
    _configure_service(monkeypatch, tmp_path)
    versions_dir = tmp_path / "svc" / "migrations" / "versions"
    _write_revision(versions_dir / "001_base.py", "base", None)
    monkeypatch.setattr(report, "read_db_revision", lambda database_url: ("base", None))

    exit_code = report.main(
        [
            "--mode",
            "status",
            "--database-url",
            "postgresql://example/valuefabric",
            "--output-dir",
            str(tmp_path / "artifacts"),
        ]
    )

    assert exit_code == 0
    payload = json.loads((tmp_path / "artifacts" / "migration-status.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "artifacts" / "migration-status.md").read_text(encoding="utf-8")
    assert payload["read_only"] is True
    assert "Database Migration Status" in markdown
    assert "upgrade" not in markdown.lower()
    assert "downgrade" not in markdown.lower()
