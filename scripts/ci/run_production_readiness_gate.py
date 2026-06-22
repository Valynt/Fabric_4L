#!/usr/bin/env python3
"""Run the centralized production-readiness pytest suites.

The Makefile target for this gate must work from Windows developer shells and
POSIX CI. Keep orchestration here so the gate does not depend on shell loops.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIR = Path("artifacts/production-readiness")
DEFAULT_SUITES = (
    "security",
    "reliability",
    "observability",
    "recovery",
    "release",
    "tenancy",
    "billing",
    "abuse",
    "config",
    "audit",
)
BOOL_STRINGS = {"0", "1", "false", "true", "no", "yes", "off", "on"}
DEFAULT_TEMP_DIR = REPO_ROOT / ".tmp" / "production-readiness-pytest"


@dataclass(frozen=True)
class SuiteResult:
    suite: str
    returncode: int
    junit_path: Path
    summary_path: Path


def gate_env() -> dict[str, str]:
    env = os.environ.copy()
    debug = env.get("DEBUG")
    if debug is not None and debug.strip().lower() not in BOOL_STRINGS:
        env["DEBUG"] = "false"
    DEFAULT_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    env["TMPDIR"] = str(DEFAULT_TEMP_DIR)
    env["TMP"] = str(DEFAULT_TEMP_DIR)
    env["TEMP"] = str(DEFAULT_TEMP_DIR)
    return env


def write_summary(
    *,
    suite: str,
    status: str,
    artifact_dir: Path,
    summary_path: Path,
    junit_path: Path,
) -> None:
    if junit_path.is_absolute():
        try:
            relative_junit = junit_path.relative_to(REPO_ROOT)
        except ValueError:
            relative_junit = junit_path
    else:
        relative_junit = junit_path
    relative_suite = Path("tests") / suite
    summary_path.write_text(
        "\n".join(
            (
                f"# Production readiness: {suite}",
                "",
                f"- Suite: {relative_suite.as_posix()}/",
                f"- JUnit artifact: {relative_junit.as_posix()}",
                f"- Status: {status}",
                "",
            )
        ),
        encoding="utf-8",
    )


def run_suite(suite: str, artifact_dir: Path, pytest_args: Sequence[str]) -> SuiteResult:
    suite_artifact_dir = artifact_dir / suite
    suite_artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = suite_artifact_dir / "summary.md"
    junit_path = suite_artifact_dir / "junit.xml"

    write_summary(
        suite=suite,
        status="running",
        artifact_dir=artifact_dir,
        summary_path=summary_path,
        junit_path=junit_path,
    )

    command = (
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        f"tests/{suite}/",
        "--junitxml",
        str(junit_path),
        *pytest_args,
    )
    result = subprocess.run(command, cwd=REPO_ROOT, env=gate_env(), check=False)
    status = "passed" if result.returncode == 0 else "failed"
    write_summary(
        suite=suite,
        status=status,
        artifact_dir=artifact_dir,
        summary_path=summary_path,
        junit_path=junit_path,
    )
    return SuiteResult(
        suite=suite,
        returncode=result.returncode,
        junit_path=junit_path,
        summary_path=summary_path,
    )


def run_gate(
    suites: Iterable[str],
    artifact_dir: Path,
    pytest_args: Sequence[str] = (),
) -> int:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for suite in suites:
        print(f"-> Production readiness suite: {suite}", flush=True)
        result = run_suite(suite, artifact_dir, pytest_args)
        if result.returncode != 0:
            print(
                f"FAIL: production readiness suite {suite} failed "
                f"(junit: {result.junit_path.as_posix()})",
                file=sys.stderr,
            )
            return result.returncode
    print("PASS: production-readiness-gate passed")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help="Directory for per-suite JUnit XML and summary.md artifacts.",
    )
    parser.add_argument(
        "--suite",
        action="append",
        choices=DEFAULT_SUITES,
        help="Suite to run. Repeat to run a subset; defaults to all suites.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra pytest arguments after --.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    pytest_args = tuple(args.pytest_args)
    if pytest_args[:1] == ("--",):
        pytest_args = pytest_args[1:]
    artifact_dir = args.artifact_dir
    if not artifact_dir.is_absolute():
        artifact_dir = REPO_ROOT / artifact_dir
    return run_gate(args.suite or DEFAULT_SUITES, artifact_dir, pytest_args)


if __name__ == "__main__":
    raise SystemExit(main())
