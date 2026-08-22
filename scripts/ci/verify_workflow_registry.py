#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOWS_DIR = ROOT / ".github" / "workflows"
DEFAULT_REGISTRY = DEFAULT_WORKFLOWS_DIR / "workflow-registry.json"
MAKEFILE = ROOT / "Makefile"
ROOT_PACKAGE_JSON = ROOT / "package.json"
WEB_PACKAGE_JSON = ROOT / "apps" / "web" / "package.json"
MAX_WORKFLOW_FILES = 58

REQUIRED_FIELDS = {
    "path",
    "name",
    "owner",
    "trigger",
    "trigger_purpose",
    "blocking",
    "required_secrets",
    "produced_artifacts",
    "runtime_budget_minutes",
    "local_validation_command",
    "deprecation_status",
}
DEPRECATION_STATES = {
    "active",
    "deprecated",
    "replaced",
    "candidate-for-consolidation",
}
SECRET_RE = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")
DYNAMIC_SECRET_RE = re.compile(r"secrets\[[^\]]*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"][^\]]*\]")
MAKE_CMD_RE = re.compile(r"^make\s+(.+)$")
PNPM_CMD_RE = re.compile(r"^pnpm\s+(.+)$")
PYTHON_SCRIPT_RE = re.compile(r"^python\s+([^\s]+\.py)(?:\s|$)")
PYTEST_RE = re.compile(r"^(?:python\s+-m\s+)?pytest(?:\s+(.+))?$")


class WorkflowRegistryError(Exception):
    pass


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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise WorkflowRegistryError(f"{path}: registry root must be a JSON object")
    return data


def workflow_files(workflows_dir: Path) -> list[Path]:
    return sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in workflows_dir.glob(pattern)
        if path.is_file()
    )


def rel_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


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


def registry_entries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    entries = registry.get("workflows")
    if not isinstance(entries, list):
        raise WorkflowRegistryError("workflow-registry.json: `workflows` must be a list")
    if not all(isinstance(entry, dict) for entry in entries):
        raise WorkflowRegistryError("workflow-registry.json: every workflow entry must be an object")
    return entries


def load_make_targets(root: Path) -> set[str]:
    makefile = root / "Makefile"
    if not makefile.exists():
        return set()
    targets: set[str] = set()
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if line.startswith(("\t", " ")) or ":" not in line or "##" not in line:
            continue
        head = line.split(":", 1)[0].strip()
        if not head or head.startswith(".") or "=" in head:
            continue
        for token in head.split():
            if re.fullmatch(r"[A-Za-z0-9_.\-/]+", token):
                targets.add(token)
    return targets


