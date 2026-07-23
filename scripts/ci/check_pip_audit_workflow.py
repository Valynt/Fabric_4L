#!/usr/bin/env python3
"""Reject pip-audit CLI options that are not supported by pip-audit."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


UNSUPPORTED_OPTIONS = ("--severity", "--exit-code")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "workflow",
        nargs="?",
        type=Path,
        default=Path(".github/workflows/pr-checks.yml"),
    )
    args = parser.parse_args()

    content = args.workflow.read_text(encoding="utf-8")
    findings: list[str] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if "pip-audit" not in line:
            continue
        for option in UNSUPPORTED_OPTIONS:
            if re.search(rf"(?<!\S){re.escape(option)}(?:=|\s|$)", line):
                findings.append(f"{args.workflow}:{line_number}: unsupported pip-audit option {option}")

    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
