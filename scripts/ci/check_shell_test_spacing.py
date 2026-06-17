#!/usr/bin/env python3
"""Enforce whitespace around shell test bracket constructs in workflow run blocks.

Catches the common mistake:
    if [["${VAR}" == ... ]]; then   -> missing space after [[
    if ["${VAR}" = ... ]; then     -> missing space after [
which bash parses as a command name rather than a test, causing silent failures.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
# Patterns that indicate a malformed test construct in a shell run block.
BAD_PATTERNS = [
    re.compile(r"(?:if|elif)\s*\[\[(?![ \t])"),   # [[ not followed by whitespace
    re.compile(r"(?:if|elif)\s*\[(?!\[)(?![ \t])"),  # [ not followed by [ or whitespace
]


def main() -> int:
    violations: list[tuple[Path, int, str]] = []
    if not WORKFLOW_DIR.exists():
        print(f"Workflow directory not found: {WORKFLOW_DIR}", file=sys.stderr)
        return 0

    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            # Only inspect lines that look like the start of an if test.
            stripped = line.strip()
            if not stripped.startswith("if ") and not stripped.startswith("elif "):
                continue
            for pattern in BAD_PATTERNS:
                if pattern.search(line):
                    violations.append((path, lineno, stripped))
                    break

    if violations:
        print("Shell test bracket spacing violations found:")
        for path, lineno, snippet in violations:
            print(f"  {path}:{lineno}: {snippet}")
        print(
            "Fix: ensure spaces after [[ and [, e.g. "
            "'if [[ \"${VAR}\" == ... ]]; then' or "
            "'if [ \"${VAR}\" = ... ]; then'"
        )
        return 1

    print("Shell test bracket spacing check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
