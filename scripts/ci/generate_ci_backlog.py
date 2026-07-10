#!/usr/bin/env python3
"""Generate a CI failure backlog from GitHub Actions workflow/job execution data.

The generator groups job executions by workflow id, job name, head SHA, and a
normalized event context.  A failed job signature is classified as ``flaky test``
only when either:

* a later run attempt/rerun for the same workflow/job/head SHA/event context
  succeeded, or
* an owner override explicitly sets the category to ``flaky test``.

Input is intentionally permissive so it can consume saved ``gh api`` responses,
small test fixtures, or already-normalized job records.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

FAILED_CONCLUSIONS = {"failure", "timed_out", "startup_failure", "action_required"}
SUCCESS_CONCLUSIONS = {"success"}
DEFAULT_FAILURE_CATEGORY = "real regression"
FLAKY_CATEGORY = "flaky test"


@dataclass(frozen=True, order=True)
class ExecutionOrder:
    timestamp: str
    run_id: int
    run_attempt: int
    job_id: int


@dataclass(frozen=True)
class EventContext:
    event: str = "unknown"
    head_branch: str = ""
    base_branch: str = ""
    ref: str = ""
    pull_request: str = ""

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "EventContext":
        event = _text(
            raw.get("event") or raw.get("event_name") or raw.get("github_event") or "unknown"
        )
        pull_request = raw.get("pull_request") or raw.get("pr") or raw.get("pull_request_number")
        if isinstance(pull_request, Mapping):
            pull_request = pull_request.get("number") or pull_request.get("id")
        return cls(
            event=event,
            head_branch=_text(raw.get("head_branch") or raw.get("branch") or raw.get("source_branch")),
            base_branch=_text(raw.get("base_branch") or raw.get("target_branch")),
            ref=_text(raw.get("ref") or raw.get("head_ref")),
            pull_request=_text(pull_request),
        )

    def key(self) -> str:
        parts = {"event": self.event}
        if self.head_branch:
            parts["head_branch"] = self.head_branch
        if self.base_branch:
            parts["base_branch"] = self.base_branch
        if self.ref:
            parts["ref"] = self.ref
        if self.pull_request:
            parts["pull_request"] = self.pull_request
        return json.dumps(parts, sort_keys=True, separators=(",", ":"))

    def label(self) -> str:
        parts = [self.event]
        if self.pull_request:
            parts.append(f"PR #{self.pull_request}")
        if self.head_branch:
            parts.append(f"head={self.head_branch}")
        if self.base_branch:
            parts.append(f"base={self.base_branch}")
        if self.ref:
            parts.append(f"ref={self.ref}")
        return ", ".join(parts)


@dataclass(frozen=True)
class JobSignature:
    workflow_id: str
    job_name: str
    head_sha: str
    event_context: EventContext

    def key(self) -> str:
        return "|".join((self.workflow_id, self.job_name, self.head_sha, self.event_context.key()))


@dataclass(frozen=True)
class JobExecution:
    signature: JobSignature
    conclusion: str
    status: str
    run_id: int
    run_attempt: int
    job_id: int
    workflow_name: str = ""
    run_url: str = ""
    job_url: str = ""
    started_at: str = ""
    completed_at: str = ""

    @property
    def order(self) -> ExecutionOrder:
        return ExecutionOrder(
            timestamp=_sortable_timestamp(self.completed_at or self.started_at),
            run_id=self.run_id,
            run_attempt=self.run_attempt,
            job_id=self.job_id,
        )


@dataclass(frozen=True)
class OwnerOverride:
    category: str = ""
    owner: str = ""
    blocking_status: str = ""
    remediation_link: str = ""
    notes: str = ""

    @property
    def explicitly_flaky(self) -> bool:
        return self.category.strip().lower() == FLAKY_CATEGORY


@dataclass
class BacklogEntry:
    workflow_id: str
    workflow_name: str
    job_name: str
    head_sha: str
    event_context: str
    category: str
    failure_count: int
    failed_run_urls: list[str]
    rerun_tested_failures: int
    recovered_flaky_failures: int
    owner: str = ""
    blocking_status: str = ""
    remediation_link: str = ""
    notes: str = ""
    override_category: str = ""
    has_rerun_recovery_evidence: bool = False


@dataclass
class BacklogReport:
    entries: list[BacklogEntry]
    recovered_flaky_failures: int
    flaky_failures_tested_by_rerun: int

    @property
    def flaky_recovery_rate(self) -> float:
        if self.flaky_failures_tested_by_rerun == 0:
            return 0.0
        return self.recovered_flaky_failures / self.flaky_failures_tested_by_rerun

    def to_dict(self) -> dict[str, Any]:
        return {
            "flaky_recovery": {
                "recovered_flaky_failures": self.recovered_flaky_failures,
                "flaky_failures_tested_by_rerun": self.flaky_failures_tested_by_rerun,
                "rate": self.flaky_recovery_rate,
                "label": "recovered flaky failures / flaky failures tested by rerun",
            },
            "entries": [asdict(entry) for entry in self.entries],
        }

    def to_markdown(self) -> str:
        numerator = self.recovered_flaky_failures
        denominator = self.flaky_failures_tested_by_rerun
        percent = f"{self.flaky_recovery_rate * 100:.1f}%" if denominator else "n/a"
        lines = [
            "# CI Failure Backlog",
            "",
            "## Flaky recovery",
            "",
            "| KPI | Numerator | Denominator | Rate |",
            "| --- | ---: | ---: | ---: |",
            f"| recovered flaky failures / flaky failures tested by rerun | {numerator} | {denominator} | {percent} |",
            "",
            "## Failure signatures",
            "",
            "| Workflow ID | Workflow | Job | Head SHA | Event context | Category | Failures | "
            "Rerun-tested | Recovered | Owner | Blocking | Remediation |",
            "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
        for entry in self.entries:
            lines.append(
                "| "
                + " | ".join(
                    _md_cell(value)
                    for value in (
                        entry.workflow_id,
                        entry.workflow_name,
                        entry.job_name,
                        entry.head_sha[:12],
                        entry.event_context,
                        entry.category,
                        str(entry.failure_count),
                        str(entry.rerun_tested_failures),
                        str(entry.recovered_flaky_failures),
                        entry.owner,
                        entry.blocking_status,
                        entry.remediation_link,
                    )
                )
                + " |"
            )
        return "\n".join(lines)


def generate_backlog(
    executions: Iterable[JobExecution], overrides: Mapping[str, OwnerOverride] | None = None
) -> BacklogReport:
    overrides = overrides or {}
    grouped: dict[str, list[JobExecution]] = defaultdict(list)
    for execution in executions:
        grouped[execution.signature.key()].append(execution)

    entries: list[BacklogEntry] = []
    recovered_total = 0
    rerun_tested_total = 0

    for signature_key, signature_executions in sorted(grouped.items()):
        ordered = sorted(signature_executions, key=lambda item: item.order)
        failed = [item for item in ordered if item.conclusion in FAILED_CONCLUSIONS]
        if not failed:
            continue

        first = ordered[0]
        override = overrides.get(signature_key) or OwnerOverride()
        rerun_tested_failures = 0
        recovered_flaky_failures = 0
        for failure in failed:
            later = [candidate for candidate in ordered if candidate.order > failure.order]
            if not later:
                continue
            rerun_tested_failures += 1
            if any(candidate.conclusion in SUCCESS_CONCLUSIONS for candidate in later):
                recovered_flaky_failures += 1

        has_recovery_evidence = recovered_flaky_failures > 0
        category = override.category or DEFAULT_FAILURE_CATEGORY
        if has_recovery_evidence or override.explicitly_flaky:
            category = FLAKY_CATEGORY

        if category == FLAKY_CATEGORY:
            rerun_tested_total += rerun_tested_failures
            recovered_total += recovered_flaky_failures

        entries.append(
            BacklogEntry(
                workflow_id=first.signature.workflow_id,
                workflow_name=first.workflow_name,
                job_name=first.signature.job_name,
                head_sha=first.signature.head_sha,
                event_context=first.signature.event_context.label(),
                category=category,
                failure_count=len(failed),
                failed_run_urls=[url for url in (_best_url(item) for item in failed) if url],
                rerun_tested_failures=rerun_tested_failures,
                recovered_flaky_failures=recovered_flaky_failures,
                owner=override.owner,
                blocking_status=override.blocking_status,
                remediation_link=override.remediation_link,
                notes=override.notes,
                override_category=override.category,
                has_rerun_recovery_evidence=has_recovery_evidence,
            )
        )

    entries.sort(key=lambda entry: (entry.category != FLAKY_CATEGORY, -entry.failure_count, entry.workflow_id, entry.job_name))
    return BacklogReport(
        entries=entries,
        recovered_flaky_failures=recovered_total,
        flaky_failures_tested_by_rerun=rerun_tested_total,
    )


def load_executions(path: Path) -> list[JobExecution]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(_iter_executions(payload))


def load_overrides(path: Path | None) -> dict[str, OwnerOverride]:
    if not path:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_overrides = payload.get("overrides", payload) if isinstance(payload, Mapping) else payload
    overrides: dict[str, OwnerOverride] = {}
    if isinstance(raw_overrides, Mapping):
        iterator = raw_overrides.items()
        for key, value in iterator:
            if isinstance(value, str):
                overrides[str(key)] = OwnerOverride(category=value)
            elif isinstance(value, Mapping):
                overrides[str(key)] = _owner_override(value)
        return overrides
    if isinstance(raw_overrides, list):
        for item in raw_overrides:
            if not isinstance(item, Mapping):
                continue
            key = _override_key(item)
            if key:
                overrides[key] = _owner_override(item)
    return overrides


def _iter_executions(payload: Any) -> Iterable[JobExecution]:
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_executions(item)
        return
    if not isinstance(payload, Mapping):
        return

    if "workflow_runs" in payload:
        yield from _iter_executions(payload["workflow_runs"])
        return
    if "runs" in payload:
        yield from _iter_executions(payload["runs"])
        return
    if "jobs" in payload and _looks_like_run(payload):
        run = payload
        for job in payload.get("jobs") or []:
            if isinstance(job, Mapping):
                yield _execution_from_job(job, run)
        return
    if "jobs" in payload:
        yield from _iter_executions(payload["jobs"])
        return
    if _looks_like_job(payload):
        yield _execution_from_job(payload, payload)


def _execution_from_job(job: Mapping[str, Any], run: Mapping[str, Any]) -> JobExecution:
    workflow_run = job.get("workflow_run") if isinstance(job.get("workflow_run"), Mapping) else {}
    run_metadata = {**workflow_run, **run}
    merged = {**run_metadata, **job}
    event_context = EventContext.from_mapping(merged)
    signature = JobSignature(
        workflow_id=_text(
            run_metadata.get("workflow_id")
            or run_metadata.get("workflow_database_id")
            or run_metadata.get("workflow_name")
            or run_metadata.get("name")
            or job.get("workflow_id")
            or job.get("workflow_name")
            or "unknown"
        ),
        job_name=_text(job.get("name") or job.get("job_name") or job.get("job") or "unknown"),
        head_sha=_text(merged.get("head_sha") or merged.get("headSha") or merged.get("sha") or "unknown"),
        event_context=event_context,
    )
    return JobExecution(
        signature=signature,
        conclusion=_text(job.get("conclusion") or merged.get("conclusion")).lower(),
        status=_text(job.get("status") or merged.get("status")).lower(),
        run_id=_int(job.get("run_id") or run_metadata.get("run_id") or run_metadata.get("id")),
        run_attempt=_int(job.get("run_attempt") or run_metadata.get("run_attempt") or merged.get("attempt"), default=1),
        job_id=_int(job.get("id") or job.get("job_id")),
        workflow_name=_text(run_metadata.get("workflow_name") or run_metadata.get("name")),
        run_url=_text(run_metadata.get("html_url") or run_metadata.get("run_url")),
        job_url=_text(job.get("html_url") or job.get("job_url")),
        started_at=_text(job.get("started_at") or run_metadata.get("created_at") or run_metadata.get("run_started_at")),
        completed_at=_text(job.get("completed_at") or run_metadata.get("updated_at")),
    )


def _owner_override(raw: Mapping[str, Any]) -> OwnerOverride:
    return OwnerOverride(
        category=_text(raw.get("category") or raw.get("failure_category")),
        owner=_text(raw.get("owner")),
        blocking_status=_text(raw.get("blocking_status") or raw.get("blocking")),
        remediation_link=_text(raw.get("remediation_link") or raw.get("remediation")),
        notes=_text(raw.get("notes")),
    )


def _override_key(raw: Mapping[str, Any]) -> str:
    if raw.get("signature"):
        return _text(raw.get("signature"))
    workflow_id = _text(raw.get("workflow_id"))
    job_name = _text(raw.get("job_name") or raw.get("job"))
    head_sha = _text(raw.get("head_sha") or raw.get("sha"))
    if not (workflow_id and job_name and head_sha):
        return ""
    return JobSignature(workflow_id, job_name, head_sha, EventContext.from_mapping(raw)).key()


def _looks_like_run(payload: Mapping[str, Any]) -> bool:
    return any(
        key in payload
        for key in (
            "workflow_id",
            "workflow_database_id",
            "workflow_name",
            "run_id",
            "run_attempt",
            "head_sha",
            "event",
            "html_url",
        )
    )


def _looks_like_job(payload: Mapping[str, Any]) -> bool:
    return any(key in payload for key in ("job_name", "run_attempt", "head_sha", "workflow_id")) and any(
        key in payload for key in ("conclusion", "status")
    )


def _best_url(execution: JobExecution) -> str:
    return execution.job_url or execution.run_url


def _sortable_timestamp(value: str) -> str:
    if not value:
        return "0001-01-01T00:00:00+00:00"
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).astimezone(timezone.utc).isoformat()
    except ValueError:
        return value


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _md_cell(value: Any) -> str:
    text = _text(value).replace("\n", " ")
    return text.replace("|", "\\|") or "-"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSON file containing workflow runs or job executions.")
    parser.add_argument("--owner-overrides", type=Path, help="Optional JSON category/owner overrides keyed by signature.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path, help="Write output to this path instead of stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = generate_backlog(load_executions(args.input), load_overrides(args.owner_overrides))
    rendered = json.dumps(report.to_dict(), indent=2, sort_keys=True) if args.format == "json" else report.to_markdown()
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
