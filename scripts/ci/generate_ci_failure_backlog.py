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
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON_OUTPUT = ROOT / "reports" / "ci_failure_backlog.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "reports" / "ci_failure_backlog.md"

FAILURE_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}
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
    re.compile(r"(?P<sig>\b(?:Error|TypeError|ValueError|RuntimeError|ImportError|ModuleNotFoundError):\s+.+)"),
    re.compile(r"(?P<sig>\b(?:Timed out|timeout|cancelled|No space left on device|rate limit).*)", re.IGNORECASE),
    re.compile(r"(?P<sig>\b(?:ruff|mypy|pytest|vitest|playwright|eslint|tsc|vite|pnpm|docker)\b.*(?:failed|error|exit code \d+).*)", re.IGNORECASE),
    re.compile(r"(?P<sig>Process completed with exit code \d+\.)", re.IGNORECASE),
]
PATH_RE = re.compile(r"(?:[\w.-]+/)+[\w./-]+")
HEX_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<![A-Za-z_])-?\d+(?:\.\d+)?")
SPACE_RE = re.compile(r"\s+")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


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
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None


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
    return normalize_signature(f"{job.get('name', 'unknown job')} concluded {job.get('conclusion', 'unknown')}")


def categorize_failure(signature: str, job_name: str) -> str:
    haystack = f"{job_name} {signature}".lower()
    if any(token in haystack for token in ("pytest", "vitest", "playwright", "test", "assertionerror", "failed <path>", "failed tests/")):
        return "test"
    if any(token in haystack for token in ("ruff", "eslint", "prettier", "lint", "format")):
        return "lint"
    if any(token in haystack for token in ("mypy", "pyright", "tsc", "typecheck", "type error")):
        return "typecheck"
    if any(token in haystack for token in ("vite", "webpack", "build", "rollup")):
        return "build"
    if any(token in haystack for token in ("pnpm install", "pip install", "dependency", "module not found", "modulenotfounderror", "importerror")):
        return "dependency"
    if any(token in haystack for token in ("timed out", "timeout", "cancelled")):
        return "timeout"
    if any(token in haystack for token in ("docker", "postgres", "redis", "neo4j", "no space left", "rate limit", "connection refused")):
        return "infrastructure"
    if any(token in haystack for token in ("secret", "credential", "security", "gitleaks", "auth")):
        return "security"
    return "unknown"


def matrix_aware_job_name(job: Mapping[str, Any]) -> str:
    # GitHub's REST job name already includes matrix values for matrix jobs, e.g.
    # "test (3.11, ubuntu-latest)". Preserve it exactly and append explicit
    # matrix metadata only for fixtures or future API shapes that provide it.
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


def run_failed(run: Mapping[str, Any]) -> bool:
    return str(run.get("conclusion") or "").lower() in FAILURE_CONCLUSIONS


def job_failed(job: Mapping[str, Any]) -> bool:
    conclusion = str(job.get("conclusion") or "").lower()
    return conclusion in FAILURE_CONCLUSIONS


def build_failure_records(
    runs: Sequence[Mapping[str, Any]],
    jobs_by_run: Mapping[int, Sequence[Mapping[str, Any]]],
    logs_by_job: Mapping[int, str] | None = None,
) -> list[FailureRecord]:
    logs_by_job = logs_by_job or {}
    records: list[FailureRecord] = []
    for run in runs:
        run_id = int(run["id"])
        if not run_failed(run) and not any(job_failed(job) for job in jobs_by_run.get(run_id, [])):
            continue
        for job in jobs_by_run.get(run_id, []):
            if not job_failed(job):
                continue
            job_id = int(job.get("id") or 0)
            log_text = str(job.get("log_text") or logs_by_job.get(job_id) or "")
            signature = extract_failure_signature(log_text, job)
            job_name = matrix_aware_job_name(job)
            records.append(
                FailureRecord(
                    workflow_name=str(run.get("name") or run.get("workflow_name") or "unknown workflow"),
                    workflow_file=str(run.get("path") or run.get("workflow_file") or ""),
                    job_name=job_name,
                    run_id=run_id,
                    run_attempt=int(run.get("run_attempt") or 1),
                    head_sha=str(run.get("head_sha") or ""),
                    branch=str(run.get("head_branch") or ""),
                    event=str(run.get("event") or ""),
                    conclusion=str(job.get("conclusion") or run.get("conclusion") or ""),
                    started_at=str(job.get("started_at") or run.get("run_started_at") or run.get("created_at") or ""),
                    completed_at=str(job.get("completed_at") or run.get("updated_at") or ""),
                    log_url=str(job.get("logs_url") or job.get("html_url") or run.get("logs_url") or ""),
                    artifact_reference=str(run.get("artifacts_url") or job.get("artifacts_url") or ""),
                    failure_signature=signature,
                    primary_failure_category=categorize_failure(signature, job_name),
                    rerun_relationship=rerun_relationship(run),
                )
            )
    return records


