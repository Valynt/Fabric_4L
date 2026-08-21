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
PLACEHOLDER_VALUES = {"", "tbd", "todo", "pending", "?", "<fill me in>", "n/a", "none"}


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

    # Fall back to set membership when per-file stats are absent.
    relevant = {p for p in changed if not is_excluded(p)}
    return additions, relevant


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
    pattern = re.compile(rf"(?mi)^[-*]?\s*\*{re.escape(label)}:?\*\*?\s*(.+?)\s*$")
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

    if justification.casefold() in PLACEHOLDER_VALUES:
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
