#!/usr/bin/env python3
"""Collect PR backlog health report metrics.

This script replaces fragile inline bash in the ``pr-backlog-health`` workflow.
It aggregates GitHub check runs across all pages of the ``check-runs`` API,
loads the authoritative required-check list from ``config/ci/required-status-checks.json``,
computes the main-branch pass rate, finds stale open PRs, and renders a clean
Markdown issue body. It supports offline fixture inputs so the behaviour is
deterministically testable without network access.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_REQUIRED_CHECKS_CONFIG = "config/ci/required-status-checks.json"
DEFAULT_USER_AGENT = "value-fabric-pr-backlog-health"
API_VERSION = "2022-11-28"

# Task-status values that mark a check run as finished. GitHub reports
# "completed" for concluded runs; anything else is still in flight.
COMPLETED_STATUSES = {"completed"}


@dataclass(frozen=True)
class MetricsConfig:
    repo: str
    token: str
    server_url: str = "https://github.com"
    stale_days: int = 14
    main_sha: str = ""
    required_checks_config: Path = DEFAULT_REQUIRED_CHECKS_CONFIG
    check_runs_file: Path | None = None
    prs_file: Path | None = None
    body_output: Path | None = None
    github_output: Path | None = None


def github_api_base(server_url: str) -> str:
    """Return the API base URL for a GitHub server URL."""
    server = urllib.parse.urlparse(server_url.rstrip("/"))
    if not server.scheme or not server.netloc:
        raise ValueError(f"Invalid GitHub server URL: {server_url}")

    if server.netloc == "api.github.com":
        return urllib.parse.urlunparse(
            (server.scheme, server.netloc, "/repos", "", "", "")
        )
    if server.netloc == "github.com":
        return "https://api.github.com/repos"
    return urllib.parse.urlunparse(
        (server.scheme, server.netloc, "/api/v3/repos", "", "", "")
    )


def next_link(link_header: str | None) -> str | None:
    """Extract the ``rel="next"`` URL from a GitHub Link header."""
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        start = section.find("<")
        end = section.find(">")
        if start != -1 and end != -1 and end > start:
            return section[start + 1 : end]
    return None


def api_get(url: str, token: str) -> tuple[dict[str, Any], str | None]:
    """GET a GitHub API URL, returning ``(payload, next_page_url)``."""
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": DEFAULT_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            link_header = response.headers.get("Link")
            return payload, next_link(link_header)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed with {exc.code}: {body}") from exc


def fetch_paginated(url: str, token: str, list_key: str) -> list[dict[str, Any]]:
    """Fetch every page of a paginated GitHub collection."""
    items: list[dict[str, Any]] = []
    while url:
        payload, url = api_get(url, token)
        values = payload.get(list_key, [])
        if isinstance(values, list):
            items.extend(values)
    return items


def load_required_checks(path: Path) -> list[str]:
    """Load the authoritative required-status-checks list from a JSON file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    checks = payload.get("required_status_checks")
    if not isinstance(checks, list):
        raise ValueError("required_status_checks must be a list")
    parsed: list[str] = []
    for item in checks:
        if not isinstance(item, str) or not item:
            raise ValueError("each required status check must be a non-empty string")
        parsed.append(item)
    if not parsed:
        raise ValueError("required_status_checks must be a non-empty list")
    return parsed


def _completed_at(run: dict[str, Any]) -> datetime:
    rawhave = run.get("completed_at")
    return (
        datetime.fromisoformat(rawhave.replace("Z", "+00:00"))
        if isinstance(rawhave, str) and rawhave
        else datetime.min.replace(tzinfo=UTC)
    )


def aggregate_check_conclusions(runs: list[dict[str, Any]]) -> dict[str, str]:
    """Map each check name to the latest completed conclusion.

    Ignores unfinished (in_progress/queued) runs and runs without a name.
    When a check appears multiple times, the most recently completed run wins.
    """
    latest: dict[str, tuple[datetime, str]] = {}
    for run in runs:
        name = run.get("name")
        if not isinstance(name, str) or not name:
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status not in COMPLETED_STATUSES or not isinstance(conclusion, str):
            continue
        completed = _completed_at(run)
        current = latest.get(name)
        if current is None or completed > current[0]:
            latest[name] = (completed, conclusion)
    return {name: conclusion for name, (_, conclusion) in latest.items()}


