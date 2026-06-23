#!/usr/bin/env python3
"""Fail if performance load-test workflows configure forbidden auth bypass flags.

The load-test stack is production-like enough to exercise required auth paths.
It must therefore use signed CI test credentials rather than production-forbidden
bypass toggles.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

FORBIDDEN_BYPASS_FLAGS = (
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "ALLOW_DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
)

# Match either YAML/env assignments (FLAG: true, FLAG=true) or generated .env
# lines inside workflow run blocks. Comments are ignored below.
_ASSIGNMENT_RE = re.compile(
    r"(?P<flag>{flags})\b\s*(?::|=)\s*(?P<value>[^\s#]+)?".format(
        flags="|".join(re.escape(flag) for flag in FORBIDDEN_BYPASS_FLAGS)
    )
)


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def scan(path: Path) -> list[str]:
    violations: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        if _is_comment(line):
            continue
        match = _ASSIGNMENT_RE.search(line)
        if not match:
            continue
        flag = match.group("flag")
        value = (match.group("value") or "").strip().strip('"\'')
        violations.append(
            f"{path}:{line_number} configures production-forbidden auth bypass flag "
            f"{flag}{'=' + value if value else ''}"
        )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assert performance workflows do not configure auth bypass flags."
    )
    parser.add_argument(
        "workflow",
        nargs="+",
        type=Path,
        help="Performance workflow file(s) to scan.",
    )
    args = parser.parse_args()

    violations: list[str] = []
    for workflow in args.workflow:
        violations.extend(scan(workflow))

    if violations:
        print("ERROR: performance workflow auth bypass guard failed")
        for violation in violations:
            print(f" - {violation}")
        return 1

    print("Performance workflow auth bypass guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
