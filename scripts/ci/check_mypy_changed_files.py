#!/usr/bin/env python3
"""Run mypy on Python files changed in the current PR/branch.

New or touched files must have zero mypy errors. This is the "typed changed files"
gate. It does not consult the legacy baseline: touching a file with baseline debt
requires cleaning that debt.

Usage:
    python scripts/ci/check_mypy_changed_files.py \
        --service-dir services/layer1-ingestion \
        --base-ref origin/main
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _changed_files(service_dir: Path, base_ref: str | None) -> list[str]:
    if base_ref is None:
        # Compare against HEAD~1 by default
        base_ref = "HEAD~1"

    # Committed / tracked changes relative to the base ref
    diff_cmd = ["git", "diff", "--name-only", "--diff-filter=ACMRT", base_ref]
    diff_result = subprocess.run(
        diff_cmd, cwd=service_dir, capture_output=True, text=True, check=False
    )
    if diff_result.returncode != 0:
        print(f"git diff failed: {diff_result.stderr}", file=sys.stderr)
        return []
    changed = [line.strip() for line in diff_result.stdout.splitlines() if line.strip()]

    # Untracked files in the working tree
    untracked_result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=service_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    untracked = [
        line.strip() for line in untracked_result.stdout.splitlines() if line.strip()
    ]

    all_files = changed + untracked
    return [f for f in all_files if f.endswith(".py") and f.startswith("src/")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-dir", required=True, type=Path)
    parser.add_argument("--base-ref", default="origin/main")
    args = parser.parse_args()

    service_dir = args.service_dir.resolve()
    files = _changed_files(service_dir, args.base_ref)
    if not files:
        print("No changed Python source files; typed changed-files gate passes.")
        return 0

    cmd = [sys.executable, "-m", "mypy", *files]
    result = subprocess.run(cmd, cwd=service_dir)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