def compute_pass_rate(
    checks: list[str], conclusions: dict[str, str]
) -> tuple[int, int, int]:
    """Return ``(passed, total, percent)`` for the required checks.

    The percent uses floor division of ``passed * 100 / total`` so that
    7/8 renders as 87%, matching how the report has traditionally presented it.
    """
    passed = sum(1 for check in checks if conclusions.get(check) == "success")
    total = len(checks)
    percent = passed * 100 // total if total else 0
    return passed, total, percent


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def find_stale_prs(
    prs: list[dict[str, Any]], stale_days: int, now: datetime
) -> list[dict[str, str]]:
    """Return a list of open PRs not updated within ``stale_days``.

    Each returned row has ``number``, ``title``, ``author`` and ``updated_at``.
    Comparison is done in UTC.
    """
    now = now.astimezone(UTC)
    cutoff = now - timedelta(days=stale_days)
    stale: list[dict[str, str]] = []
    for pr in prs:
        number = pr.get("number")
        if not isinstance(number, int):
            continue
        updated = _parse_utc(pr.get("updatedAt"))
        if updated is None:
            continue
        if updated.astimezone(UTC) < cutoff:
            author_raw = pr.get("author") or {}
            author = (
                author_raw.get("login") if isinstance(author_raw, dict) else None
            )
            stale.append(
                {
                                "number": number,
                    "title": _parse_str(pr.get("title"), ""),
                    "author": _parse_str(author, "unknown"),
                    "updated_at": pr["updatedAt"],
                }
            )
    return stale


def _parse_str(value: Any, default: str) -> str:
    return value if isinstance(value, str) else default


