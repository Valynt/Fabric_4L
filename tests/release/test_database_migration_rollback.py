"""Release checks for database migration rollback safety."""

from __future__ import annotations

import subprocess
from pathlib import Path


MIGRATION_ROOTS = [
    Path("services/layer1-ingestion/migrations/versions"),
    Path("services/layer2-extraction/migrations/versions"),
    Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
    Path("services/layer4-agents/migrations/versions"),
    Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
    Path("services/api/migrations/versions"),
]


def test_database_migration_rollback_runbook_documents_strategy() -> None:
    runbook = Path("docs/operations/runbooks/database-migration-rollback.md")
    assert runbook.is_file(), "Database migration rollback runbook is missing"
    text = runbook.read_text(encoding="utf-8").lower()
    for marker in (
        "forward-fix",
        "restore from backup",
        "explicit production approval",
        "unsupported downgrade policy",
        "upgrade to `head`",
        "downgrade -1",
    ):
        assert marker in text, f"Database migration rollback runbook missing {marker!r}"


def test_makefile_exposes_static_and_live_migration_rollback_gates() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    for target in (
        "check-migration-rollback-policy",
        "gate-migration-readiness",
        "gate-database-live",
        "check-migration-postgres-roundtrip",
    ):
        assert f"{target}:" in makefile, f"Makefile missing {target}"


def test_migration_rollback_policy_script_passes_static_check() -> None:
    result = subprocess.run(
        ["python", "scripts/ci/check_migration_rollback_policy.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "rollback policy" in result.stdout.lower()


def test_all_alembic_managed_roots_are_covered() -> None:
    missing = [root for root in MIGRATION_ROOTS if not root.is_dir()]
    assert not missing, f"Missing Alembic migration roots: {missing}"

    policy_script = Path("scripts/ci/check_migration_rollback_policy.py").read_text(encoding="utf-8")
    for root in MIGRATION_ROOTS:
        assert root.as_posix() in policy_script, f"Rollback policy script does not inspect {root}"
