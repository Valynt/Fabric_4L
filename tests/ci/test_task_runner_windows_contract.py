"""Contracts for the provider-native task-runner smoke jobs."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
GITHUB_WORKFLOW = ROOT / ".github/workflows/pr-checks.yml"
DEPOT_WORKFLOW = ROOT / ".depot/workflows/pr-checks.yml"
WORKFLOWS = (GITHUB_WORKFLOW, DEPOT_WORKFLOW)
JOB_ID = "task-runner-native-smoke"
AGGREGATE_ID = "aggregate-01-repository-integrity"
SCOPE_CONDITION = (
    "needs.change-scope.outputs.ci-global == 'true' || "
    "needs.change-scope.outputs.ci-tooling == 'true' || "
    "needs.change-scope.outputs.deps == 'true'"
)
SKIP_CONDITION = (
    "${{ needs.change-scope.outputs.ci-global == 'false' && "
    "needs.change-scope.outputs.ci-tooling == 'false' && "
    "needs.change-scope.outputs.deps == 'false' }}"
)

CHECKOUT_ACTION = "actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332"
PYTHON_ACTION = "actions/setup-python@42375524e23c412d93fb67b49958b491fce71c38"
PNPM_ACTION = "pnpm/action-setup@fc06bc1257f339d1d5d8b3a19a8cae5388b55320"
NODE_ACTION = "actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8"

EXPECTED_COMMANDS = (
    "pnpm install --frozen-lockfile",
    "pnpm run test:fabric-cli",
    "pnpm run fabric -- list",
    "python scripts/ci/check_task_runner_shadow_parity.py",
    "pnpm run fabric -- check-conflict-markers",
    "pnpm run fabric -- check-no-nul-bytes",
    "pnpm run fabric -- platform-contract:typecheck",
    "pnpm run fabric -- web:typecheck",
    "pnpm exec nx show project layer1-ingestion --json",
    "pnpm exec nx show project layer4-agents --json",
)


def _workflow(path: Path) -> dict[str, object]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), path
    return document


def _commands(job: dict[str, object]) -> tuple[str, ...]:
    commands: list[str] = []
    for step in job["steps"]:
        run = step.get("run")
        if not isinstance(run, str):
            continue
        commands.extend(line.strip() for line in run.splitlines() if line.strip())
    return tuple(commands)


def _actions(job: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        step["uses"]: step.get("with", {})
        for step in job["steps"]
        if isinstance(step, dict) and "uses" in step
    }


def test_smoke_is_native_scoped_and_pinned_in_both_providers() -> None:
    provider_commands: list[tuple[str, ...]] = []

    for path in WORKFLOWS:
        workflow = _workflow(path)
        assert "merge_group" in workflow["on"], path

        job = workflow["jobs"][JOB_ID]
        expected_runner = (
            "windows-latest" if path == GITHUB_WORKFLOW else "depot-ubuntu-latest"
        )
        assert job["runs-on"].split(" #", maxsplit=1)[0] == expected_runner, path
        assert job["timeout-minutes"] == 15, path
        assert job["needs"] == "change-scope", path
        assert job["if"] == SCOPE_CONDITION, path
        if path == GITHUB_WORKFLOW:
            assert job["defaults"]["run"]["shell"] == "pwsh", path
        else:
            assert "defaults" not in job, path
        assert job["env"] == {
            "CYPRESS_INSTALL_BINARY": "0",
            "FABRIC_LEGACY_MODE": "error",
            "NX_DAEMON": "false",
            "NX_NO_CLOUD": "true",
        }, path

        if path == GITHUB_WORKFLOW:
            job_text = yaml.safe_dump(job, sort_keys=False)
            forbidden = re.search(r"(?i)\b(?:bash|make|wsl)\b", job_text)
            assert forbidden is None, f"{path}: forbidden Windows-job token {forbidden}"

        actions = _actions(job)
        assert CHECKOUT_ACTION in actions, path
        assert actions[PYTHON_ACTION]["python-version"] == "3.11", path
        assert actions[PNPM_ACTION]["version"] == "10.18.1", path
        assert actions[NODE_ACTION]["node-version"] == "22.22.2", path
        assert actions[NODE_ACTION]["cache"] == "pnpm", path
        assert actions[NODE_ACTION]["cache-dependency-path"] == "pnpm-lock.yaml", path

        commands = _commands(job)
        assert commands == EXPECTED_COMMANDS, path
        run_steps = [step["run"] for step in job["steps"] if "run" in step]
        assert all("\n" not in command.strip() for command in run_steps), path

        shadow_step = next(
            step for step in job["steps"] if step.get("name") == "Validate static shadow parity"
        )
        evidence_step = next(
            step
            for step in job["steps"]
            if step.get("name") == "Upload static shadow parity evidence"
        )
        assert shadow_step["if"] == "runner.os == 'Linux'", path
        assert evidence_step["if"] == "always() && runner.os == 'Linux'", path
        assert evidence_step["with"]["if-no-files-found"] == "error", path
        provider_commands.append(commands)

    assert provider_commands[0] == provider_commands[1]


def test_windows_smoke_is_skip_safe_in_repository_integrity_aggregate() -> None:
    for path in WORKFLOWS:
        workflow = _workflow(path)
        aggregate = workflow["jobs"][AGGREGATE_ID]
        assert JOB_ID in aggregate["needs"], path

        summary_step = aggregate["steps"][-1]
        assert summary_step["env"]["SKIPSAFE_TASK_RUNNER"] == SKIP_CONDITION, path
        assert (
            "--skip-safe task-runner-native-smoke=SKIPSAFE_TASK_RUNNER"
            in summary_step["run"]
        ), path