def aggregate_backlog(records: Sequence[FailureRecord], min_occurrences: int = 2) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[FailureRecord]] = defaultdict(list)
    for record in records:
        key = (record.workflow_file or record.workflow_name, record.job_name, record.failure_signature)
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
                "rerun_attempts": [item.rerun_relationship for item in ordered if item.rerun_relationship.get("is_rerun")],
            }
        )
    return sorted(backlog, key=lambda row: (-row["occurrences"], row["workflow"], row["job_name"], row["failure_signature"]))


def markdown_escape(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(backlog: Sequence[Mapping[str, Any]], generated_at: str, window_days: int) -> str:
    lines = [
        "# CI Failure Backlog",
        "",
        f"Generated at: `{generated_at}`",
        f"Window: `{window_days}` days",
        "",
    ]
    if not backlog:
        lines.append("No recurring failing workflow/job signatures met the occurrence threshold.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "| Occurrences | Workflow | Job | Category | Signature | First seen | Last seen | Branches | Runs | Latest log |",
            "|---:|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in backlog:
        log_url = row.get("latest_log_url") or ""
        log_cell = f"[log]({log_url})" if log_url else ""
        lines.append(
            "| {occurrences} | {workflow} | {job} | {category} | {signature} | {first} | {last} | {branches} | {runs} | {log} |".format(
                occurrences=row.get("occurrences", 0),
                workflow=markdown_escape(row.get("workflow_file") or row.get("workflow_name") or row.get("workflow")),
                job=markdown_escape(row.get("job_name")),
                category=markdown_escape(row.get("primary_failure_category")),
                signature=markdown_escape(row.get("failure_signature")),
                first=markdown_escape(row.get("first_seen")),
                last=markdown_escape(row.get("last_seen")),
                branches=markdown_escape(", ".join(row.get("branches", []))),
                runs=markdown_escape(", ".join(str(run_id) for run_id in row.get("run_ids", []))),
                log=log_cell,
            )
        )
    return "\n".join(lines) + "\n"


def run_gh_api(path: str) -> Any:
    result = subprocess.run(["gh", "api", "--paginate", "--slurp", path], check=True, text=True, capture_output=True)
    text = result.stdout.strip()
    if not text:
        return {}
    payload = json.loads(text)
    if not isinstance(payload, list):
        return payload
    merged: dict[str, Any] = {}
    for page in payload:
        if not isinstance(page, Mapping):
            continue
        for key, value in page.items():
            if isinstance(value, list):
                merged.setdefault(key, []).extend(value)
            elif key not in merged:
                merged[key] = value
    return merged


def collect_with_gh(repo: str, window_days: int, include_logs: bool = False) -> tuple[list[Mapping[str, Any]], dict[int, list[Mapping[str, Any]]], dict[int, str]]:
    cutoff = cutoff_for_window(window_days)
    runs_path = f"/repos/{repo}/actions/runs?created=>={cutoff}&per_page=100"
    run_payload = run_gh_api(runs_path)
    runs = list(run_payload.get("workflow_runs", [])) if isinstance(run_payload, Mapping) else []
    jobs_by_run: dict[int, list[Mapping[str, Any]]] = {}
    logs_by_job: dict[int, str] = {}
    for run in runs:
        run_id = int(run["id"])
        jobs_payload = run_gh_api(f"/repos/{repo}/actions/runs/{run_id}/attempts/{int(run.get('run_attempt') or 1)}/jobs?per_page=100")
        jobs = list(jobs_payload.get("jobs", [])) if isinstance(jobs_payload, Mapping) else []
        jobs_by_run[run_id] = jobs
        if include_logs:
            for job in jobs:
                if not job_failed(job):
                    continue
                job_id = int(job.get("id") or 0)
                if not job_id:
                    continue
                try:
                    result = subprocess.run(["gh", "api", f"/repos/{repo}/actions/jobs/{job_id}/logs"], check=True, text=True, capture_output=True)
                    logs_by_job[job_id] = result.stdout
                except subprocess.CalledProcessError:
                    logs_by_job[job_id] = ""
    return runs, jobs_by_run, logs_by_job


def load_fixture_payloads(fixture_dir: Path) -> tuple[list[Mapping[str, Any]], dict[int, list[Mapping[str, Any]]], dict[int, str]]:
    runs_payload = json.loads((fixture_dir / "workflow_runs.json").read_text(encoding="utf-8"))
    runs = list(runs_payload.get("workflow_runs", runs_payload if isinstance(runs_payload, list) else []))
    jobs_by_run: dict[int, list[Mapping[str, Any]]] = {}
    logs_by_job: dict[int, str] = {}
    for jobs_file in sorted(fixture_dir.glob("jobs_*.json")):
        run_id = int(jobs_file.stem.removeprefix("jobs_"))
        payload = json.loads(jobs_file.read_text(encoding="utf-8"))
        jobs_by_run[run_id] = list(payload.get("jobs", payload if isinstance(payload, list) else []))
    logs_dir = fixture_dir / "logs"
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            logs_by_job[int(log_file.stem)] = log_file.read_text(encoding="utf-8")
    return runs, jobs_by_run, logs_by_job


def write_outputs(records: Sequence[FailureRecord], backlog: Sequence[Mapping[str, Any]], json_output: Path, markdown_output: Path, generated_at: str, window_days: int) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": generated_at,
        "window_days": window_days,
        "records": [record.to_dict() for record in records],
        "backlog": list(backlog),
    }
    json_output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_output.write_text(render_markdown(backlog, generated_at, window_days), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate recurring GitHub Actions failure backlog artifacts.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), help="GitHub repository as OWNER/REPO. Defaults to GITHUB_REPOSITORY.")
    parser.add_argument("--window-days", type=int, default=14, help="Number of days of workflow runs to collect.")
    parser.add_argument("--fixture-dir", type=Path, help="Read fixture JSON/logs instead of calling gh api.")
    parser.add_argument("--include-logs", action="store_true", help="Download failed job logs with gh api for stronger signatures.")
    parser.add_argument("--min-occurrences", type=int, default=2, help="Minimum occurrences needed for a backlog row.")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.window_days < 1:
        raise SystemExit("--window-days must be at least 1")
    if args.min_occurrences < 1:
        raise SystemExit("--min-occurrences must be at least 1")

    if args.fixture_dir:
        runs, jobs_by_run, logs_by_job = load_fixture_payloads(args.fixture_dir)
    else:
        if not args.repo:
            raise SystemExit("--repo or GITHUB_REPOSITORY is required when not using --fixture-dir")
        runs, jobs_by_run, logs_by_job = collect_with_gh(args.repo, args.window_days, args.include_logs)

    records = build_failure_records(runs, jobs_by_run, logs_by_job)
    backlog = aggregate_backlog(records, args.min_occurrences)
    generated_at = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    write_outputs(records, backlog, args.json_output, args.markdown_output, generated_at, args.window_days)
    print(f"wrote {len(records)} failure records and {len(backlog)} recurring backlog rows")
    print(f"json: {args.json_output}")
    print(f"markdown: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
