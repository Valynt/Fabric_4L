#!/usr/bin/env python3
"""Generate a recurring CI failure backlog from GitHub Actions data.

The module keeps the GitHub API collection layer separate from parsing and
aggregation so tests can exercise the transformation with checked-in fixtures.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON_OUTPUT = ROOT / "reports" / "ci_failure_backlog.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "reports" / "ci_failure_backlog.md"

FAILURE_CONCLUSIONS = {
    "failure",
    "timed_out",
    "cancelled",
    "action_required",
    "startup_failure",
}
CANCELLED_CONCLUSION = "cancelled"

NOISE_PREFIXES = (
    "Run ",
    "shell:",
    "env:",
    "with:",
    "##[group]",
    "##[endgroup]",
)

SIGNATURE_PATTERNS = [
    re.compile(r"(?P<sig>FAILED\s+[^\s]+(?:\s+-\s+.+)?)", re.IGNORECASE),
    re.compile(r"(?P<sig>AssertionError: .+)", re.IGNORECASE),
    re.compile(r"(?P<sig>E\s+AssertionError: .+)", re.IGNORECASE),
    re.compile(r"(?P<sig>ERROR:\s+.+)", re.IGNORECASE),
    re.compile(
        r"(?P<sig>\b(?:Error|TypeError|ValueError|RuntimeError|ImportError|ModuleNotFoundError):\s+.+)"
    ),
    re.compile(
        r"(?P<sig>\b(?:Timed out|timeout|cancelled|No space left on device|rate limit).*)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<sig>\b(?:ruff|mypy|pytest|vitest|playwright|eslint|tsc|vite|pnpm|docker)\b.*(?:failed|error|exit code \d+).*)",
        re.IGNORECASE,
    ),
    re.compile(r"(?P<sig>Process completed with exit code \d+\.)", re.IGNORECASE),
]

PATH_RE = re.compile(r"(?:[\w.-]+/)+[\w./-]+")
HEX_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<![A-Za-z_])-?\d+(?:\.\d+)?")
SPACE_RE = re.compile(r"\s+")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclasses.dataclass(frozen=True)
class BacklogConfig:
    repo: str
    window_days: int
    branch: str | None
    workflow_filter: str | None
    include_cancelled: bool
    generated_at: dt.datetime
    server_url: str

    @property
    def window_start(self) -> dt.datetime:
        return self.generated_at - dt.timedelta(days=self.window_days)


@dataclasses.dataclass(frozen=True)
class FailureRecord:
    workflow_name: str
    workflow_file: str
    job_name: str
    run_id: int | None
    run_attempt: int | None
    head_sha: str
    branch: str
    event: str
    conclusion: str
    started_at: str
    completed_at: str
    log_url: str
    artifact_reference: str
    failure_signature: str
    primary_failure_category: str
    rerun_relationship: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def parse_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def duration_seconds(run: Mapping[str, Any]) -> int | None:
    started = parse_timestamp(str(run.get("run_started_at") or run.get("created_at") or ""))
    updated = parse_timestamp(str(run.get("updated_at") or ""))
    if not started or not updated:
        return None
    return max(0, int((updated - started).total_seconds()))


def cutoff_for_window(window_days: int, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.UTC)
    return (now - dt.timedelta(days=window_days)).date().isoformat()


def normalize_signature(text: str) -> str:
    text = ANSI_RE.sub("", text).strip()
    text = PATH_RE.sub("<path>", text)
    text = HEX_RE.sub("<sha>", text)
    text = NUMBER_RE.sub("<num>", text)
    text = SPACE_RE.sub(" ", text)
    return text[:240]


def extract_failure_signature(log_text: str, job: Mapping[str, Any]) -> str:
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith(NOISE_PREFIXES):
            continue
        clean = ANSI_RE.sub("", line)
        for pattern in SIGNATURE_PATTERNS:
            match = pattern.search(clean)
            if match:
                return normalize_signature(match.group("sig"))

    if job.get("conclusion") == "timed_out":
        return "job timed out"
    if job.get("conclusion") == "cancelled":
        return "job cancelled"

    return normalize_signature(
        f"{job.get('name', 'unknown job')} concluded {job.get('conclusion', 'unknown')}"
    )


def categorize_failure(signature: str, job_name: str) -> str:
    haystack = f"{job_name} {signature}".lower()

    if any(
        token in haystack
        for token in (
            "pytest",
            "vitest",
            "playwright",
            "test",
            "assertionerror",
            "failed <path>",
            "failed tests/",
        )
    ):
        return "test"
    if any(token in haystack for token in ("ruff", "eslint", "prettier", "lint", "format")):
        return "lint"
    if any(token in haystack for token in ("mypy", "pyright", "tsc", "typecheck", "type error")):
        return "typecheck"
    if any(token in haystack for token in ("vite", "webpack", "build", "rollup")):
        return "build"
    if any(
        token in haystack
        for token in (
            "pnpm install",
            "pip install",
            "dependency",
            "module not found",
            "modulenotfounderror",
            "importerror",
        )
    ):
        return "dependency"
    if any(token in haystack for token in ("timed out", "timeout", "cancelled")):
        return "timeout"
    if any(
        token in haystack
        for token in (
            "docker",
            "postgres",
            "redis",
            "neo4j",
            "no space left",
            "rate limit",
            "connection refused",
        )
    ):
        return "infrastructure"
    if any(token in haystack for token in ("secret", "credential", "security", "gitleaks", "auth")):
        return "security"

    return "unknown"


def matrix_aware_job_name(job: Mapping[str, Any]) -> str:
    name = str(job.get("name") or "unknown job")
    matrix = job.get("matrix")
    if isinstance(matrix, Mapping) and matrix:
        rendered = ", ".join(f"{key}={value}" for key, value in sorted(matrix.items()))
        if rendered not in name:
            return f"{name} ({rendered})"
    return name


def rerun_relationship(run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run.get("id")
    attempt = int(run.get("run_attempt") or 1)
    return {
        "run_id": run_id,
        "run_attempt": attempt,
        "is_rerun": attempt > 1,
        "previous_attempt": attempt - 1 if attempt > 1 else None,
        "original_run_id": run_id if attempt > 1 else None,
    }


def run_failed(run: Mapping[str, Any], include_cancelled: bool = True) -> bool:
    conclusion = str(run.get("conclusion") or "").lower()
    if conclusion == CANCELLED_CONCLUSION:
        return include_cancelled
    return conclusion in FAILURE_CONCLUSIONS


def job_failed(job: Mapping[str, Any], include_cancelled: bool = True) -> bool:
    conclusion = str(job.get("conclusion") or "").lower()
    if conclusion == CANCELLED_CONCLUSION:
        return include_cancelled
    return conclusion in FAILURE_CONCLUSIONS


def matches_workflow_filter(run: Mapping[str, Any], workflow_filter: str | None) -> bool:
    if not workflow_filter:
        return True
    needle = workflow_filter.casefold()
    candidates = (
        str(run.get("name") or ""),
        str(run.get("path") or ""),
        str(run.get("workflow_id") or ""),
    )
    return any(needle in candidate.casefold() for candidate in candidates)


def is_in_window(run: Mapping[str, Any], window_start: dt.datetime | None) -> bool:
    if window_start is None:
        return True
    created_at = parse_timestamp(str(run.get("created_at") or ""))
    return created_at is not None and created_at >= window_start


def filter_backlog_runs(
    runs: Iterable[Mapping[str, Any]],
    *,
    workflow_filter: str | None,
    include_cancelled: bool,
    window_start: dt.datetime | None = None,
) -> list[Mapping[str, Any]]:
    return [
        run
        for run in runs
        if is_in_window(run, window_start)
        and run_failed(run, include_cancelled=include_cancelled)
        and matches_workflow_filter(run, workflow_filter)
    ]


def normalize_run(run: Mapping[str, Any]) -> dict[str, Any]:
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
        "duration_seconds": duration_seconds(run),
        "html_url": run.get("html_url"),
        "actor": (run.get("actor") or {}).get("login"),
        "triggering_actor": (run.get("triggering_actor") or {}).get("login"),
    }


def build_failure_records(
    runs: Sequence[Mapping[str, Any]],
    jobs_by_run: Mapping[int, Sequence[Mapping[str, Any]]],
    logs_by_job: Mapping[int, str] | None = None,
    *,
    include_cancelled: bool = True,
) -> list[FailureRecord]:
    logs_by_job = logs_by_job or {}
    records: list[FailureRecord] = []

    for run in runs:
        run_id = int(run["id"])
        jobs = jobs_by_run.get(run_id, [])

        if not run_failed(run, include_cancelled=include_cancelled) and not any(
            job_failed(job, include_cancelled=include_cancelled) for job in jobs
        ):
            continue

        for job in jobs:
            if not job_failed(job, include_cancelled=include_cancelled):
                continue

            job_id = int(job.get("id") or 0)
            log_text = str(job.get("log_text") or logs_by_job.get(job_id) or "")
            signature = extract_failure_signature(log_text, job)
            job_name = matrix_aware_job_name(job)

            records.append(
                FailureRecord(
                    workflow_name=str(
                        run.get("name") or run.get("workflow_name") or "unknown workflow"
                    ),
                    workflow_file=str(run.get("path") or run.get("workflow_file") or ""),
                    job_name=job_name,
                    run_id=run_id,
                    run_attempt=int(run.get("run_attempt") or 1),
                    head_sha=str(run.get("head_sha") or ""),
                    branch=str(run.get("head_branch") or ""),
                    event=str(run.get("event") or ""),
                    conclusion=str(job.get("conclusion") or run.get("conclusion") or ""),
                    started_at=str(
                        job.get("started_at")
                        or run.get("run_started_at")
                        or run.get("created_at")
                        or ""
                    ),
                    completed_at=str(job.get("completed_at") or run.get("updated_at") or ""),
                    log_url=str(
                        job.get("logs_url")
                        or job.get("html_url")
                        or run.get("logs_url")
                        or ""
                    ),
                    artifact_reference=str(
                        run.get("artifacts_url") or job.get("artifacts_url") or ""
                    ),
                    failure_signature=signature,
                    primary_failure_category=categorize_failure(signature, job_name),
                    rerun_relationship=rerun_relationship(run),
                )
            )

    return records


def aggregate_backlog(
    records: Sequence[FailureRecord], min_occurrences: int = 2
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[FailureRecord]] = defaultdict(list)

    for record in records:
        key = (
            record.workflow_file or record.workflow_name,
            record.job_name,
            record.failure_signature,
        )
        groups[key].append(record)

    backlog: list[dict[str, Any]] = []

    for (workflow_key, job_name, signature), items in groups.items():
        if len(items) < min_occurrences:
            continue

        ordered = sorted(items, key=lambda item: item.started_at or "")
        run_ids = [item.run_id for item in ordered]

        backlog.append(
            {
                "workflow": workflow_key,
                "workflow_name": ordered[-1].workflow_name,
                "workflow_file": ordered[-1].workflow_file,
                "job_name": job_name,
                "failure_signature": signature,
                "primary_failure_category": ordered[-1].primary_failure_category,
                "occurrences": len(items),
                "first_seen": ordered[0].started_at,
                "last_seen": ordered[-1].started_at,
                "branches": sorted({item.branch for item in items if item.branch}),
                "events": sorted({item.event for item in items if item.event}),
                "run_ids": run_ids,
                "latest_log_url": ordered[-1].log_url,
                "rerun_attempts": [
                    item.rerun_relationship
                    for item in ordered
                    if item.rerun_relationship.get("is_rerun")
                ],
            }
        )

    return sorted(
        backlog,
        key=lambda row: (
            -row["occurrences"],
            row["workflow"],
            row["job_name"],
            row["failure_signature"],
        ),
    )


def build_run_summary(runs: Sequence[Mapping[str, Any]], config: BacklogConfig) -> dict[str, Any]:
    backlog_runs = [
        normalize_run(run)
        for run in filter_backlog_runs(
            (r for r in runs if config.branch is None or r.get("head_branch") == config.branch),
            workflow_filter=config.workflow_filter,
            include_cancelled=config.include_cancelled,
            window_start=config.window_start,
        )
    ]
    backlog_runs.sort(key=lambda run: str(run.get("created_at") or ""), reverse=True)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in backlog_runs:
        grouped[
            f"{run['workflow_name']} ({run.get('workflow_path') or run.get('workflow_id') or 'unknown'})"
        ].append(run)

    by_workflow: dict[str, dict[str, Any]] = {}
    for workflow_name, workflow_runs in sorted(grouped.items()):
        conclusions = Counter(str(run.get("conclusion") or "unknown") for run in workflow_runs)
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

    conclusions_total = Counter(str(run.get("conclusion") or "unknown") for run in backlog_runs)

    return {
        "total_backlog_runs": len(backlog_runs),
        "workflow_count": len(by_workflow),
        "conclusions": dict(sorted(conclusions_total.items())),
        "workflows": by_workflow,
        "runs": backlog_runs,
    }


def markdown_escape(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(payload: Mapping[str, Any]) -> str:
    metadata = payload["metadata"]
    summary = payload["summary"]
    recurring_backlog = payload["recurring_backlog"]

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
        f"- Recurring signatures: **{len(recurring_backlog)}**",
        f"- Conclusions: `{json.dumps(summary['conclusions'], sort_keys=True)}`",
        "",
    ]

    lines.extend(
        [
            "## Workflow backlog",
            "",
        ]
    )

    if not summary["workflows"]:
        lines.extend(
            [
                "No failed workflow runs matched the requested reporting window and filters.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "| Workflow | Count | Conclusions | First seen | Latest run |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for workflow_name, data in summary["workflows"].items():
            latest = data["latest_run"]
            latest_url = latest.get("html_url") or ""
            latest_label = (
                f"#{latest.get('run_number')}" if latest.get("run_number") else "run"
            )
            latest_link = (
                f"[{latest_label}]({latest_url})" if latest_url else latest_label
            )
            lines.append(
                "| "
                f"{markdown_escape(workflow_name)} | "
                f"{data['count']} | "
                f"`{json.dumps(data['conclusions'], sort_keys=True)}` | "
                f"{markdown_escape(data['first_seen_at'])} | "
                f"{latest_link} ({markdown_escape(latest.get('conclusion'))}) |"
            )
        lines.append("")

    lines.extend(
        [
            "## Recurring failure signatures",
            "",
        ]
    )

    if not recurring_backlog:
        lines.extend(
            [
                "No recurring failing workflow/job signatures met the occurrence threshold.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "| Occurrences | Workflow | Job | Category | Signature | First seen | Last seen | Branches | Runs | Latest log |",
                "|---:|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for row in recurring_backlog:
            log_url = row.get("latest_log_url") or ""
            log_cell = f"[log]({log_url})" if log_url else ""
            lines.append(
                "| {occurrences} | {workflow} | {job} | {category} | {signature} | "
                "{first} | {last} | {branches} | {runs} | {log} |".format(
                    occurrences=row.get("occurrences", 0),
                    workflow=markdown_escape(
                        row.get("workflow_file")
                        or row.get("workflow_name")
                        or row.get("workflow")
                    ),
                    job=markdown_escape(row.get("job_name")),
                    category=markdown_escape(row.get("primary_failure_category")),
                    signature=markdown_escape(row.get("failure_signature")),
                    first=markdown_escape(row.get("first_seen")),
                    last=markdown_escape(row.get("last_seen")),
                    branches=markdown_escape(", ".join(row.get("branches", []))),
                    runs=markdown_escape(
                        ", ".join(str(run_id) for run_id in row.get("run_ids", []))
                    ),
                    log=log_cell,
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Recent backlog runs",
            "",
            "| Created | Workflow | Branch | Conclusion | Run | Actor |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )

    for run in summary["runs"][:50]:
        run_url = run.get("html_url") or ""
        run_label = (
            f"#{run.get('run_number')}"
            if run.get("run_number")
            else str(run.get("id") or "run")
        )
        run_link = f"[{run_label}]({run_url})" if run_url else run_label
        lines.append(
            "| "
            f"{markdown_escape(run.get('created_at') or '')} | "
            f"{markdown_escape(run.get('workflow_name') or '')} | "
            f"{markdown_escape(run.get('branch') or '')} | "
            f"{markdown_escape(run.get('conclusion') or '')} | "
            f"{run_link} | "
            f"{markdown_escape(run.get('actor') or '')} |"
        )

    lines.append("")
    return "\n".join(lines)


def next_link(link_header: str | None) -> str | None:
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
            return payload, next_link(link_header)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed with {exc.code}: {body}") from exc


def github_api_base(server_url: str) -> str:
    server = urllib.parse.urlparse(server_url.rstrip("/"))
    if not server.scheme or not server.netloc:
        raise ValueError(f"Invalid GitHub server URL: {server_url}")

    if server.netloc == "api.github.com":
        api_host = server.netloc
        api_path = "/repos"
    elif server.netloc == "github.com":
        api_host = "api.github.com"
        api_path = "/repos"
    else:
        api_host = server.netloc
        api_path = "/api/v3/repos"

    return urllib.parse.urlunparse((server.scheme, api_host, api_path, "", "", ""))


def actions_runs_url(config: BacklogConfig) -> str:
    owner_repo = urllib.parse.quote(config.repo, safe="/")
    params = {
        "per_page": "100",
        "status": "completed",
        "created": f">={config.window_start.date().isoformat()}",
    }
    if config.branch:
        params["branch"] = config.branch

    return (
        f"{github_api_base(config.server_url)}/{owner_repo}/actions/runs?"
        f"{urllib.parse.urlencode(params)}"
    )


def fetch_paginated(url: str, token: str, list_key: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    while url:
        payload, url = api_get(url, token)
        values = payload.get(list_key, [])
        if isinstance(values, list):
            items.extend(values)

    return items


def fetch_workflow_runs(config: BacklogConfig, token: str) -> list[dict[str, Any]]:
    return fetch_paginated(actions_runs_url(config), token, "workflow_runs")


def fetch_jobs_for_run(
    repo: str, run_id: int, run_attempt: int, server_url: str, token: str
) -> list[dict[str, Any]]:
    owner_repo = urllib.parse.quote(repo, safe="/")
    url = (
        f"{github_api_base(server_url)}/{owner_repo}/actions/runs/{run_id}"
        f"/attempts/{run_attempt}/jobs?per_page=100"
    )
    return fetch_paginated(url, token, "jobs")


def fetch_job_log(repo: str, job_id: int, server_url: str, token: str) -> str:
    owner_repo = urllib.parse.quote(repo, safe="/")
    url = f"{github_api_base(server_url)}/{owner_repo}/actions/jobs/{job_id}/logs"

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
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError:
        return ""


def collect_from_github(
    config: BacklogConfig,
    token: str,
    include_logs: bool = False,
    max_failed_runs: int | None = None,
) -> tuple[list[Mapping[str, Any]], dict[int, list[Mapping[str, Any]]], dict[int, str]]:
    runs = fetch_workflow_runs(config)

    # Only failed runs can contribute to the backlog; fetching jobs for every run
    # is an N+1 cost that explodes on high-volume repositories (GitHub does not
    # support server-side conclusion filtering on the runs endpoint).
    failed_runs = [
        run for run in runs if run_failed(run, include_cancelled=config.include_cancelled)
    ]

    if max_failed_runs is not None and len(failed_runs) > max_failed_runs:
        failed_runs = failed_runs[:max_failed_runs]

    jobs_by_run: dict[int, list[Mapping[str, Any]]] = {}
    logs_by_job: dict[int, str] = {}

    for run in failed_runs:
        run_id = int(run["id"])
        run_attempt = int(run.get("run_attempt") or 1)
        jobs = fetch_jobs_for_run(config.repo, run_id, run_attempt, config.server_url, token)
        jobs_by_run[run_id] = jobs

        if include_logs:
            for job in jobs:
                if not job_failed(job, include_cancelled=config.include_cancelled):
                    continue
                job_id = int(job.get("id") or 0)
                if job_id:
                    logs_by_job[job_id] = fetch_job_log(
                        config.repo, job_id, config.server_url, token
                    )

    return failed_runs, jobs_by_run, logs_by_job


def load_fixture_payloads(
    fixture_dir: Path,
) -> tuple[list[Mapping[str, Any]], dict[int, list[Mapping[str, Any]]], dict[int, str]]:
    runs_payload = json.loads((fixture_dir / "workflow_runs.json").read_text(encoding="utf-8"))

    if isinstance(runs_payload, list):
        runs = runs_payload
    else:
        runs = list(runs_payload.get("workflow_runs", []))

    jobs_by_run: dict[int, list[Mapping[str, Any]]] = {}
    logs_by_job: dict[int, str] = {}

    for jobs_file in sorted(fixture_dir.glob("jobs_*.json")):
        run_id = int(jobs_file.stem.removeprefix("jobs_"))
        payload = json.loads(jobs_file.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            jobs_by_run[run_id] = payload
        else:
            jobs_by_run[run_id] = list(payload.get("jobs", []))

    logs_dir = fixture_dir / "logs"
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            logs_by_job[int(log_file.stem)] = log_file.read_text(encoding="utf-8")

    return runs, jobs_by_run, logs_by_job


def build_payload(
    runs: Sequence[Mapping[str, Any]],
    records: Sequence[FailureRecord],
    recurring_backlog: Sequence[Mapping[str, Any]],
    config: BacklogConfig,
) -> dict[str, Any]:
    run_summary = build_run_summary(runs, config)

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
            "source": "GitHub Actions workflow run and job metadata",
        },
        "summary": {
            "total_backlog_runs": run_summary["total_backlog_runs"],
            "workflow_count": run_summary["workflow_count"],
            "conclusions": run_summary["conclusions"],
            "workflows": run_summary["workflows"],
            "runs": run_summary["runs"],
        },
        "records": [record.to_dict() for record in records],
        "recurring_backlog": list(recurring_backlog),
    }


def write_outputs(
    payload: Mapping[str, Any],
    json_output: Path,
    markdown_output: Path,
) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    json_output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_output.write_text(render_markdown(payload), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate recurring GitHub Actions failure backlog artifacts."
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="GitHub repository as OWNER/REPO. Defaults to GITHUB_REPOSITORY.",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub token with actions:read. Not required with --fixture-dir.",
    )
    parser.add_argument(
        "--server-url",
        default=os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=14,
        help="Number of days of workflow runs to collect.",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help=(
            "Reference ISO-8601 timestamp (e.g. 2026-06-03T00:00:00Z) used to compute "
            "the reporting window. Defaults to the current time. Intended for "
            "deterministic fixture-driven runs and tests."
        ),
    )
    parser.add_argument(
        "--branch", default="all", help="Branch to report, or 'all' for all branches."
    )
    parser.add_argument(
        "--workflow-filter",
        default="",
        help="Substring filter for workflow name, path, or ID.",
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        help="Read fixture JSON/logs instead of calling the GitHub API.",
    )
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Download failed job logs for stronger signatures.",
    )
    parser.add_argument(
        "--include-cancelled",
        action="store_true",
        help="Include cancelled workflow runs and jobs in backlog.",
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=2,
        help="Minimum occurrences needed for a recurring backlog row.",
    )
    parser.add_argument(
        "--max-failed-runs",
        type=int,
        default=None,
        help=(
            "Cap the number of failed runs collected from the GitHub API. "
            "Protects scheduled runs on high-volume repositories from N+1 job "
            "fetches exhausting the time/rate budget. Defaults to unlimited."
        ),
    )
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.window_days < 1:
        raise SystemExit("--window-days must be at least 1")
    if args.min_occurrences < 1:
        raise SystemExit("--min-occurrences must be at least 1")

    branch = args.branch.strip() if args.branch else None
    if branch and branch.casefold() == "all":
        branch = None

    repo = args.repo or "fixture/repository"

    if args.generated_at:
        generated_at = parse_timestamp(args.generated_at)
        if generated_at is None:
            raise SystemExit(f"invalid --generated-at timestamp: {args.generated_at}")
    else:
        generated_at = dt.datetime.now(dt.UTC)

    config = BacklogConfig(
        repo=repo,
        window_days=args.window_days,
        branch=branch,
        workflow_filter=args.workflow_filter.strip() or None,
        include_cancelled=args.include_cancelled,
        generated_at=generated_at,
        server_url=args.server_url,
    )

    if args.fixture_dir:
        runs, jobs_by_run, logs_by_job = load_fixture_payloads(args.fixture_dir)
    else:
        if not args.repo:
            raise SystemExit("--repo or GITHUB_REPOSITORY is required when not using --fixture-dir")
        if not args.token:
            raise SystemExit("--token or GITHUB_TOKEN is required when not using --fixture-dir")
        runs, jobs_by_run, logs_by_job = collect_from_github(
            config,
            args.token,
            include_logs=args.include_logs,
            max_failed_runs=args.max_failed_runs,
        )

    filtered_runs = filter_backlog_runs(
        runs,
        workflow_filter=config.workflow_filter,
        include_cancelled=config.include_cancelled,
        window_start=config.window_start,
    )

    records = build_failure_records(
        filtered_runs,
        jobs_by_run,
        logs_by_job,
        include_cancelled=config.include_cancelled,
    )
    recurring_backlog = aggregate_backlog(records, args.min_occurrences)

    payload = build_payload(filtered_runs, records, recurring_backlog, config)
    write_outputs(payload, args.json_output, args.markdown_output)

    print(
        f"wrote {len(records)} failure records and "
        f"{len(recurring_backlog)} recurring backlog rows"
    )
    print(f"json: {args.json_output}")
    print(f"markdown: {args.markdown_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
