from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_ROOTS = (
    Path("services/layer1-ingestion/migrations/versions"),
    Path("services/layer2-extraction/migrations/versions"),
    Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
    Path("services/layer4-agents/migrations/versions"),
    Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
    Path("services/api/migrations/versions"),
)
DESTRUCTIVE_UPGRADE_PATTERNS = (
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
    re.compile(r"\bdrop_table\s*\(", re.IGNORECASE),
    re.compile(r"\bdrop_column\s*\(", re.IGNORECASE),
)


def _migration_files() -> list[Path]:
    files: list[Path] = []
    for root in MIGRATION_ROOTS:
        files.extend(sorted((REPO_ROOT / root).glob("*.py")))
    return [path for path in files if not path.name.startswith("__")]


def _upgrade_body(source: str) -> str:
    start = source.find("def upgrade")
    if start == -1:
        return ""
    end = source.find("def downgrade", start)
    return source[start:] if end == -1 else source[start:end]


def test_destructive_rollback_policy_script_passes() -> None:
    result = subprocess.run(
        ["python", "scripts/ci/check_migration_rollback_policy.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "rollback policy" in result.stdout.lower()


def test_destructive_upgrade_migrations_require_runtime_guard_or_explicit_approval() -> None:
    failures: list[str] = []

    for path in _migration_files():
        source = path.read_text(encoding="utf-8")
        upgrade = _upgrade_body(source)
        if not any(pattern.search(upgrade) for pattern in DESTRUCTIVE_UPGRADE_PATTERNS):
            continue
        if not any(
            marker in source
            for marker in (
                "DESTRUCTIVE_ACK_VALUE",
                "PRODUCTION_LIKE_ENVIRONMENTS",
                "MIGRATION_REVIEW_REQUIRED",
                "explicit production approval",
            )
        ):
            failures.append(str(path.relative_to(REPO_ROOT)))

    assert not failures, "Destructive upgrade migrations lack approval/guard evidence: " + ", ".join(failures)


def test_static_migration_safety_scan_publishes_machine_readable_findings() -> None:
    result = subprocess.run(
        ["python", "scripts/ci/check_migration_safety.py", "--json", "--use-baseline"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().startswith("[")
