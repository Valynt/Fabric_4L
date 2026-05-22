#!/usr/bin/env python3
"""Fail CI when non-canonical shared identity imports are introduced."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = ["services", "value_fabric", "packages", "tests", "scripts"]
ALLOWLIST_PATH = REPO_ROOT / "config" / "ci" / "shared_identity_import_shim_allowlist.txt"

DISALLOWED_PATTERNS = [
    re.compile(r"^\s*(from|import)\s+shared\.identity(\.|\s|$)"),
    re.compile(r"^\s*(from|import)\s+value_fabric\.layer[1-6]\.identity(\.|\s|$)"),
    re.compile(r"^\s*(from|import)\s+services\.layer[1-6].*\.identity(\.|\s|$)"),
]


def load_allowlist() -> set[Path]:
    if not ALLOWLIST_PATH.exists():
        return set()
    entries: set[Path] = set()
    for raw in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.add(Path(line))
    return entries


def main() -> int:
    allowlist = load_allowlist()
    violations: list[str] = []

    for root in SCAN_ROOTS:
        scan_root = REPO_ROOT / root
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*.py"):
            rel = path.relative_to(REPO_ROOT)
            if rel in allowlist:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if any(pattern.search(line) for pattern in DISALLOWED_PATTERNS):
                    violations.append(f"{rel}:{lineno}: {line.strip()}")

    if violations:
        print(
            "Shared identity canonical import check failed. "
            "Use 'from value_fabric.shared.identity ...' imports only.",
            file=sys.stderr,
        )
        print(
            "Explicit shim exceptions must be listed in "
            "config/ci/shared_identity_import_shim_allowlist.txt.",
            file=sys.stderr,
        )
        for item in violations:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("OK: no new non-canonical shared identity imports found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
