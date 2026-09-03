"""Tests for deterministic task-runner shadow-parity evidence."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.ci import check_task_runner_shadow_parity as parity


def _runner(exit_codes: dict[tuple[str, ...], int]):
    def run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        key = tuple(command)
        return subprocess.CompletedProcess(command, exit_codes[key], "", "")

    return run


def test_report_requires_both_owners_to_pass_with_equal_status() -> None:
    exit_codes: dict[tuple[str, ...], int] = {}
    for task in parity.TASKS:
        exit_codes[("make", task)] = 0
        exit_codes[("corepack", "pnpm", "run", "fabric", "--", task)] = 0

    report = parity.build_report(runner=_runner(exit_codes), base_env={})

    assert report["passed"] is True
    assert report["cache_enabled"] is False
    assert [result["task"] for result in report["tasks"]] == list(parity.TASKS)
    assert all(result["artifacts"] == [] for result in report["tasks"])


def test_report_fails_closed_on_status_mismatch() -> None:
    exit_codes: dict[tuple[str, ...], int] = {}
    for task in parity.TASKS:
        exit_codes[("make", task)] = 0
        exit_codes[("corepack", "pnpm", "run", "fabric", "--", task)] = 0
    exit_codes[("corepack", "pnpm", "run", "fabric", "--", parity.TASKS[0])] = 7

    report = parity.build_report(runner=_runner(exit_codes), base_env={})

    assert report["passed"] is False
    assert report["tasks"][0]["passed"] is False


def test_main_writes_machine_readable_evidence(tmp_path: Path, monkeypatch) -> None:
    report = {
        "schema_version": 1,
        "mode": "linux-shadow",
        "cache_enabled": False,
        "passed": True,
        "tasks": [],
    }
    monkeypatch.setattr(parity, "build_report", lambda: report)
    output = tmp_path / "parity.json"

    assert parity.main(["--output", str(output)]) == 0
    assert '"passed": true' in output.read_text(encoding="utf-8")
