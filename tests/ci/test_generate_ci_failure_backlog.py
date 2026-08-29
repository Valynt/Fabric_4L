from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "generate_ci_failure_backlog.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_ci_failure_backlog", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _config(module, **overrides):
    defaults = dict(
        repo="acme/example",
        window_days=7,
        branch=None,
        workflow_filter=None,
        include_cancelled=False,
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
        server_url="https://github.com",
    )
    defaults.update(overrides)
    return module.BacklogConfig(**defaults)


def test_window_filters_runs_older_than_reporting_window() -> None:
    module = _load_module()
    config = _config(module)  # generated_at 2026-06-03, window 7d -> start 2026-05-27
    runs = [
        {"id": 1, "created_at": "2026-06-02T10:00:00Z", "conclusion": "failure"},
        {"id": 2, "created_at": "2026-05-20T10:00:00Z", "conclusion": "failure"},
    ]

    kept = module.filter_backlog_runs(
        runs,
        workflow_filter=config.workflow_filter,
        include_cancelled=config.include_cancelled,
        window_start=config.window_start,
    )

    assert [run["id"] for run in kept] == [1]


def test_actions_runs_url_supports_public_github_and_ghes() -> None:
    module = _load_module()

    public_url = module.actions_runs_url(_config(module))
    assert public_url.startswith("https://api.github.com/repos/acme/example/actions/runs?")
    assert "created=%3E=2026-05-27" in public_url or "created=%3E%3D2026-05-27" in public_url

    ghes_url = module.actions_runs_url(
        _config(module, server_url="https://github.enterprise.example")
    )
    assert ghes_url.startswith(
        "https://github.enterprise.example/api/v3/repos/acme/example/actions/runs?"
    )


def test_include_cancelled_adds_cancelled_runs_and_jobs() -> None:
    module = _load_module()
    runs = [
        {
            "id": 1,
            "name": "Nightly",
            "path": ".github/workflows/nightly.yml",
            "created_at": "2026-06-02T13:00:00Z",
            "head_branch": "main",
            "head_sha": "abc123",
            "event": "schedule",
            "conclusion": "cancelled",
            "run_attempt": 1,
        },
    ]
    jobs_by_run = {
        1: [
            {
                "id": 10,
                "name": "unit",
                "conclusion": "cancelled",
                "started_at": "2026-06-02T13:00:00Z",
                "completed_at": "2026-06-02T13:01:00Z",
            }
        ]
    }

    records = module.build_failure_records(
        runs, jobs_by_run, include_cancelled=True
    )
    assert len(records) == 1
    assert records[0].conclusion == "cancelled"

    records_excluded = module.build_failure_records(
        runs, jobs_by_run, include_cancelled=False
    )
    assert records_excluded == []


def test_recurring_aggregation_deduplicates_by_workflow_job_signature() -> None:
    module = _load_module()
    runs = [
        {
            "id": 1,
            "name": "PR Checks",
            "path": ".github/workflows/pr-checks.yml",
            "created_at": "2026-06-01T10:00:00Z",
            "head_branch": "feature/x",
            "head_sha": "abc123",
            "event": "pull_request",
            "conclusion": "failure",
            "run_attempt": 1,
        },
        {
            "id": 2,
            "name": "PR Checks",
            "path": ".github/workflows/pr-checks.yml",
            "created_at": "2026-06-02T10:00:00Z",
            "head_branch": "feature/y",
            "head_sha": "def456",
            "event": "pull_request",
            "conclusion": "failure",
            "run_attempt": 1,
        },
    ]
    shared_failure = "FAILED src/accounts/test_auth.py - AssertionError: expected 2 got 1"
    jobs_by_run = {
        1: [
            {
                "id": 10,
                "name": "backend-tests",
                "conclusion": "failure",
                "started_at": "2026-06-01T10:01:00Z",
                "completed_at": "2026-06-01T10:02:00Z",
                "log_text": shared_failure,
            }
        ],
        2: [
            {
                "id": 20,
                "name": "backend-tests",
                "conclusion": "failure",
                "started_at": "2026-06-02T10:01:00Z",
                "completed_at": "2026-06-02T10:02:00Z",
                "log_text": shared_failure,
            }
        ],
    }

    records = module.build_failure_records(runs, jobs_by_run, include_cancelled=False)
    backlog = module.aggregate_backlog(records, min_occurrences=2)

    assert len(backlog) == 1
    row = backlog[0]
    assert row["occurrences"] == 2
    assert row["workflow_file"] == ".github/workflows/pr-checks.yml"
    assert row["job_name"] == "backend-tests"
    assert row["run_ids"] == [1, 2]


