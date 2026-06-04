#!/usr/bin/env python3
"""Verify route-map audit artifacts are fresh and consistent with App.tsx."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Allow importing sibling _lib without a package __init__.py
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from _lib import resolve_repo_root  # type: ignore[import-not-found]

APP_REL = Path("apps/web/src/App.tsx")
ROUTE_MAP_REL = Path("apps/web/audit-output/route-map.md")
EXTRACTION_REL = Path("apps/web/audit-output/track-a-route-extraction.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repository root (default: auto-detected)",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve() if args.repo_root else resolve_repo_root()
    app = repo_root / APP_REL
    route_map = repo_root / ROUTE_MAP_REL
    extraction = repo_root / EXTRACTION_REL

    missing = [str(p) for p in (app, route_map, extraction) if not p.exists()]
    if missing:
        print(f"ERROR: missing required files: {', '.join(missing)}")
        return 1

    try:
        summary = json.loads(extraction.read_text(encoding="utf-8")).get("summary", {})
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: failed to parse {EXTRACTION_REL}: {exc}")
        return 1

    expected_total = summary.get("total")
    if not isinstance(expected_total, int):
        print("ERROR: track-a-route-extraction.json missing numeric summary.total")
        return 1

    match = re.search(r"\*\*Total Routes:\*\*\s*(\d+)", route_map.read_text(encoding="utf-8"))
    if not match:
        print('ERROR: route-map.md missing "**Total Routes:** <count>" header')
        return 1

    found_total = int(match.group(1))
    if found_total != expected_total:
        print(
            f"ERROR: route count drift detected: "
            f"route-map={found_total}, extraction={expected_total}"
        )
        return 1

    print(f"OK: route-map freshness and count checks passed (total routes: {expected_total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