def load_pnpm_scripts(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    scripts = data.get("scripts", {})
    return set(scripts.keys()) if isinstance(scripts, dict) else set()


def command_exists(command: str, root: Path) -> bool:
    command = command.strip()
    if not command:
        return False

    make_match = MAKE_CMD_RE.match(command)
    if make_match:
        tokens = shlex.split(make_match.group(1))
        target = next((token for token in tokens if not token.startswith("-") and "=" not in token), "")
        return target in load_make_targets(root)

    pnpm_match = PNPM_CMD_RE.match(command)
    if pnpm_match:
        tokens = shlex.split(pnpm_match.group(1))
        if not tokens:
            return False
        if tokens[0] == "run" and len(tokens) >= 2:
            return tokens[1] in load_pnpm_scripts(root / "package.json")
        if tokens[0] in load_pnpm_scripts(root / "package.json"):
            return True
        if tokens[0] == "--dir" and len(tokens) >= 4 and tokens[2] == "run":
            package_json = root / tokens[1] / "package.json"
            return tokens[3] in load_pnpm_scripts(package_json)
        if tokens[0] == "--filter" and "run" in tokens:
            run_index = tokens.index("run")
            if run_index + 1 < len(tokens):
                if tokens[1] in {"./apps/web", "web"}:
                    return tokens[run_index + 1] in load_pnpm_scripts(root / "apps" / "web" / "package.json")
                return tokens[run_index + 1] in load_pnpm_scripts(root / "package.json")
        return False

    python_match = PYTHON_SCRIPT_RE.match(command)
    if python_match:
        return (root / python_match.group(1)).exists()

    pytest_match = PYTEST_RE.match(command)
    if pytest_match:
        args = shlex.split(pytest_match.group(1) or "")
        targets = [arg for arg in args if not arg.startswith("-")]
        return not targets or all((root / target).exists() for target in targets)

    return False


def command_uses_public_interface(command: str) -> bool:
    command = command.strip()
    return bool(MAKE_CMD_RE.match(command) or PNPM_CMD_RE.match(command))


def entry_key(entry: dict[str, Any]) -> str:
    return str(entry.get("path", "<missing path>"))


def validate_entry_shape(entry: dict[str, Any], errors: list[str]) -> None:
    path = entry_key(entry)
    missing = sorted(REQUIRED_FIELDS - set(entry))
    if missing:
        errors.append(f"{path}: missing required field(s): {', '.join(missing)}")
        return

    for field in ("path", "name", "owner", "trigger_purpose", "local_validation_command", "deprecation_status"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            errors.append(f"{path}: `{field}` must be a non-empty string")

    if not isinstance(entry.get("trigger"), list) or not all(
        isinstance(item, str) and item.strip() for item in entry.get("trigger", [])
    ):
        errors.append(f"{path}: `trigger` must be a non-empty list of strings")

    if not isinstance(entry.get("blocking"), bool):
        errors.append(f"{path}: `blocking` must be a boolean")

    for field in ("required_secrets", "produced_artifacts"):
        if not isinstance(entry.get(field), list) or not all(isinstance(item, str) for item in entry.get(field, [])):
            errors.append(f"{path}: `{field}` must be a list of strings")

    if not isinstance(entry.get("runtime_budget_minutes"), int) or entry.get("runtime_budget_minutes", 0) <= 0:
        errors.append(f"{path}: `runtime_budget_minutes` must be a positive integer")

    status = entry.get("deprecation_status")
    if status not in DEPRECATION_STATES:
        errors.append(f"{path}: `deprecation_status` must be one of {', '.join(sorted(DEPRECATION_STATES))}")
    elif status != "active" and not (
        isinstance(entry.get("replaced_by"), str) and entry.get("replaced_by", "").strip()
    ):
        errors.append(f"{path}: non-active workflow must declare `replaced_by` or a resolution path")


def validate_duplicate_groups(registry: dict[str, Any], registered_paths: set[str], errors: list[str]) -> None:
    groups = registry.get("duplicate_groups")
    if not isinstance(groups, list):
        errors.append("workflow-registry.json: `duplicate_groups` must be a list")
        return

    covered: set[str] = set()
    for index, group in enumerate(groups):
        label = f"duplicate_groups[{index}]"
        if not isinstance(group, dict):
            errors.append(f"{label}: must be an object")
            continue
        required = {"status", "canonical_workflow", "overlapping_workflows", "reason", "resolution_path"}
        missing = sorted(required - set(group))
        if missing:
            errors.append(f"{label}: missing required field(s): {', '.join(missing)}")
            continue
        canonical = group.get("canonical_workflow")
        overlaps = group.get("overlapping_workflows")
        if not isinstance(canonical, str) or canonical not in registered_paths:
            errors.append(f"{label}: canonical workflow is not registered: {canonical}")
        if not isinstance(overlaps, list) or not overlaps:
            errors.append(f"{label}: overlapping_workflows must be a non-empty list")
            continue
        for path in overlaps:
            if path not in registered_paths:
                errors.append(f"{label}: overlapping workflow is not registered: {path}")
            covered.add(str(path))
        if canonical:
            covered.add(str(canonical))
        for field in ("status", "reason", "resolution_path"):
            if not isinstance(group.get(field), str) or not group[field].strip():
                errors.append(f"{label}: `{field}` must be a non-empty string")

    # Heuristic overlap detection: same trigger set plus first purpose token.
    purpose_groups: dict[tuple[tuple[str, ...], str], list[str]] = defaultdict(list)
    for entry in registry_entries(registry):
        purpose = str(entry.get("trigger_purpose", "")).lower()
        token = next((part for part in re.split(r"[^a-z0-9]+", purpose) if len(part) >= 4), "")
        if token:
            purpose_groups[(tuple(sorted(entry.get("trigger", []))), token)].append(str(entry.get("path")))

    for paths in purpose_groups.values():
        if len(paths) <= 1:
            continue
        if not set(paths).issubset(covered):
            errors.append(
                "workflow-registry.json: overlapping workflows require a duplicate_groups entry: "
                + ", ".join(sorted(paths))
            )


def validate_registry(
    *,
    root: Path,
    workflows_dir: Path,
    registry_path: Path,
) -> list[str]:
    errors: list[str] = []
    if not registry_path.exists():
        return [f"Missing workflow registry: {registry_path}"]

    try:
        registry = load_json(registry_path)
        entries = registry_entries(registry)
    except (OSError, json.JSONDecodeError, WorkflowRegistryError) as exc:
        return [str(exc)]

    workflow_paths = workflow_files(workflows_dir)
    if len(workflow_paths) > MAX_WORKFLOW_FILES:
        errors.append(
            f"{rel_path(workflows_dir, root)}: workflow count {len(workflow_paths)} exceeds "
            f"S6-6 limit of {MAX_WORKFLOW_FILES}"
        )

    actual_files = {rel_path(path, root): path for path in workflow_paths}
    by_path: dict[str, dict[str, Any]] = {}
    for entry in entries:
        path = str(entry.get("path", ""))
        if path in by_path:
            errors.append(f"{path}: duplicate registry entry")
        by_path[path] = entry
        validate_entry_shape(entry, errors)

    missing_entries = sorted(set(actual_files) - set(by_path))
    stale_entries = sorted(set(by_path) - set(actual_files))
    for path in missing_entries:
        errors.append(f"{path}: workflow file is missing from workflow-registry.json")
    for path in stale_entries:
        errors.append(f"{path}: registry entry points to a missing workflow file")

    for path, entry in sorted(by_path.items()):
        workflow_path = actual_files.get(path)
        if workflow_path is None:
            continue
        try:
            data = load_yaml(workflow_path)
        except yaml.YAMLError as exc:
            errors.append(f"{path}: invalid workflow YAML: {exc}")
            continue

        actual_name = str(data.get("name", "")).strip()
        if actual_name and entry.get("name") != actual_name:
            errors.append(f"{path}: registry name {entry.get('name')!r} does not match workflow name {actual_name!r}")

        actual_triggers = workflow_triggers(data)
        if sorted(entry.get("trigger", [])) != actual_triggers:
            errors.append(
                f"{path}: registry trigger {sorted(entry.get('trigger', []))!r} "
                f"does not match workflow trigger {actual_triggers!r}"
            )

        actual_secrets = workflow_secrets(workflow_path)
        registered_secrets = sorted(entry.get("required_secrets", []))
        if registered_secrets != actual_secrets:
            errors.append(
                f"{path}: registry required_secrets {registered_secrets!r} "
                f"does not match workflow secrets {actual_secrets!r}"
            )

        actual_artifacts = workflow_artifact_paths(data)
        registered_artifacts = sorted(entry.get("produced_artifacts", []))
        if registered_artifacts != actual_artifacts:
            errors.append(
                f"{path}: registry produced_artifacts {registered_artifacts!r} "
                f"does not match upload-artifact paths {actual_artifacts!r}"
            )

        if entry.get("runtime_budget_minutes", 0) < workflow_runtime_budget(data):
            errors.append(
                f"{path}: runtime budget {entry.get('runtime_budget_minutes')} is below workflow timeout "
                f"{workflow_runtime_budget(data)}"
            )

        command = str(entry.get("local_validation_command", ""))
        if not command_exists(command, root):
            errors.append(f"{path}: local validation command is not recognized: {command}")
        elif not command_uses_public_interface(command):
            errors.append(
                f"{path}: local validation command must use a documented public command-map interface: {command}"
            )

    validate_duplicate_groups(registry, set(by_path), errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GitHub Actions workflow ownership registry")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--workflows-dir", type=Path)
    parser.add_argument("--registry", type=Path)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    workflows_dir = (args.workflows_dir or root / ".github" / "workflows").resolve()
    registry_path = (args.registry or workflows_dir / "workflow-registry.json").resolve()

    errors = validate_registry(root=root, workflows_dir=workflows_dir, registry_path=registry_path)
    if errors:
        print("Workflow registry validation failed:\n")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print(f"Workflow registry validation passed: {registry_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
