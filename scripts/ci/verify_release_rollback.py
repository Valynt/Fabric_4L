#!/usr/bin/env python3
"""Verify static release rollback readiness without touching live systems."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str]) -> int:
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, check=False)
    return result.returncode


def main() -> int:
    checks = [
        [sys.executable, "scripts/ci/check_migration_rollback_policy.py"],
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/release/test_database_migration_rollback.py",
            "tests/release/test_rollback_procedure.py",
        ],
    ]
    for command in checks:
        rc = _run(command)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
