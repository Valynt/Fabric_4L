#!/usr/bin/env python3
"""Fail when tracked source files contain unresolved merge conflict blocks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


START = "<<<<<<<"
SEPARATOR = "======="
END = ">>>>>>>"


def _tracked_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [repo_root / line for line in result.stdout.splitlines() if line.strip()]


def _has_conflict_block(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    in_conflict = False
    saw_separator = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{START} "):
            in_conflict = True
            saw_separator = False
            continue
        if in_conflict and stripped == SEPARATOR:
            saw_separator = True
            continue
        if in_conflict and stripped.startswith(f"{END} ") and saw_separator:
            return True

    return False


def find_conflicts(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.is_file() and _has_conflict_block(path)]


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    repo_root = Path.cwd()
    paths = [Path(arg) for arg in args] if args else _tracked_files(repo_root)
    conflicts = find_conflicts(paths)

    if conflicts:
        print("Unresolved merge conflict markers found:")
        for path in conflicts:
            try:
                display = path.resolve().relative_to(repo_root.resolve())
            except ValueError:
                display = path
            print(f" - {display}")
        return 1

    print("No unresolved merge conflict markers found in tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
