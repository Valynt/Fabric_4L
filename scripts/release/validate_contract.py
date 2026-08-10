#!/usr/bin/env python3
"""V1 release factory — validate the launch contract and control-plane artifacts.

Thin wrapper (INV-FACTORY-001): the authoritative validation logic lives in
the CI-enforced pytest suite tests/release/test_release_v1_contract_artifacts.py
(run by make gate-release-policy). This script executes that suite so the
same checks are available as `make validate-launch-contract` without
duplicating validation logic.

Usage:
    python scripts/release/validate_contract.py
    make validate-launch-contract
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATOR = "tests/release/test_release_v1_contract_artifacts.py"


def main() -> int:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            VALIDATOR,
            "-q",
            "--no-mandatory-dep-check",
        ],
        cwd=REPO_ROOT,
        check=False,
    )
    if proc.returncode == 0:
        print("launch contract and release/v1 control-plane artifacts are valid")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