def _coerce_check_runs(data: Any) -> list[dict[str, Any]]:
    """Accept either a bare list of check runs or a ``{"check_runs": [...]}`` wrapper."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        value = data.get("check_runs")
        if isinstance(value, list):
            return value
    raise ValueError("check-runs payload must be a list or a check_runs object")


def render_markdown(
    repo: str,
    main_sha: str,
    stale_days: int,
    stale_prs: list[dict[str, str]],
    required_checks: list[str],
    conclusions: dict[str, str],
    generated_at: datetime,
    runbook_url: str,
) -> str:
    """Render the report body as Markdown."""
    passed, total, _percent = compute_pass_rate(required_checks, conclusions)

    lines: list[str] = []
    lines.append("## PR Backlog Health Report")
    lines.append("")
    lines.append("Automated weekly report generated by the `pr-backlog-health` workflow.")
    lines.append("")
    lines.append(f"- Generation time (UTC): `{generated_at.astimezone(UTC).isoformat()}`")
    lines.append(f"- Repository: `{repo}`")
    lines.append(f"- `main` HEAD: `{main_sha}`")
    lines.append(f"- Staleness threshold: `{stale_days}` days")
    lines.append("")
    lines.append("## Required-check pass rate")
    lines.append("")
    lines.append(f"**{passed}/{total}** required checks passing on `main` "
                     f"(**{_pass_percent(passed, total)}%**).")
    lines.append("")
    lines.append("| Check | Conclusion |")
    lines.append("| --- | --- |")

    for check in required_checks:
        conclusion = conclusions.get(check)
        if conclusion is None:
            icon = "—"
            label = "missing"
        elif conclusion == "success":
            icon = "✅"
            label = "success"
        elif conclusion in {"failure", "timed_out", "action_required", "cancelled"}:
            icon = "❌"
            label = conclusion
        else:
            icon = "—"
            label = conclusion
        lines.append(f"| {_md_escape(check)} | {icon} {_md_escape(label)} |")
    lines.append("")

    lines.append("## Open PRs")
    lines.append("")
    if stale_prs:
        lines.append(f"**{len(stale_prs)}** stale open PR (not updated in "
                     f">={stale_days} days):")
        lines.append("")
        for pr in stale_prs:
            lines.append(
                f"- #{_md_escape(pr['number'])} by @{_md_escape(pr['author'])}: "
                f"{_md_escape(pr['title'])} "
                f"(updated {pr['updated_at']})"
            )
    else:
        lines.append("No stale open PRs.")
    lines.append("")
    lines.append(f"See the [runbook]({runbook_url}) for how to use this report.")
    lines.append("")
    return "\n".join(lines)


def _pass_percent(passed: int, total: int) -> int:
    return passed * 100 // total if total else 0


def _md_escape(value: str) -> str:
    return str(value).replace("|", "\\|")


def fetch_check_runs(repo: str, sha: str, server_url: str, token: str) -> list[dict[str, Any]]:
    """Fetch all check runs for a commit across every page."""
    owner_repo = urllib.parse.quote(repo, safe="/")
    url = (
        f"{github_api_base(server_url)}/{owner_repo}/commits/"
        f"{urllib.parse.quote(sha, safe='')}/check-runs?per_page=100"
    )
    return fetch_paginated(url, token, "check_runs")


def fetch_open_pulls(repo: str, server_url: str, token: str) -> list[dict[str, Any]]:
    """Fetch all open pull requests across every page.

    The pulls endpoint returns a bare JSON array, so we page through the link
    headers manually and aggregate arrays rather than a named collection key.
    """
    owner_repo = urllib.parse.quote(repo, safe="/")
    url = (
        f"{github_api_base(server_url)}/{owner_repo}/pulls"
        f"?state=open&per_page=100"
    )
    items: list[dict[str, Any]] = []
    while url:
        page, url = _page_payload(url, token)
        if isinstance(page, list):
            items.extend(item for item in page if isinstance(item, dict))
    return items


def _page_payload(url: str, token: str) -> tuple[Any, str | None]:
    """GET a URL and return ``(payload, next_page_url)`` for any payload shape."""
    payload, next_url = api_get(url, token)
    return payload, next_url


def load_json_file(path: Path | None) -> Any:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def collect_metrics(config: MetricsConfig) -> dict[str, Any]:
    """Collect and compile the full report payload (offline or live)."""
    required_checks = load_required_checks(config.required_checks_config)

    if config.check_runs_file is not None:
        runs_payload = load_json_file(config.check_runs_file)
        assert runs_payload is not None
        runs = _coerce_check_runs(runs_payload)
    else:
        runs = fetch_check_runs(config.repo, config.main_sha, config.server_url, config.token)

    if config.prs_file is not None:
        prs_payload = load_json_file(config.prs_file)
        raw_prs = prs_payload if isinstance(prs_payload, list) else prs_payload.get("items", [])
    else:
        raw_prs = fetch_open_pulls(config.repo, config.server_url, config.token)

    conclusions = aggregate_check_conclusions(runs)
    passed, total, percent = compute_pass_rate(required_checks, conclusions)
    now = datetime.now(UTC)
    stale_prs = find_stale_prs(raw_prs, config.stale_days, now)

    runbook_url = (
        f"{config.server_url.rstrip('/')}/{config.repo}/blob/main/"
        "docs/runbooks/operational/pr-backlog-health.md"
    )

    return {
        "repo": config.repo,
        "main_sha": config.main_sha,
        "stale_days": config.stale_days,
        "required_checks": required_checks,
        "conclusions": conclusions,
        "stale_prs": stale_prs,
        "passed": passed,
        "total": total,
        "percent": percent,
        "generated_at": now,
        "runbook_url": runbook_url,
        "issue_title": render_issue_title(len(stale_prs), percent),
    }


def render_issue_title(stale_count: int, pass_rate: int) -> str:
    """Render the issue title for the report."""
    return (
        f"PR Backlog Health Report — {stale_count} stale, "
        f"{pass_rate}% main pass rate"
    )


def write_github_output(output_path: Path, key: str, value: str) -> None:
    """Append a ``key=value`` line to a GitHub action output file."""
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name GitHub repository")
    parser.add_argument("--token", default=None, help="GitHub token (default: GITHUB_TOKEN/GH_TOKEN env)")
    parser.add_argument("--server-url", default="https://github.com", help="GitHub server base URL")
    parser.add_argument("--stale-days", type=int, default=14, help="days without update to consider a PR stale")
    parser.add_argument("--main-sha", required=True, help="full HEAD SHA of main to query for check runs")
    parser.add_argument("--required-checks-config", type=Path, default=DEFAULT_REQUIRED_CHECKS_CONFIG)
    parser.add_argument("--check-runs-file", type=Path, default=None, help="offline JSON fixture for check runs")
    parser.add_argument("--prs-file", type=Path, default=None, help="offline JSON fixture for open pull requests")
    parser.add_argument("--body-output", type=Path, default=None, help="write rendered Markdown body here")
    parser.add_argument("--github-output", type=Path, default=None, help="write key=value outputs here")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    token = args.token or None
    if token is None:
        import os

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("error: a GitHub token is required (--token or GITHUB_TOKEN/GH_TOKEN env)", file=sys.stderr)
        return 2

    config = MetricsConfig(
        repo=args.repo,
        token=token,
        server_url=args.server_url,
        stale_days=args.stale_days,
        main_sha=args.main_sha,
        required_checks_config=args.required_checks_config,
        check_runs_file=args.check_runs_file,
        prs_file=args.prs_file,
        body_output=args.body_output,
        github_output=args.github_output,
    )

    metrics = collect_metrics(config)
    body = render_markdown(
        repo=metrics["repo"],
        main_sha=metrics["main_sha"],
        stale_days=metrics["stale_days"],
        stale_prs=metrics["stale_prs"],
        required_checks=metrics["required_checks"],
        conclusions=metrics["conclusions"],
        generated_at=metrics["generated_at"],
        runbook_url=metrics["runbook_url"],
    )

    if config.body_output is not None:
        config.body_output.write_text(body, encoding="utf-8")

    if config.github_output is not None:
        write_github_output(config.github_output, "body_file", str(config.body_output) if config.body_output else "")
        write_github_output(config.github_output, "issue_title", metrics["issue_title"])
        write_github_output(config.github_output, "stale_count", str(len(metrics["stale_prs"])))
        write_github_output(config.github_output, "pass_rate", str(metrics["percent"]))
        write_github_output(config.github_output, "main_sha", metrics["main_sha"])

    if config.github_output is None and config.body_output is None:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())