#!/usr/bin/env python3
"""Enforce PR size policy with generated-file awareness.

Classifies a PR by net additions (excluding generated/lockfile/docs-only paths)
into small / medium / large. Large PRs require a `**Size justification:**` field
in the PR body explaining why the change could not be split. Generated-only and
docs-only PRs are exempt.

Companion to scripts/ci/check_pr_governance_fields.py. Wired into pr-checks.yml
alongside the governance impact fields gate.

Rationale (from PR review #1374-#1384): several PRs self-described as "small"
while introducing +2600-3000 lines. A size policy makes the contract between
author and reviewer explicit without banning large changes.

Ownership: Platform Governance. Troubleshooting: see
docs/runbooks/operational/governance-gates-troubleshooting.md.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Size thresholds (net additions after exclusions). Tuned to repo history:
# the median backend PR is < 400 additions; > 1000 is rare and warrants a
# split justification.
SMALL_MAX = 200
MEDIUM_MAX = 1000

# Paths excluded from the size count: generated artifacts, lockfiles, and
# auto-regenerated clients. A PR that only touches these is "generated-only".
EXCLUDED_PREFIXES = (
    "contracts/openapi/",
    "contracts/jsonschema/",
    "packages/platform-contract/src/typescript/generated/",
    "apps/web/src/api/generated/",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
    "go.sum",
    "signoff-evidence/",
    "artifacts/",
)

SIZE_JUSTIFICATION_LABEL = "Size justification"
# Placeholder values that should be rejected as non-justifications.
# Includes the stock PR template instruction text (so an untouched
# template cannot pass the size gate). The template wraps instructions
# in an HTML comment so the author replaces it with a real rationale.
PLACEHOLDER_VALUES = {
    "",
    "tbd",
    "todo",
    "pending",
    "?",
    "<fill me in>",
    "n/a",
    "none",
}
# Reject any value that is entirely an HTML comment (e.g. the untouched
# template instruction block). Matched case-insensitively.
_HTML_COMMENT_RE = re.compile(r"^\s*<!--.*-->\s*$", re.DOTALL | re.IGNORECASE)


def is_placeholder_justification(value: str) -> bool:
    """Return True if the value is a placeholder, not a real justification."""
    return value.casefold() in PLACEHOLDER_VALUES or bool(_HTML_COMMENT_RE.match(value))


def _git_numstat(base_ref: str) -> dict[str, int]:
    """Return a {path: additions} map from ``git diff --numstat``.

    Used as a fallback when the GitHub event payload lacks per-file
    statistics (the ``pull_request`` event body carries aggregate
    ``additions`` but not the ``files`` array with per-file stats).
    Computing the diff from the checked-out repo lets us subtract
    generated-file additions that the size policy excludes, instead of
    returning the unfiltered aggregate total (which would misclassify
    generated-heavy PRs as large).
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", "--no-renames", base_ref],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode != 0:
        return {}
    stats: dict[str, int] = {}
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        additions_str, _, path = parts
        if additions_str == "-":
            continue  # binary file
        try:
            stats[path] = int(additions_str)
        except ValueError:
            continue
    return stats


def parse_additions(payload: dict, env_changed: str) -> tuple[int, set[str]]:
    """Return (net_additions, relevant_changed_files)."""
    pr = payload.get("pull_request") or {}
    additions = int(pr.get("additions") or 0)
    changed = {
        str(path).strip()
        for path in pr.get("changed_files_list", [])
        if str(path).strip()
    }
    if not changed and env_changed:
        changed = {item.strip() for item in env_changed.split() if item.strip()}

    relevant: set[str] = set()
    excluded_additions = 0
    # If the payload carries per-file stats, subtract excluded file additions.
    files = pr.get("files") or []
    if files:
        for f in files:
            path = str(f.get("filename") or "").strip()
            if not path:
                continue
            if is_excluded(path):
                excluded_additions += int(f.get("additions") or 0)
            else:
                relevant.add(path)
        net = max(0, additions - excluded_additions)
        return net, relevant

    # Fallback: the pull_request event body carries aggregate additions but
    # not the per-file stats array. Use git diff --numstat against the base
    # ref to get per-file additions so excluded (generated/lockfile) paths
    # are subtracted. If git is unavailable or the base ref is unknown,
    # fall back to filtering by path membership only (aggregate additions,
    # relevant files) — this over-counts but never under-counts.
    base_ref = _base_ref(payload)
    if base_ref:
        numstat = _git_numstat(base_ref)
        if numstat:
            for path, file_adds in numstat.items():
                if is_excluded(path):
                    excluded_additions += file_adds
                else:
                    relevant.add(path)
            net = max(0, additions - excluded_additions)
            return net, relevant

    # Last resort: set membership only (cannot subtract generated additions).
    relevant = {p for p in changed if not is_excluded(p)}
    return additions, relevant


def _base_ref(payload: dict) -> str:
    """Extract the base ref to diff against from the GitHub event payload."""
    pr = payload.get("pull_request") or {}
    base = pr.get("base") or {}
    return str(base.get("ref") or "").strip() or ""


def is_excluded(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def classify(net_additions: int) -> str:
    if net_additions <= SMALL_MAX:
        return "small"
    if net_additions <= MEDIUM_MAX:
        return "medium"
    return "large"


def extract_field_value(body: str, label: str) -> str | None:
    # Match Markdown bold (**label:**) or italic (*label:*) field headers,
    # optionally preceded by a bullet (- or *). Allows 1-2 asterisks on
    # each side so the PR template's `**Size justification:**` format
    # parses correctly. Captures the text after the header.
    pattern = re.compile(
        rf"(?mi)^[-*]?\s*\*{{1,2}}{re.escape(label)}:?\*{{1,2}}\s*(.+?)\s*$"
    )
    match = pattern.search(body)
    return match.group(1).strip() if match else None


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH not set; skipping PR size policy check.")
        return 0

    payload = json.loads(Path(event_path).read_text(encoding="utf-8-sig"))
    if "pull_request" not in payload:
        print("No pull_request payload found; skipping PR size policy check.")
        return 0

    net_additions, relevant = parse_additions(payload, os.environ.get("CHANGED_FILES", ""))
    size = classify(net_additions)
    pr = payload.get("pull_request") or {}
    title = str(pr.get("title") or "")
    body = str(pr.get("body") or "")

    print(f"PR size: {size} ({net_additions} net additions across {len(relevant)} relevant files)")

    if not relevant:
        print("No non-generated file changes detected; PR is generated-only and exempt from size policy.")
        return 0

    if size != "large":
        return 0

    justification = extract_field_value(body, SIZE_JUSTIFICATION_LABEL)
    if justification is None:
        print(
            f"ERROR: Large PR ({net_additions} additions) is missing the required "
            f"**{SIZE_JUSTIFICATION_LABEL}:** field in the PR body.",
            file=sys.stderr,
        )
        print(
            "Explain why this change could not be split into smaller PRs, or split it. "
            "Large PRs are not banned, but the author-reviewer contract must be explicit.",
            file=sys.stderr,
        )
        print(f"PR title: {title}", file=sys.stderr)
        return 1

    if is_placeholder_justification(justification):
        print(
            f"ERROR: Large PR has a placeholder **{SIZE_JUSTIFICATION_LABEL}:** value: "
            f"{justification!r}. Provide a concrete rationale.",
            file=sys.stderr,
        )
        return 1

    print(f"Large PR justification accepted: {justification}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
