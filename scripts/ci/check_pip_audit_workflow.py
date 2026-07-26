#!/usr/bin/env python3
"""Reject pip-audit CLI options that are not supported by pip-audit."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


UNSUPPORTED_OPTIONS = ("--severity", "--exit-code")


def collect_findings(workflow_path: Path, content: str) -> list[str]:
    workflow = yaml.safe_load(content) or {}
    findings: list[str] = []
    jobs = workflow.get("jobs", {})
    for job_name, job in jobs.items():
        for step_index, step in enumerate(job.get("steps", []), start=1):
            run = step.get("run")
            if not isinstance(run, str) or "pip-audit" not in run:
                continue

            step_name = step.get("name", f"step {step_index}")
            for option in UNSUPPORTED_OPTIONS:
                if re.search(rf"(?<!\S){re.escape(option)}(?:=|\s|$)", run):
                    findings.append(
                        f"{workflow_path}: jobs.{job_name}.{step_name}: unsupported pip-audit option {option}"
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "workflow",
        nargs="?",
        type=Path,
        default=Path(".github/workflows/pr-checks.yml"),
    )
    args = parser.parse_args()

    try:
        content = args.workflow.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{args.workflow}: unable to read workflow ({exc})", file=sys.stderr)
        return 1

    try:
        findings = collect_findings(args.workflow, content)
    except yaml.YAMLError as exc:
        print(f"{args.workflow}: invalid workflow YAML ({exc})", file=sys.stderr)
        return 1

    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
