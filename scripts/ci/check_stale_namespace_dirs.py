#!/usr/bin/env python3
"""Guard that deleted legacy namespace directories are not reintroduced.

Per ADR-027, the following directories were removed and must not exist:
  - value_fabric/
  - value_fabric/layer1/
  - value_fabric/layer2/
  - value_fabric/layer3/
  - value_fabric/layer4/
  - value_fabric/layer5/
  - value_fabric/layer6/
  - value_fabric/layer1_ingestion/
  - value_fabric/layer3_knowledge/
  - value_fabric/layer2_extraction/
  - value_fabric/layer6_benchmarks/

Run as a CI step or locally:

    python scripts/ci/check_stale_namespace_dirs.py

Exit 0 when clean, 1 when violations found.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# These directories must not exist at all (fully deleted per ADR-027).
DELETED_DIRS: tuple[str, ...] = (
    "value_fabric",
    "value_fabric/layer1_ingestion",
    "value_fabric/layer3_knowledge",
    "value_fabric/layer2_extraction",
    "value_fabric/layer6_benchmarks",
    "value_fabric/layer1",
    "value_fabric/layer2",
    "value_fabric/layer3",
    "value_fabric/layer4",
    "value_fabric/layer5",
    "value_fabric/layer6",
)


def main() -> int:
    violations: list[str] = []

    # Check deleted directories are gone.
    deleted_root_seen = False
    for rel in DELETED_DIRS:
        path = REPO_ROOT / rel
        if path.exists():
            if deleted_root_seen and rel.startswith("value_fabric/"):
                continue
            contents = list(path.iterdir())
            violations.append(
                f"DELETED dir reintroduced: {rel}/ ({len(contents)} item(s))"
            )
            if rel == "value_fabric":
                deleted_root_seen = True

    if violations:
        print("Stale namespace directory violations found:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("Stale namespace directory check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
