from __future__ import annotations

import importlib.util
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


def test_build_backlog_filters_failures_and_renders_markdown() -> None:
    module = _load_module()
    config = module.BacklogConfig(
        repo="acme/example",
        window_days=7,
        branch="main",
        workflow_filter="PR",
        include_cancelled=False,
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
        server_url="https://github.com",
    )
    runs = [
        {
            "id": 1,
            "run_number": 10,
            "run_attempt": 1,
            "workflow_id": 100,
            "name": "PR Checks",
            "path": ".github/workflows/pr-checks.yml",
            "event": "pull_request",
            "status": "completed",
            "conclusion": "failure",
            "head_branch": "main",
            "head_sha": "abc123",
            "created_at": "2026-06-02T10:00:00Z",
            "run_started_at": "2026-06-02T10:00:00Z",
            "updated_at": "2026-06-02T10:05:00Z",
            "html_url": "https://github.com/acme/example/actions/runs/1",
            "actor": {"login": "octocat"},
            "triggering_actor": {"login": "octocat"},
        },
        {
            "id": 2,
            "run_number": 11,
            "name": "PR Checks",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-06-02T11:00:00Z",
        },
        {
            "id": 3,
            "run_number": 12,
            "name": "Smoke Gate",
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-06-02T12:00:00Z",
        },
        {
            "id": 4,
            "run_number": 13,
            "name": "PR Checks",
            "status": "completed",
            "conclusion": "cancelled",
            "created_at": "2026-06-02T13:00:00Z",
        },
    ]

    backlog = module.build_backlog(runs, config)
    markdown = module.render_markdown(backlog)

    assert backlog["summary"]["total_backlog_runs"] == 1
    assert backlog["summary"]["workflow_count"] == 1
    assert backlog["summary"]["conclusions"] == {"failure": 1}
    assert backlog["runs"][0]["duration_seconds"] == 300
    assert "# CI Failure Backlog" in markdown
    assert "PR Checks" in markdown
    assert "Smoke Gate" not in markdown


def test_actions_runs_url_supports_public_github_and_ghes() -> None:
    module = _load_module()
    config = module.BacklogConfig(
        repo="acme/example",
        window_days=7,
        branch="main",
        workflow_filter=None,
        include_cancelled=False,
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
        server_url="https://github.com",
    )

    assert module._actions_runs_url(config).startswith(
        "https://api.github.com/repos/acme/example/actions/runs?"
    )

    ghes_config = module.BacklogConfig(
        repo="acme/example",
        window_days=7,
        branch="main",
        workflow_filter=None,
        include_cancelled=False,
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
        server_url="https://github.enterprise.example",
    )

    assert module._actions_runs_url(ghes_config).startswith(
        "https://github.enterprise.example/api/v3/repos/acme/example/actions/runs?"
    )


def test_include_cancelled_adds_cancelled_runs() -> None:
    module = _load_module()
    config = module.BacklogConfig(
        repo="acme/example",
        window_days=7,
        branch=None,
        workflow_filter=None,
        include_cancelled=True,
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
        server_url="https://github.com",
    )

    backlog = module.build_backlog(
        [
            {
                "id": 1,
                "name": "Nightly",
                "status": "completed",
                "conclusion": "cancelled",
                "created_at": "2026-06-02T13:00:00Z",
            },
            {
                "id": 2,
                "name": "Nightly",
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-06-02T14:00:00Z",
            },
        ],
        config,
    )

    assert backlog["summary"]["total_backlog_runs"] == 1
    assert backlog["summary"]["conclusions"] == {"cancelled": 1}
