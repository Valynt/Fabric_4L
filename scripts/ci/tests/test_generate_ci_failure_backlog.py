from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from scripts.ci.generate_ci_failure_backlog import (
    BacklogConfig,
    aggregate_backlog,
    build_failure_records,
    build_payload,
    github_api_base,
    load_fixture_payloads,
    render_markdown,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ci_failure_backlog"


def test_github_api_base_uses_enterprise_host_api_path() -> None:
    assert (
        github_api_base("https://github.example.internal")
        == "https://github.example.internal/api/v3/repos"
    )


def test_github_api_base_supports_public_web_and_api_hosts() -> None:
    assert github_api_base("https://github.com") == "https://api.github.com/repos"
    assert github_api_base("https://api.github.com") == "https://api.github.com/repos"


def test_build_failure_records_extracts_required_fields_and_rerun_relationship() -> None:
    runs, jobs_by_run, logs_by_job = load_fixture_payloads(FIXTURE_DIR)

    records = build_failure_records(runs, jobs_by_run, logs_by_job)

    assert len(records) == 3
    first = records[0]
    assert first.workflow_name == "PR Checks"
    assert first.workflow_file == ".github/workflows/pr-checks.yml"
    assert first.job_name == "backend-tests (3.11, ubuntu-latest)"
    assert first.run_id == 101
    assert first.run_attempt == 1
    assert first.head_sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert first.branch == "feature/a"
    assert first.event == "pull_request"
    assert first.conclusion == "failure"
    assert first.started_at == "2026-05-20T10:02:00Z"
    assert first.completed_at == "2026-05-20T10:04:00Z"
    assert first.log_url.endswith("/101/job/501")
    assert first.artifact_reference.endswith("/101/artifacts")
    assert first.failure_signature == "FAILED <path>::test_resume_checkpoint - AssertionError: expected <num> got <num>"
    assert first.primary_failure_category == "test"
    assert first.rerun_relationship["is_rerun"] is False

    rerun = records[1]
    assert rerun.rerun_relationship == {
        "run_id": 102,
        "run_attempt": 2,
        "is_rerun": True,
        "previous_attempt": 1,
        "original_run_id": 102,
    }


def test_aggregate_backlog_keeps_only_recurring_signatures() -> None:
    runs, jobs_by_run, logs_by_job = load_fixture_payloads(FIXTURE_DIR)
    records = build_failure_records(runs, jobs_by_run, logs_by_job)

    backlog = aggregate_backlog(records, min_occurrences=2)

    assert len(backlog) == 1
    row = backlog[0]
    assert row["workflow_file"] == ".github/workflows/pr-checks.yml"
    assert row["job_name"] == "backend-tests (3.11, ubuntu-latest)"
    assert row["occurrences"] == 2
    assert row["primary_failure_category"] == "test"
    assert row["run_ids"] == [101, 102]
    assert row["rerun_attempts"][0]["previous_attempt"] == 1


def test_render_markdown_outputs_one_row_per_recurring_signature() -> None:
    runs, jobs_by_run, logs_by_job = load_fixture_payloads(FIXTURE_DIR)
    records = build_failure_records(runs, jobs_by_run, logs_by_job)
    backlog = aggregate_backlog(records, min_occurrences=2)

    config = BacklogConfig(
        repo="acme/fabric",
        window_days=14,
        branch=None,
        workflow_filter=None,
        include_cancelled=True,
        generated_at=dt.datetime(2026, 6, 3, tzinfo=dt.UTC),
        server_url="https://github.com",
    )
    payload = build_payload(runs, records, backlog, config)

    markdown = render_markdown(payload)

    assert "| Occurrences | Workflow | Job | Category | Signature |" in markdown
    assert markdown.count("backend-tests (3.11, ubuntu-latest)") == 1
    assert "typecheck" not in markdown


def test_cli_writes_machine_readable_json_and_markdown(tmp_path: Path) -> None:
    json_output = tmp_path / "backlog.json"
    markdown_output = tmp_path / "backlog.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/generate_ci_failure_backlog.py",
            "--fixture-dir",
            str(FIXTURE_DIR),
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
            "--include-cancelled",
            "--window-days",
            "30",
            "--generated-at",
            "2026-06-03T00:00:00Z",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "wrote 3 failure records and 1 recurring backlog rows" in result.stdout
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert len(payload["records"]) == 3
    assert len(payload["recurring_backlog"]) == 1
    assert "# CI Failure Backlog" in markdown_output.read_text(encoding="utf-8")
