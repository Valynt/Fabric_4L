#!/usr/bin/env python3
"""Validate spacing around [[ and ]] in GitHub Actions workflow run blocks.

Checks unquoted, non-heredoc shell content only. The rule is the standard bash
style: "[[" must be followed by whitespace, and "]]" must be preceded by whitespace.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
BAD_OPEN = re.compile(r"\[\[(?!\s)")
BAD_CLOSE = re.compile(r"(?<!\s)\]\]")
HEREDOC_START = re.compile(r"\s*<<\s*(-?)\s*['\"]?([^\s'\"]+)['\"]?(?:\s|$)")


def unquoted_segments(line: str) -> list[str]:
    """Return line segments that are outside single and double quotes."""
    segments: list[str] = []
    i = 0
    n = len(line)
    current = ""
    while i < n:
        ch = line[i]
        if ch == '"':
            segments.append(current)
            current = ""
            i += 1
            while i < n and line[i] != '"':
                if line[i] == "\\" and i + 1 < n:
                    i += 2
                else:
                    i += 1
            i += 1
            continue
        if ch == "'":
            segments.append(current)
            current = ""
            i += 1
            while i < n and line[i] != "'":
                i += 1
            i += 1
            continue
        current += ch
        i += 1
    segments.append(current)
    return segments


def find_heredoc_delimiter(line: str) -> str | None:
    """Return the heredoc delimiter if this line starts a quoted heredoc."""
    m = HEREDOC_START.search(line)
    if m:
        return m.group(2)
    return None


def check_file(path: Path) -> list[str]:
    violations: list[str] = []
    in_run_block = False
    run_indent: int | None = None
    run_lines: list[tuple[int, str]] = []
    heredoc_delim: str | None = None

    for idx, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.rstrip("\n")
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("run:"):
            in_run_block = True
            run_indent = indent
            heredoc_delim = None
            inline = stripped[4:].lstrip()
            if inline:
                run_lines.append((idx, inline))
            continue

        if in_run_block:
            if stripped == "" or indent > run_indent:
                if stripped:
                    if heredoc_delim is not None:
                        if stripped == heredoc_delim:
                            heredoc_delim = None
                        # Skip heredoc body lines.
                    else:
                        delim = find_heredoc_delimiter(stripped)
                        if delim is not None:
                            heredoc_delim = delim
                            # The line that opens the heredoc may also contain shell code before <<;
                            # include it for checking by keeping it in run_lines.
                        run_lines.append((idx, stripped))
                continue
            # Block ended; evaluate accumulated lines.
            for lno, content in run_lines:
                for segment in unquoted_segments(content):
                    if BAD_OPEN.search(segment) or BAD_CLOSE.search(segment):
                        violations.append(f"{path}:{lno}: {content}")
                        break
            in_run_block = False
            run_indent = None
            run_lines = []
            heredoc_delim = None

    if in_run_block:
        for lno, content in run_lines:
            for segment in unquoted_segments(content):
                if BAD_OPEN.search(segment) or BAD_CLOSE.search(segment):
                    violations.append(f"{path}:{lno}: {content}")
                    break

    return violations


def main() -> int:
    all_violations: list[str] = []
    for path in sorted(set(WORKFLOW_DIR.glob("*.yml")) | set(WORKFLOW_DIR.glob("*.yaml"))):
        all_violations.extend(check_file(path))

    if all_violations:
        print("Shell test bracket spacing violations found:")
        for v in all_violations:
            print(f"  {v}")
        return 1

    print("Shell test bracket spacing check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
