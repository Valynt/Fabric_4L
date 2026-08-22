from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "collect_pr_backlog_metrics.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("collect_pr_backlog_metrics", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_required_checks_reads_config(tmp_path) -> None:
    module = _load_module()
    config_path = tmp_path / "required-status-checks.json"
    config_path.write_text(
        '{"required_status_checks": ["check-a", "check-b"]}', encoding="utf-8"
    )
    assert module.load_required_checks(config_path) == ["check-a", "check-b"]


def test_load_required_checks_rejects_non_list(tmp_path) -> None:
    module = _load_module()
    config_path = tmp_path / "required-status-checks.json"
    config_path.write_text('{"required_status_checks": "check-a"}', encoding="utf-8")
    try:
        module.load_required_checks(config_path)
    except ValueError:
        return
    raise AssertionError("expected ValueError for malformed config")


def test_aggregate_check_conclusions_picks_latest_completed_per_name() -> None:
    module = _load_module()
    runs = [
        {
            "name": "behavior-tests",
            "status": "completed",
            "conclusion": "failure",
            "completed_at": "2026-06-01T00:00:00Z",
        },
        {
            "name": "behavior-tests",
            "status": "completed",
            "conclusion": "success",
            "completed_at": "2026-06-01T01:00:00Z",
        },
        {
            "name": "prod-readiness",
            "status": "in_progress",
            "conclusion": None,
            "completed_at": None,
        },
        {
            "name": "Structural Preflight",
            "status": "completed",
            "conclusion": "success",
            "completed_at": "2026-06-01T00:00:00Z",
        },
    ]
    assert module.aggregate_check_conclusions(runs) == {
        "behavior-tests": "success",
        "Structural Preflight": "success",
    }


def test_aggregate_check_conclusions_ignores_unnamed_and_unfinished() -> None:
    module = _load_module()
    runs = [
        {"name": "", "status": "completed", "conclusion": "success"},
        {"name": "still-running", "status": "queued", "conclusion": None},
        {"name": "done", "status": "completed", "conclusion": "failure"},
    ]
    assert module.aggregate_check_conclusions(runs) == {"done": "failure"}


def test_compute_pass_rate_counts_only_success() -> None:
    module = _load_module()
    checks = ["a", "b", "c", "d"]
    conclusions = {"a": "success", "b": "failure", "c": "success", "d": "skipped"}
    assert module.compute_pass_rate(checks, conclusions) == (2, 4, 50)


def test_compute_pass_rate_missing_check_is_not_passed() -> None:
    module = _load_module()
    checks = ["a", "b"]
    conclusions = {"a": "success"}
    assert module.compute_pass_rate(checks, conclusions) == (1, 2, 50)


def test_find_stale_prs_filters_by_updated_at() -> None:
    module = _load_module()
    now = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    prs = [
        {
            "number": 1,
            "title": "stale",
            "author": {"login": "alice"},
            "updatedAt": "2026-05-01T00:00:00Z",
        },
        {
            "number": 2,
            "title": "fresh",
            "author": {"login": "bob"},
            "updatedAt": "2026-06-02T00:00:00Z",
        },
    ]
    stale = module.find_stale_prs(prs, 14, now)
    assert [row["number"] for row in stale] == [1]
    assert stale[0]["author"] == "alice"


def test_find_stale_prs_accepts_rest_pulls_shape() -> None:
    """Live /pulls payloads use updated_at and user.login, not updatedAt/author."""
    module = _load_module()
    now = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
    prs = [
        {
            "number": 7,
            "title": "rest stale",
            "user": {"login": "carol"},
            "updated_at": "2026-05-01T00:00:00Z",
        },
        {
            "number": 8,
            "title": "rest fresh",
            "user": {"login": "dave"},
            "updated_at": "2026-06-02T00:00:00Z",
        },
    ]
    stale = module.find_stale_prs(prs, 14, now)
    assert [row["number"] for row in stale] == [7]
    assert stale[0]["author"] == "carol"


def test_coerce_check_runs_accepts_list_and_wrapped_shapes() -> None:
    module = _load_module()
    assert module._coerce_check_runs(
        [{"name": "a", "conclusion": "success"}]
    ) == [{"name": "a", "conclusion": "success"}]
    assert module._coerce_check_runs(
        {"check_runs": [{"name": "a"}]}
    ) == [{"name": "a"}]


def test_render_markdown_is_clean_and_structured() -> None:
    module = _load_module()
    conclusions = {
        "mandatory-security-regression": "success",
        "contract-compliance": "success",
        "prod-readiness": "failure",
        "behavior-tests": "success",
        "Layer 5 - Source Contract": "success",
        "Layer 5 - Tenant Isolation Regression": "success",
        "Layer 5 - Contract Shape Regression": "success",
        "Structural Preflight": "success",
    }
    checks = list(conclusions)
    markdown = module.render_markdown(
        repo="acme/example",
        main_sha="abc123",
        stale_days=14,
        stale_prs=[
            {
                "number": 42,
                "title": "Fix the thing",
                "author": "octocat",
                "updated_at": "2026-06-01T00:00:00Z",
            }
        ],
        required_checks=checks,
        conclusions=conclusions,
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
        runbook_url=(
            "https://github.com/acme/example/blob/main/"
            "docs/runbooks/operational/pr-backlog-health.md"
        ),
    )
    assert "7/8" in markdown
    assert "**87%**" in markdown
    assert "`main` HEAD: `abc123`" in markdown
    assert "✅ success" in markdown
    assert "❌ failure" in markdown
    assert "- #42 by @octocat: Fix the thing (updated 2026-06-01T00:00:00Z)" in markdown
    assert "\\n" not in markdown
    assert "No stale open PRs." not in markdown


def test_render_markdown_empty_state() -> None:
    module = _load_module()
    markdown = module.render_markdown(
        repo="acme/example",
        main_sha="abc123",
        stale_days=14,
        stale_prs=[],
        required_checks=["check-a"],
        conclusions={"check-a": "success"},
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
        runbook_url="https://github.com/acme/example/blob/main/docs/runbooks/operational/pr-backlog-health.md",
    )
    assert "No stale open PRs." in markdown
    assert "**1/1**" in markdown


def test_render_issue_title() -> None:
    module = _load_module()
    assert (
        module.render_issue_title(2, 87)
        == "PR Backlog Health Report — 2 stale, 87% main pass rate"
    )


def test_write_github_output_appends_key_value(tmp_path) -> None:
    module = _load_module()
    output_path = tmp_path / "github-output"
    output_path.write_text("", encoding="utf-8")
    module.write_github_output(output_path, "body_file", "C:/tmp/body.md")
    module.write_github_output(output_path, "issue_title", "Some Title")
    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert lines == ["body_file=C:/tmp/body.md", "issue_title=Some Title"]
