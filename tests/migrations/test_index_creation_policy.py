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


RAW_CREATE_INDEX = re.compile(r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b", re.IGNORECASE)


def _migration_files() -> list[Path]:
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


def test_large_table_raw_index_creation_is_idempotent_or_non_blocking() -> None:
    failures: list[str] = []

    for path in _migration_files():
        source = path.read_text(encoding="utf-8", errors="ignore")
        if "LARGE_TABLE_MIGRATION" not in source and "large table" not in source.lower():
            continue
        for line_no, line in enumerate(source.splitlines(), start=1):
            if line.lstrip().startswith(("#", "--")):
                continue
            if not RAW_CREATE_INDEX.search(line):
                continue
            upper = line.upper()
            if "IF NOT EXISTS" in upper or "CONCURRENTLY" in upper:
                continue
            failures.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")

    assert not failures, "Large-table raw CREATE INDEX statements must use IF NOT EXISTS or CONCURRENTLY: " + "; ".join(failures)


def test_index_policy_is_exercised_by_existing_migrations() -> None:
    indexed_files = [
        path
        for path in _migration_files()
        if "create_index" in path.read_text(encoding="utf-8", errors="ignore")
        or RAW_CREATE_INDEX.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]

    assert indexed_files, "Expected migration index coverage so index policy tests remain meaningful"
