#!/usr/bin/env python3
"""Fail if tracked source/config files contain NUL bytes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ALLOWED_SUFFIXES = {".py", ".ts", ".tsx", ".json", ".yaml"}


def files_with_nul(paths: list[Path], base: Path | None = None) -> list[str]:
    """Return relative path strings for any files in *paths* that contain NUL bytes."""
    offenders: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        data = path.read_bytes()
        if b"\x00" in data:
            label = str(path.relative_to(base)) if base else str(path)
            offenders.append(label)
    return offenders


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"], check=True, capture_output=True, text=True
    )
    files: list[Path] = []
    for line in result.stdout.splitlines():
        path = Path(line)
        if path.suffix in ALLOWED_SUFFIXES:
            files.append(path)
    return files


def main() -> int:
    offenders = files_with_nul(tracked_files(), Path.cwd())

    if offenders:
        print("ERROR: NUL-byte guard failed: tracked files with embedded \\x00 detected:")
        for offender in offenders:
            print(f"  - {offender}")
        print("Remove NUL bytes before merging.")
        return 1

    print("OK: NUL-byte guard passed: no tracked .py/.ts/.tsx/.json/.yaml files contain \\x00 bytes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