def test_collect_from_github_only_fetches_jobs_for_failed_runs() -> None:
    module = _load_module()
    config = _config(module)

    runs = [
        {"id": 1, "name": "Success", "conclusion": "success"},
        {"id": 2, "name": "Failure", "conclusion": "failure"},
        {"id": 3, "name": "Cancelled", "conclusion": "cancelled"},
    ]

    fetched_jobs = []

    def fake_fetch_runs(_cfg):
        return runs

    def fake_fetch_jobs(repo, run_id, run_attempt, server_url, token):
        fetched_jobs.append(run_id)
        return [{"id": f"j{run_id}", "name": "job", "conclusion": "failure"}]

    module.fetch_workflow_runs = fake_fetch_runs
    module.fetch_jobs_for_run = fake_fetch_jobs

    collected, jobs_by_run, _ = module.collect_from_github(
        config, "token", include_logs=False
    )

    assert [run["id"] for run in collected] == [2]
    assert fetched_jobs == [2]
    assert 2 in jobs_by_run


def test_collect_from_github_max_failed_runs_caps_fetched_jobs() -> None:
    module = _load_module()
    config = _config(module)

    runs = [
        {"id": 1, "name": "Failure", "conclusion": "failure"},
        {"id": 2, "name": "Failure", "conclusion": "failure"},
        {"id": 3, "name": "Failure", "conclusion": "failure"},
    ]

    fetched_jobs = []

    def fake_fetch_runs(_cfg):
        return runs

    def fake_fetch_jobs(repo, run_id, run_attempt, server_url, token):
        fetched_jobs.append(run_id)
        return [{"id": f"j{run_id}", "name": "job", "conclusion": "failure"}]

    module.fetch_workflow_runs = fake_fetch_runs
    module.fetch_jobs_for_run = fake_fetch_jobs

    collected, jobs_by_run, _ = module.collect_from_github(
        config, "token", include_logs=False, max_failed_runs=2
    )

    assert [run["id"] for run in collected] == [1, 2]
    assert fetched_jobs == [1, 2]


def test_cli_generated_at_flag_makes_window_deterministic(tmp_path: Path) -> None:
    runs = {
        "workflow_runs": [
            {
                "id": 1,
                "name": "PR Checks",
                "path": ".github/workflows/pr-checks.yml",
                "run_attempt": 1,
                "head_sha": "abc123",
                "head_branch": "main",
                "event": "push",
                "conclusion": "failure",
                "created_at": "2026-05-20T10:00:00Z",
            }
        ]
    }
    jobs_file = {
        "jobs": [
            {
                "id": 10,
                "name": "backend-tests",
                "conclusion": "failure",
                "started_at": "2026-05-20T10:01:00Z",
                "completed_at": "2026-05-20T10:02:00Z",
                "log_text": "FAILED src/test_thing.py - AssertionError: expected 1 got 0",
            }
        ]
    }
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "workflow_runs.json").write_text(json.dumps(runs), encoding="utf-8")
    (fixture_dir / "jobs_1.json").write_text(json.dumps(jobs_file), encoding="utf-8")

    # A reference clock close to the run keeps the run inside the 30-day window.
    json_output = tmp_path / "out.json"
    markdown_output = tmp_path / "out.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--fixture-dir",
            str(fixture_dir),
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
            "--window-days",
            "30",
            "--generated-at",
            "2026-05-25T00:00:00Z",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "wrote 1 failure records" in result.stdout
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert len(payload["records"]) == 1
    assert "# CI Failure Backlog" in markdown_output.read_text(encoding="utf-8")
