from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_package_scripts_expose_migration_idempotency_gate() -> None:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package_json["scripts"]

    assert scripts["db:migrate:test"] == "python scripts/ci/check_migration_drift.py --round-trip"
    assert scripts["db:schema:diff"] == "python scripts/ci/migration_status_report.py --mode check"


def test_live_migration_gate_uses_disposable_databases_and_round_trip() -> None:
    source = (REPO_ROOT / "scripts/ci/check_migration_drift.py").read_text(encoding="utf-8")

    for marker in (
        "CREATE DATABASE",
        "DROP DATABASE IF EXISTS",
        '("upgrade", "head")',
        '("downgrade", "-1")',
        "metadata/schema drift detected",
    ):
        assert marker in source


def test_live_round_trip_validation_runs_when_database_url_is_available() -> None:
    if not os.environ.get("MIGRATION_DRIFT_DATABASE_URL") and not os.environ.get("DB_MIGRATION_DATABASE_URL"):
        return

    result = subprocess.run(
        ["python", "scripts/ci/check_migration_drift.py", "--round-trip"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

