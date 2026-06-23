#!/usr/bin/env python3
"""Generate a deterministic workflow-registry.json from GitHub Actions workflow files.

This generator is the source of truth for the workflow registry. It scans
.github/workflows, extracts auto-detectable metadata, and writes a sorted,
minimally opinionated registry. Manual fields (owner, trigger_purpose, blocking,
local_validation_command, deprecation_status) are filled with safe defaults
and must be curated by the owning team.

Run with --check in CI to fail closed when the registry is stale.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOWS_DIR = ROOT / ".github" / "workflows"
DEFAULT_REGISTRY = DEFAULT_WORKFLOWS_DIR / "workflow-registry.json"

DEFAULT_OWNER = "@value-fabric/sre-leads"
DEFAULT_LOCAL_VALIDATION_COMMAND = "make check-workflow-references"
DEFAULT_TRIGGER_PURPOSE = "CI/CD"
DEFAULT_DEPRECATION_STATUS = "active"

SECRET_RE = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")
DYNAMIC_SECRET_RE = re.compile(r"secrets\[[^\]]*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"][^\]]*\]")


class GithubActionsLoader(yaml.SafeLoader):
    """YAML loader that keeps GitHub Actions' `on` key as a string."""


for first, resolvers in list(GithubActionsLoader.yaml_implicit_resolvers.items()):
    GithubActionsLoader.yaml_implicit_resolvers[first] = [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag != "tag:yaml.org,2002:bool"
    ]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.load(fh, Loader=GithubActionsLoader)
    return data if isinstance(data, dict) else {}


def workflow_files(workflows_dir: Path) -> list[Path]:
    return sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in workflows_dir.glob(pattern)
        if path.is_file()
    )


def workflow_triggers(data: dict[str, Any]) -> list[str]:
    raw = data.get("on")
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return sorted(str(item) for item in raw)
    if isinstance(raw, dict):
        return sorted(str(key) for key in raw)
    return []


def workflow_artifact_paths(data: dict[str, Any]) -> list[str]:
    artifacts: list[str] = []
    jobs = data.get("jobs")
    if not isinstance(jobs, dict):
        return artifacts
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = str(step.get("uses", ""))
            if not uses.startswith("actions/upload-artifact"):
                continue
            with_block = step.get("with") if isinstance(step.get("with"), dict) else {}
            raw_path = with_block.get("path", "")
            if isinstance(raw_path, list):
                artifacts.extend(str(item).strip() for item in raw_path if str(item).strip())
            else:
                artifacts.extend(
                    line.strip()
                    for line in str(raw_path).splitlines()
                    if line.strip()
                )
    return sorted(set(artifacts))


def workflow_secrets(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return sorted(set(SECRET_RE.findall(text)) | set(DYNAMIC_SECRET_RE.findall(text)))


def workflow_runtime_budget(data: dict[str, Any]) -> int:
    timeouts: list[int] = []
    jobs = data.get("jobs")
    if not isinstance(jobs, dict):
        return 30
    for job in jobs.values():
        if isinstance(job, dict) and isinstance(job.get("timeout-minutes"), int):
            timeouts.append(int(job["timeout-minutes"]))
    return max(timeouts) if timeouts else 30


def build_registry(workflows_dir: Path) -> dict[str, Any]:
    workflows: list[dict[str, Any]] = []
    for path in workflow_files(workflows_dir):
        rel = path.relative_to(ROOT).as_posix()
        data = load_yaml(path)
        name = data.get("name") or path.stem
        workflows.append({
            "path": rel,
            "name": name,
            "owner": DEFAULT_OWNER,
            "trigger": workflow_triggers(data),
            "trigger_purpose": DEFAULT_TRIGGER_PURPOSE,
            "blocking": False,
            "required_secrets": workflow_secrets(path),
            "produced_artifacts": workflow_artifact_paths(data),
            "runtime_budget_minutes": workflow_runtime_budget(data),
            "local_validation_command": DEFAULT_LOCAL_VALIDATION_COMMAND,
            "deprecation_status": DEFAULT_DEPRECATION_STATUS,
        })

    return {
        "version": "1.0.0",
        "description": "Machine-readable registry of GitHub Actions workflows for Fabric_4L.",
        "workflows": workflows,
        "duplicate_groups": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic workflow-registry.json")
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=DEFAULT_WORKFLOWS_DIR,
        help="Directory containing GitHub Actions workflow YAML files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Output path for workflow-registry.json",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with error if output would differ from existing file",
    )
    args = parser.parse_args()

    generated = build_registry(args.workflows_dir)
    generated_text = json.dumps(generated, indent=2, sort_keys=False) + "\n"

    if args.check:
        if not args.output.exists():
            print(f"CHECK FAILED: {args.output} does not exist", file=sys.stderr)
            return 1
        existing_text = args.output.read_text(encoding="utf-8")
        if generated_text.strip() != existing_text.strip():
            print(f"CHECK FAILED: {args.output} is stale; run `python scripts/ci/generate_workflow_registry.py`", file=sys.stderr)
            return 1
        print(f"CHECK PASSED: {args.output} is in sync")
        return 0

    args.output.write_text(generated_text, encoding="utf-8")
    print(f"Generated {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
