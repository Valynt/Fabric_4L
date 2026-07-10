#!/usr/bin/env python3
"""Validate database readiness governance docs stay wired to static gates."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOC_MARKERS: dict[Path, tuple[str, ...]] = {
    Path("docs/reference/database-runtime-compatibility-matrix.md"): (
        "make gate-database",
        "check-migration-heads",
        "check-migration-entrypoints",
        "scripts/ci/check_migration_runtime_consistency.py",
        "scripts/ci/check_db_bootstrap_conformance.py",
        "scripts/ci/check_db_production_readiness_split.py",
        "gate-database-live",
    ),
    Path("docs/reference/migration-reproducibility-invariants.md"): (
        "Alembic",
        "rollback",
        "reproducibility",
    ),
    Path("docs/operations/runbooks/database-migration-rollback.md"): (
        "explicit production approval",
        "restore from backup",
        "forward-fix",
        "rollback strategy",
    ),
}


def main() -> int:
    errors: list[str] = []
    for rel_path, markers in REQUIRED_DOC_MARKERS.items():
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"missing required database governance doc: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        lower_text = text.lower()
        for marker in markers:
            if marker.lower() not in lower_text:
                errors.append(f"{rel_path}: missing required marker {marker!r}")

    if errors:
        print("Database governance documentation violations:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Database governance documentation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
