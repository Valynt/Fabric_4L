#!/usr/bin/env python3
"""CI gate: ensure Layer 5 migrations use the correct RLS GUC.

Scans all Layer 5 Alembic migration files for the legacy/wrong RLS GUC
``app.current_tenant`` and fails if any are found. The runtime and all other
migrations use ``app.tenant_id``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"
FORBIDDEN = ("app.current_tenant",)


def main() -> int:
    """Scan migration files for forbidden RLS GUC strings."""
    failures: list[str] = []
    for path in sorted(MIGRATIONS.glob("*.py")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN:
            if forbidden in text:
                failures.append(f"{path}: contains forbidden RLS GUC {forbidden!r}")

    if failures:
        print("Layer 5 RLS GUC consistency check failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print("Layer 5 RLS GUC consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
