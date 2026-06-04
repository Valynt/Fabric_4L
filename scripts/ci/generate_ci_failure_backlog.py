#!/usr/bin/env python3
"""Generate a GitHub Actions CI failure backlog report.

The report intentionally uses only GitHub Actions run metadata so it can run with the
minimal `actions: read` permission in GitHub Actions. It writes both machine-readable JSON
and a Markdown summary suitable for uploading as workflow artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

FAILURE_CONCLUSIONS = {"failure", "timed_out", "action_required", "startup_failure"}
CANCELLED_CONCLUSION = "cancelled"


@dataclass(frozen=True)
class BacklogConfig:
    repo: str
    window_days: int
    branch: str | None
    workflow_filter: str | None
    include_cancelled: bool
    generated_at: datetime
    server_url: str

    @property
    def window_start(self) -> datetime:
        return self.generated_at - timedelta(days=self.window_days)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _duration_seconds(run: dict[str, Any]) -> int | None:
    started = _parse_datetime(run.get("run_started_at") or run.get("created_at"))
    updated = _parse_datetime(run.get("updated_at"))
    if not started or not updated:
        return None
    return max(0, int((updated - started).total_seconds()))


def _matches_workflow_filter(run: dict[str, Any], workflow_filter: str | None) -> bool:
    if not workflow_filter:
        return True
    needle = workflow_filter.casefold()
    candidates = (
        str(run.get("name") or ""),
        str(run.get("path") or ""),
        str(run.get("workflow_id") or ""),
    )
    return any(needle in candidate.casefold() for candidate in candidates)


def _is_backlog_run(run: dict[str, Any], include_cancelled: bool) -> bool:
    conclusion = run.get("conclusion")
    if conclusion in FAILURE_CONCLUSIONS:
        return True
    return include_cancelled and conclusion == CANCELLED_CONCLUSION


def _is_in_window(run: dict[str, Any], window_start: datetime | None) -> bool:
    if window_start is None:
        return True
    created_at = _parse_datetime(run.get("created_at"))
    return created_at is not None and created_at >= window_start


def filter_backlog_runs(
    runs: Iterable[dict[str, Any]],
    *,
    workflow_filter: str | None,
    include_cancelled: bool,
    window_start: datetime | None = None,
) -> list[dict[str, Any]]:
    return [
        run
        for run in runs
        if _is_in_window(run, window_start)
        and _is_backlog_run(run, include_cancelled)
        and _matches_workflow_filter(run, workflow_filter)
    ]


def normalize_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run.get("id"),
        "run_number": run.get("run_number"),
        "run_attempt": run.get("run_attempt"),
        "workflow_id": run.get("workflow_id"),
        "workflow_name": run.get("name") or "(unnamed workflow)",
        "workflow_path": run.get("path"),
        "event": run.get("event"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "branch": run.get("head_branch"),
        "head_sha": run.get("head_sha"),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "duration_seconds": _duration_seconds(run),
        "html_url": run.get("html_url"),
        "actor": (run.get("actor") or {}).get("login"),
        "triggering_actor": (run.get("triggering_actor") or {}).get("login"),
    }


def build_backlog(
    runs: Iterable[dict[str, Any]], config: BacklogConfig
) -> dict[str, Any]:
    backlog_runs = [
        normalize_run(run)
        for run in filter_backlog_runs(
            runs,
            workflow_filter=config.workflow_filter,
            include_cancelled=config.include_cancelled,
            window_start=config.window_start,
        )
    ]
    backlog_runs.sort(key=lambda run: str(run.get("created_at") or ""), reverse=True)

    by_workflow: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in backlog_runs:
        grouped[str(run["workflow_name"])].append(run)

    for workflow_name, workflow_runs in sorted(grouped.items()):
        conclusions = Counter(
            str(run.get("conclusion") or "unknown") for run in workflow_runs
        )
        branches = Counter(str(run.get("branch") or "unknown") for run in workflow_runs)
        latest = max(workflow_runs, key=lambda run: str(run.get("created_at") or ""))
        first_seen = min(str(run.get("created_at") or "") for run in workflow_runs)
        durations = [
            run["duration_seconds"]
            for run in workflow_runs
            if run.get("duration_seconds") is not None
        ]
        by_workflow[workflow_name] = {
            "count": len(workflow_runs),
            "conclusions": dict(sorted(conclusions.items())),
            "branches": dict(branches.most_common()),
            "first_seen_at": first_seen,
            "latest_run": latest,
            "average_duration_seconds": (
                round(sum(durations) / len(durations), 1) if durations else None
            ),
        }

    conclusions_total = Counter(
        str(run.get("conclusion") or "unknown") for run in backlog_runs
    )
    return {
        "metadata": {
            "repo": config.repo,
            "server_url": config.server_url,
            "generated_at": config.generated_at.isoformat().replace("+00:00", "Z"),
            "window_days": config.window_days,
            "window_start": config.window_start.isoformat().replace("+00:00", "Z"),
            "branch": config.branch or "all",
            "workflow_filter": config.workflow_filter or "all",
            "include_cancelled": config.include_cancelled,
            "source": "GitHub Actions workflow run metadata",
        },
        "summary": {
            "total_backlog_runs": len(backlog_runs),
            "workflow_count": len(by_workflow),
            "conclusions": dict(sorted(conclusions_total.items())),
        },
        "workflows": by_workflow,
        "runs": backlog_runs,
    }


def render_markdown(backlog: dict[str, Any]) -> str:
    metadata = backlog["metadata"]
    summary = backlog["summary"]
    lines = [
        "# CI Failure Backlog",
        "",
        f"**Repository:** `{metadata['repo']}`",
        f"**Generated:** {metadata['generated_at']}",
        f"**Window:** last {metadata['window_days']} day(s), starting {metadata['window_start']}",
        f"**Branch:** `{metadata['branch']}`",
        f"**Workflow filter:** `{metadata['workflow_filter']}`",
        f"**Cancelled runs included:** `{str(metadata['include_cancelled']).lower()}`",
        "",
        "## Summary",
        "",
        f"- Backlog runs: **{summary['total_backlog_runs']}**",
        f"- Affected workflows: **{summary['workflow_count']}**",
        f"- Conclusions: `{json.dumps(summary['conclusions'], sort_keys=True)}`",
        "",
    ]

    if not backlog["workflows"]:
        lines.extend(
            [
                "## Workflow backlog",
                "",
                "No failed workflow runs matched the requested reporting window and filters.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Workflow backlog",
            "",
            "| Workflow | Count | Conclusions | First seen | Latest run |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for workflow_name, data in backlog["workflows"].items():
        latest = data["latest_run"]
        latest_url = latest.get("html_url") or ""
        latest_label = (
            f"#{latest.get('run_number')}" if latest.get("run_number") else "run"
        )
        latest_link = f"[{latest_label}]({latest_url})" if latest_url else latest_label
        lines.append(
            "| "
            f"{workflow_name} | "
            f"{data['count']} | "
            f"`{json.dumps(data['conclusions'], sort_keys=True)}` | "
            f"{data['first_seen_at']} | "
            f"{latest_link} ({latest.get('conclusion')}) |"
        )

    lines.extend(
        [
            "",
            "## Recent backlog runs",
            "",
            "| Created | Workflow | Branch | Conclusion | Run | Actor |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for run in backlog["runs"][:50]:
        run_url = run.get("html_url") or ""
        run_label = (
            f"#{run.get('run_number')}"
            if run.get("run_number")
            else str(run.get("id") or "run")
        )
        run_link = f"[{run_label}]({run_url})" if run_url else run_label
        lines.append(
            "| "
            f"{run.get('created_at') or ''} | "
            f"{run.get('workflow_name') or ''} | "
            f"{run.get('branch') or ''} | "
            f"{run.get('conclusion') or ''} | "
            f"{run_link} | "
            f"{run.get('actor') or ''} |"
        )
    lines.append("")
    return "\n".join(lines)


def _api_get(url: str, token: str) -> tuple[dict[str, Any], str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "value-fabric-ci-failure-backlog-generator",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            link_header = response.headers.get("Link")
            return payload, _next_link(link_header)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API request failed with {exc.code}: {body}"
        ) from exc


def _next_link(link_header: str | None) -> str | None:
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


def _actions_runs_url(config: BacklogConfig) -> str:
    server = urllib.parse.urlparse(config.server_url.rstrip("/"))
    if not server.scheme or not server.netloc:
        raise ValueError(f"Invalid GitHub server URL: {config.server_url}")

    owner_repo = urllib.parse.quote(config.repo, safe="/")
    api_base = (
        "https://api.github.com/repos"
        if server.netloc == "github.com"
        else urllib.parse.urlunparse(
            (server.scheme, server.netloc, "/api/v3/repos", "", "", "")
        )
    )
    params = {
        "per_page": "100",
        "status": "completed",
        "created": f">={config.window_start.date().isoformat()}",
    }
    if config.branch:
        params["branch"] = config.branch
    return f"{api_base}/{owner_repo}/actions/runs?{urllib.parse.urlencode(params)}"


def fetch_workflow_runs(config: BacklogConfig, token: str) -> list[dict[str, Any]]:
    url = _actions_runs_url(config)

    runs: list[dict[str, Any]] = []
    while url:
        payload, url = _api_get(url, token)
        runs.extend(payload.get("workflow_runs", []))
    return runs


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate CI failure backlog JSON and Markdown reports."
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="Repository in owner/name form.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub token with actions:read.",
    )
    parser.add_argument(
        "--server-url",
        default=os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
    )
    parser.add_argument(
        "--window-days", type=int, default=7, help="Reporting window in days."
    )
    parser.add_argument(
        "--branch", default="main", help="Branch to report, or 'all' for all branches."
    )
    parser.add_argument(
        "--workflow-filter",
        default="",
        help="Substring filter for workflow name, path, or ID.",
    )
    parser.add_argument(
        "--include-cancelled",
        action="store_true",
        help="Include cancelled workflow runs in backlog.",
    )
    parser.add_argument(
        "--json-output", type=Path, required=True, help="Path for JSON report."
    )
    parser.add_argument(
        "--markdown-output", type=Path, required=True, help="Path for Markdown report."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.repo:
        raise SystemExit("--repo or GITHUB_REPOSITORY is required")
    if not args.token:
        raise SystemExit("--token or GITHUB_TOKEN is required")
    if args.window_days < 1:
        raise SystemExit("--window-days must be at least 1")

    branch = args.branch.strip() if args.branch else None
    if branch and branch.casefold() == "all":
        branch = None

    config = BacklogConfig(
        repo=args.repo,
        window_days=args.window_days,
        branch=branch,
        workflow_filter=args.workflow_filter.strip() or None,
        include_cancelled=args.include_cancelled,
        generated_at=datetime.now(UTC),
        server_url=args.server_url,
    )
    runs = fetch_workflow_runs(config, args.token)
    backlog = build_backlog(runs, config)
    markdown = render_markdown(backlog)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(backlog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.json_output} and {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
