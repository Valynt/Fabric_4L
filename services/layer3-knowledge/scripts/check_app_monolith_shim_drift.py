#!/usr/bin/env python3
"""Verify that app_monolith.py has been fully removed (ARCH-L3-011 cutover).

Sprint 3 completed the migration of all endpoints from app_monolith.py into
bounded domain routers under api/routes/. This script asserts the file is
absent so CI catches any accidental re-introduction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assert app_monolith.py is absent after ARCH-L3-011 cutover."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root directory (default: auto-detected)",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root
    monolith_path = (
        repo_root / "services" / "layer3-knowledge" / "src" / "api" / "app_monolith.py"
    )

    if monolith_path.exists():
        print(
            f"ERROR: {monolith_path} still exists. "
            "app_monolith.py was deleted in Sprint 3 (ARCH-L3-011). "
            "Remove it and ensure all endpoints are registered via api/routes/ domain routers.",
            file=sys.stderr,
        )
        return 1

    print("OK: app_monolith.py is absent — ARCH-L3-011 cutover verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
