#!/usr/bin/env python3
"""Run selected CI checks and emit lightweight timing artifacts.

The script is intentionally dependency-free so it can be used from GitHub Actions,
local maintainer shells, or ad hoc CI jobs. Each check is provided as a single
argument in the form:

    name|stdout_artifact_path|command

The stdout path may be blank when the caller does not need a separate command
output file. The wrapper exits non-zero if any wrapped command exits non-zero.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class TimedCheck:
    """Execution result for one timed check."""

    name: str
    command: str
    status: str
    returncode: int
    duration_seconds: float
    started_at: str
    stdout_artifact: str | None
    stdout_bytes: int
    stderr_bytes: int


def parse_check(value: str) -> tuple[str, Path | None, str]:
    """Parse a check specification from ``name|stdout_path|command``."""

    parts = value.split("|", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            "check must use format 'name|stdout_artifact_path|command'"
        )
    name, stdout_path, command = (part.strip() for part in parts)
    if not name:
        raise argparse.ArgumentTypeError("check name must not be empty")
    if not command:
        raise argparse.ArgumentTypeError("check command must not be empty")
    return name, Path(stdout_path) if stdout_path else None, command


def run_check(name: str, stdout_path: Path | None, command: str) -> TimedCheck:
    """Run one check, stream grouped output, and return timing metadata."""

    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    print(f"::group::{name}", flush=True)
    print(f"$ {command}", flush=True)
    completed = subprocess.run(
        command,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    duration = time.perf_counter() - started

    if completed.stdout:
        print(completed.stdout, end="", flush=True)
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr, flush=True)
    print(f"::endgroup::{name}", flush=True)

    if stdout_path is not None:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(completed.stdout, encoding="utf-8")

    return TimedCheck(
        name=name,
        command=command,
        status="pass" if completed.returncode == 0 else "fail",
        returncode=completed.returncode,
        duration_seconds=round(duration, 6),
        started_at=started_at.isoformat(),
        stdout_artifact=str(stdout_path) if stdout_path is not None else None,
        stdout_bytes=len(completed.stdout.encode("utf-8")),
        stderr_bytes=len(completed.stderr.encode("utf-8")),
    )


def write_json_summary(path: Path, checks: Sequence[TimedCheck]) -> None:
    """Write the machine-readable timing summary."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_duration_seconds": round(sum(check.duration_seconds for check in checks), 6),
        "checks": [asdict(check) for check in checks],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown_summary(path: Path, checks: Sequence[TimedCheck]) -> None:
    """Write the human-readable timing summary."""

    path.parent.mkdir(parents=True, exist_ok=True)
    total = sum(check.duration_seconds for check in checks)
    lines = [
        "# CI Timing Summary",
        "",
        "This artifact records wall-clock durations for targeted CI checks. It is intended for trend analysis and regression triage; it is not a replacement for functional pass/fail evidence.",
        "",
        f"Total measured duration: **{total:.3f} seconds**.",
        "",
        "| Check | Status | Duration Seconds | Return Code | Stdout Artifact |",
        "|---|---:|---:|---:|---|",
    ]
    for check in checks:
        artifact = check.stdout_artifact or ""
        lines.append(
            f"| {check.name} | {check.status.upper()} | {check.duration_seconds:.3f} | {check.returncode} | {artifact} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts/ci-timing"),
        help="Directory for ci-timing-summary.json and ci-timing-summary.md.",
    )
    parser.add_argument(
        "--check",
        action="append",
        type=parse_check,
        required=True,
        metavar="NAME|STDOUT_PATH|COMMAND",
        help="Check to time. May be repeated.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checks = [run_check(name, stdout_path, command) for name, stdout_path, command in args.check]
    write_json_summary(args.artifact_dir / "ci-timing-summary.json", checks)
    write_markdown_summary(args.artifact_dir / "ci-timing-summary.md", checks)
    failures = [check for check in checks if check.returncode != 0]
    if failures:
        print(f"{len(failures)} timed CI check(s) failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
