#!/usr/bin/env python3
"""Run the centralized production-readiness pytest suites.

The Makefile target for this gate must work from Windows developer shells and
POSIX CI. Keep orchestration here so the gate does not depend on shell loops.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
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
MANIFEST_FILENAME = "manifest.json"
SUMMARY_FILENAME = "summary.md"
JUNIT_FILENAME = "junit.xml"
SUITE_REGRESSION_DOMAINS = {
    "security": ("security", "tenant-isolation"),
    "reliability": ("operational-behavior",),
    "observability": ("operational-behavior",),
    "recovery": ("operational-behavior",),
    "release": ("operational-behavior", "architecture"),
    "tenancy": ("security", "tenant-isolation"),
    "billing": ("contracts", "tenant-isolation"),
    "abuse": ("security",),
    "config": ("security", "architecture"),
    "audit": ("security", "operational-behavior"),
}


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


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
    summary_path = suite_artifact_dir / SUMMARY_FILENAME
    junit_path = suite_artifact_dir / JUNIT_FILENAME

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


def write_manifest(
    *,
    artifact_dir: Path,
    suites: Sequence[str],
    results: Sequence[SuiteResult],
    stopped_on_failure: bool,
) -> Path:
    result_by_suite = {result.suite: result for result in results}
    suite_entries = []
    for suite in suites:
        result = result_by_suite.get(suite)
        status = "not_run"
        returncode = None
        junit_path = artifact_dir / suite / JUNIT_FILENAME
        summary_path = artifact_dir / suite / SUMMARY_FILENAME
        if result is not None:
            status = "passed" if result.returncode == 0 else "failed"
            returncode = result.returncode
            junit_path = result.junit_path
            summary_path = result.summary_path

        suite_entries.append(
            {
                "suite": suite,
                "status": status,
                "returncode": returncode,
                "command": [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-v",
                    "--tb=short",
                    f"tests/{suite}/",
                ],
                "junit_artifact": _display_path(junit_path),
                "summary_artifact": _display_path(summary_path),
                "regression_domains": list(SUITE_REGRESSION_DOMAINS[suite]),
                "blocking": True,
            }
        )

    executed = [entry for entry in suite_entries if entry["status"] != "not_run"]
    overall_status = "passed" if len(executed) == len(suite_entries) and all(
        entry["status"] == "passed" for entry in suite_entries
    ) else "failed"
    covered_domains = sorted(
        {
            domain
            for entry in suite_entries
            if entry["status"] != "not_run"
            for domain in entry["regression_domains"]
        }
    )
    required_domains = ["architecture", "contracts", "operational-behavior", "security", "tenant-isolation"]
    payload = {
        "schema_version": 1,
        "generated_at_utc": _utc_now(),
        "gate": "production-readiness-gate",
        "command": "make production-readiness-gate",
        "overall_status": overall_status,
        "stopped_on_failure": stopped_on_failure,
        "artifact_dir": _display_path(artifact_dir),
        "required_regression_domains": required_domains,
        "covered_regression_domains": covered_domains,
        "blocks_release_on_failure": True,
        "suites": suite_entries,
    }
    manifest_path = artifact_dir / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def run_gate(
    suites: Iterable[str],
    artifact_dir: Path,
    pytest_args: Sequence[str] = (),
) -> int:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    suite_list = tuple(suites)
    results: list[SuiteResult] = []
    for suite in suite_list:
        print(f"-> Production readiness suite: {suite}", flush=True)
        result = run_suite(suite, artifact_dir, pytest_args)
        results.append(result)
        if result.returncode != 0:
            manifest_path = write_manifest(
                artifact_dir=artifact_dir,
                suites=suite_list,
                results=results,
                stopped_on_failure=True,
            )
            print(
                f"FAIL: production readiness suite {suite} failed "
                f"(junit: {result.junit_path.as_posix()}, manifest: {manifest_path.as_posix()})",
                file=sys.stderr,
            )
            return result.returncode
    manifest_path = write_manifest(
        artifact_dir=artifact_dir,
        suites=suite_list,
        results=results,
        stopped_on_failure=False,
    )
    print(f"Evidence manifest: {manifest_path.as_posix()}")
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
