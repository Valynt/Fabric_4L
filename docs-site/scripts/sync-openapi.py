#!/usr/bin/env python3
"""Sync the public OpenAPI spec into the docs tree before building.

Copies the API gateway specification from the repository's canonical contracts
directory into docs-site/docs/api/openapi/ so the Swagger UI reference renders
against an always-current spec. The destination is gitignored to prevent drift;
this script is the single source for refreshing it (locally and in CI).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

DOCS_SITE = Path(__file__).resolve().parents[1]
REPO_ROOT = DOCS_SITE.parent
SOURCE = REPO_ROOT / "contracts" / "openapi" / "fabric-4l-api.json"
DEST = DOCS_SITE / "docs" / "api" / "openapi" / "fabric-4l-api.json"


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: source spec not found: {SOURCE}", file=sys.stderr)
        return 1
    DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(SOURCE, DEST)
    print(f"Synced {SOURCE} -> {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
