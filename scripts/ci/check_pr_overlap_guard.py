#!/usr/bin/env python3
"""Guard against risky change overlap across recently merged PRs."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

DEFAULT_BASE_BRANCH = "main"
DEFAULT_LOOKBACK = 15
DEFAULT_THRESHOLD = 0.45
REQUIRED_SECTION = "Why overlap is expected"
STRICT_PREFIX = "packages/shared/src/value_fabric/shared/"

ALLOWLIST: dict[str, str] = {
    "Makefile": "High-frequency operational updates are expected and low-risk.",
    "sdk/python/tests/**": "SDK test files frequently overlap when adding coverage.",
    "docs/**": "Documentation churn is expected and should not block delivery.",
    "docs/reliability/**": "Release/readiness docs often change together across PRs.",
    ".github/workflows/**": "Workflow maintenance can legitimately overlap in coordinated release windows.",
}


@dataclass(frozen=True)
class OverlapResult:
    number: int
    title: str
    overlap_ratio: float
    shared_files: list[str]


def _run_json(cmd: list[str]) -> object:
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def _match_allowlisted(path: str) -> bool:
    if path.startswith(STRICT_PREFIX):
        return False
    return any(fnmatch(path, pattern) for pattern in ALLOWLIST)


def _filtered(paths: Iterable[str]) -> set[str]:
    return {p for p in paths if p and not _match_allowlisted(p)}


def _files_for_pr(repo: str, number: int) -> set[str]:
    data = _run_json(["gh", "api", f"repos/{repo}/pulls/{number}/files", "--paginate"])
    return {item["filename"] for item in data if item.get("filename")}


def _merged_prs(repo: str, base: str, lookback: int, exclude: int) -> list[dict[str, object]]:
    """Fetch recently merged PRs using the read-only `gh pr list` command.

    The previous implementation used `gh api search/issues` with a `-number:`
    negation qualifier, which is not supported by that endpoint and caused a
    404/empty-result failure. `gh pr list --state merged` is read-only,
    paginates internally, and works for forked PRs because the PR number is
    scoped to the target repository.
    """
    # Fetch one extra so excluding the current PR still yields `lookback` items.
    limit = lookback + 1
    try:
        data = _run_json(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repo,
                "--state",
                "merged",
                "--base",
                base,
                "--limit",
                str(limit),
                "--json",
                "number,title",
            ]
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"PR overlap guard: could not list merged PRs ({exc}). Skipping history check.")
        return []

    items: list[dict[str, object]] = []
    for pr in data:
        number = int(pr.get("number", 0))
        if number == exclude:
            continue
        items.append({"number": number, "title": str(pr.get("title") or "")})
        if len(items) >= lookback:
            break
    return items


def evaluate(
    incoming_files: set[str],
    history: list[tuple[int, str, set[str]]],
    threshold: float,
) -> list[OverlapResult]:
    incoming = _filtered(incoming_files)
    flagged: list[OverlapResult] = []
    for number, title, changed in history:
        candidate = _filtered(changed)
        if not candidate:
            continue
        shared = sorted(incoming & candidate)
        if not shared:
            continue
        ratio = len(shared) / max(1, len(incoming))
        if ratio >= threshold:
            flagged.append(
                OverlapResult(number=number, title=title, overlap_ratio=ratio, shared_files=shared)
            )
    return sorted(flagged, key=lambda x: x.overlap_ratio, reverse=True)


def _has_required_section(body: str) -> bool:
    pattern = rf"(?ims)^##+\s*{re.escape(REQUIRED_SECTION)}\s*$\n+(.*?)(?=^##+\s|\Z)"
    match = re.search(pattern, body or "")
    return bool(match and match.group(1).strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr-number", type=int, default=int(os.environ.get("PR_NUMBER", "0")))
    parser.add_argument("--base", default=os.environ.get("PR_BASE_REF", DEFAULT_BASE_BRANCH))
    parser.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--pr-body-file", type=Path)
    args = parser.parse_args()

    if not args.repo or args.pr_number <= 0:
        print("PR overlap guard skipped: missing repository or PR number.")
        return 0

    incoming = _files_for_pr(args.repo, args.pr_number)
    merged = _merged_prs(args.repo, args.base, args.lookback, args.pr_number)
    history: list[tuple[int, str, set[str]]] = []
    for pr in merged:
        number = int(pr["number"])
        title = str(pr.get("title") or "")
        files = _files_for_pr(args.repo, number)
        history.append((number, title, files))

    flagged = evaluate(incoming, history, args.threshold)
    if not flagged:
        print("PR overlap guard passed: no unusual overlap detected.")
        return 0

    print("High overlap detected against recently merged PRs:")
    for item in flagged:
        print(f"- #{item.number} ({item.overlap_ratio:.0%}) {item.title}")
        for path in item.shared_files:
            reason = ALLOWLIST.get(path, "")
            suffix = f" [allowlisted: {reason}]" if reason else ""
            print(f"    - {path}{suffix}")

    body = ""
    if args.pr_body_file and args.pr_body_file.exists():
        body = args.pr_body_file.read_text(encoding="utf-8")
    elif os.environ.get("PR_BODY"):
        body = os.environ["PR_BODY"]

    if _has_required_section(body):
        print(f"Required section present: '{REQUIRED_SECTION}'.")
        return 0

    print(f"Missing required PR section with explanation: '{REQUIRED_SECTION}'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
