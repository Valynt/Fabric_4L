from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "generate_ci_backlog.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_ci_backlog", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_failed_job_with_later_successful_attempt_is_flaky_with_recovery_counts() -> None:
    module = _load_module()
    executions = [
        module.JobExecution(
            signature=module.JobSignature("123", "unit", "abc", module.EventContext(event="pull_request", pull_request="7")),
            conclusion="failure",
            status="completed",
            run_id=10,
            run_attempt=1,
            job_id=100,
            completed_at="2026-06-01T10:00:00Z",
        ),
        module.JobExecution(
            signature=module.JobSignature("123", "unit", "abc", module.EventContext(event="pull_request", pull_request="7")),
            conclusion="success",
            status="completed",
            run_id=10,
            run_attempt=2,
            job_id=101,
            completed_at="2026-06-01T10:05:00Z",
        ),
    ]

    report = module.generate_backlog(executions)

    assert report.recovered_flaky_failures == 1
    assert report.flaky_failures_tested_by_rerun == 1
    assert report.entries[0].category == "flaky test"
    assert report.entries[0].has_rerun_recovery_evidence is True


def test_failure_without_rerun_is_not_marked_flaky_by_default() -> None:
    module = _load_module()
    signature = module.JobSignature("123", "unit", "abc", module.EventContext(event="pull_request"))
    report = module.generate_backlog(
        [
            module.JobExecution(
                signature=signature,
                conclusion="failure",
                status="completed",
                run_id=10,
                run_attempt=1,
                job_id=100,
                completed_at="2026-06-01T10:00:00Z",
            )
        ]
    )

    assert report.entries[0].category == "real regression"
    assert report.recovered_flaky_failures == 0
    assert report.flaky_failures_tested_by_rerun == 0


def test_owner_override_can_explicitly_mark_flaky_without_rerun_evidence() -> None:
    module = _load_module()
    signature = module.JobSignature("123", "unit", "abc", module.EventContext(event="pull_request"))
    report = module.generate_backlog(
        [
            module.JobExecution(
                signature=signature,
                conclusion="failure",
                status="completed",
                run_id=10,
                run_attempt=1,
                job_id=100,
                completed_at="2026-06-01T10:00:00Z",
            )
        ],
        {signature.key(): module.OwnerOverride(category="flaky test", owner="qa-owner")},
    )

    assert report.entries[0].category == "flaky test"
    assert report.entries[0].owner == "qa-owner"
    assert report.recovered_flaky_failures == 0
    assert report.flaky_failures_tested_by_rerun == 0


def test_same_job_and_sha_in_different_event_contexts_do_not_cross_recover() -> None:
    module = _load_module()
    executions = [
        module.JobExecution(
            signature=module.JobSignature("123", "unit", "abc", module.EventContext(event="pull_request", pull_request="7")),
            conclusion="failure",
            status="completed",
            run_id=10,
            run_attempt=1,
            job_id=100,
            completed_at="2026-06-01T10:00:00Z",
        ),
        module.JobExecution(
            signature=module.JobSignature("123", "unit", "abc", module.EventContext(event="push", ref="refs/heads/main")),
            conclusion="success",
            status="completed",
            run_id=11,
            run_attempt=1,
            job_id=101,
            completed_at="2026-06-01T10:05:00Z",
        ),
    ]

    report = module.generate_backlog(executions)

    assert len(report.entries) == 1
    assert report.entries[0].category == "real regression"
    assert report.recovered_flaky_failures == 0


def test_cli_outputs_flaky_recovery_numerator_and_denominator_in_json_and_markdown(tmp_path: Path) -> None:
    payload = {
        "workflow_runs": [
            {
                "id": 10,
                "workflow_id": 123,
                "name": "PR Checks",
                "event": "pull_request",
                "head_sha": "abcdef",
                "run_attempt": 1,
                "created_at": "2026-06-01T10:00:00Z",
                "jobs": [{"id": 100, "name": "unit", "conclusion": "failure", "completed_at": "2026-06-01T10:01:00Z"}],
            },
            {
                "id": 10,
                "workflow_id": 123,
                "name": "PR Checks",
                "event": "pull_request",
                "head_sha": "abcdef",
                "run_attempt": 2,
                "created_at": "2026-06-01T10:05:00Z",
                "jobs": [{"id": 101, "name": "unit", "conclusion": "success", "completed_at": "2026-06-01T10:06:00Z"}],
            },
        ]
    }
    input_path = tmp_path / "runs.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    json_result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(input_path), "--format", "json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    json_payload = json.loads(json_result.stdout)
    assert json_payload["flaky_recovery"]["recovered_flaky_failures"] == 1
    assert json_payload["flaky_recovery"]["flaky_failures_tested_by_rerun"] == 1

    markdown_result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(input_path), "--format", "markdown"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "recovered flaky failures / flaky failures tested by rerun" in markdown_result.stdout
    assert "| recovered flaky failures / flaky failures tested by rerun | 1 | 1 | 100.0% |" in markdown_result.stdout
