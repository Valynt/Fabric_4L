#!/usr/bin/env python3
"""Run root npm parity gates through canonical Python targets.

This keeps package.json scripts portable across Windows shells and POSIX CI
while preserving the same pytest target lists used by the Makefile gates.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
BOOL_STRINGS = {"0", "1", "false", "true", "no", "yes", "off", "on"}


@dataclass(frozen=True)
class Gate:
    command: tuple[str, ...]
    cwd: Path = REPO_ROOT


GATES: dict[str, Gate] = {
    "security": Gate(
        (
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "--tb=short",
            "-x",
            "tests/security/test_security_smoke.py",
        )
    ),
    "isolation": Gate(
        (
            sys.executable,
            str(REPO_ROOT / "scripts" / "ci" / "run_tenant_isolation_gate.py"),
        )
    ),
    "crawler": Gate(
        (
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "--tb=short",
            "tests/crawler/",
            "tests/unit/test_playwright_crawler.py",
            "tests/unit/test_crawler_config.py",
            "tests/unit/test_crawler_telemetry.py",
            "tests/unit/test_quality_gate.py",
        ),
        cwd=REPO_ROOT / "services/layer1-ingestion",
    ),
}


def gate_env() -> dict[str, str]:
    env = os.environ.copy()
    debug = env.get("DEBUG")
    if debug is not None and debug.strip().lower() not in BOOL_STRINGS:
        env["DEBUG"] = "false"
    return env


def run_gate(name: str) -> int:
    gate = GATES[name]
    result = subprocess.run(gate.command, cwd=gate.cwd, env=gate_env(), check=False)
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate", choices=sorted(GATES))
    args = parser.parse_args(argv)
    return run_gate(args.gate)


if __name__ == "__main__":
    raise SystemExit(main())
