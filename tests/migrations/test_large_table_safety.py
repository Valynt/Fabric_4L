from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATHS = (
    "services/layer1-ingestion/migrations",
    "services/layer2-extraction/migrations",
    "services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations",
    "services/layer3-knowledge/src/migrations",
    "services/layer4-agents/migrations",
    "services/layer5-ground-truth/src/layer5_ground_truth/migrations",
    "services/layer6-benchmarks/migrations",
    "services/api/migrations",
)


def _all_migration_files() -> list[Path]:
    files: list[Path] = []
    for root in MIGRATION_PATHS:
        base = REPO_ROOT / root
        if base.exists():
            files.extend(
                path
                for path in base.rglob("*")
                if path.is_file() and path.suffix in {".py", ".sql", ".cypher"}
            )
    return sorted(files)


def test_large_table_policy_is_documented_for_migration_authors() -> None:
    readme = (REPO_ROOT / "tests/migrations/README.md").read_text(encoding="utf-8").lower()

    for marker in ("large table", "concurrently", "phased strategy", "expand/contract"):
        assert marker in readme


def test_migrations_marked_large_table_use_non_blocking_or_phased_strategy() -> None:
    failures: list[str] = []
    large_table_marker = re.compile(r"LARGE_TABLE_MIGRATION|large table", re.IGNORECASE)

    for path in _all_migration_files():
        source = path.read_text(encoding="utf-8", errors="ignore")
        if not large_table_marker.search(source):
            continue
        lower = source.lower()
        if "create index" in lower and "concurrently" not in lower and "phased" not in lower:
            failures.append(str(path.relative_to(REPO_ROOT)))
        if "alter table" in lower and "lock timeout" not in lower and "phased" not in lower:
            failures.append(str(path.relative_to(REPO_ROOT)))

    assert not failures, "Large table migrations need non-blocking/phased safety evidence: " + ", ".join(failures)

