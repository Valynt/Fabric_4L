#!/usr/bin/env python3
"""Validate GitHub branch protection required status checks against canonical config.

Also validates PR review policy (required approving reviews, dismiss-stale,
conversation resolution) against the canonical config. Conversation
resolution is the guard against merge-before-review-fix (see PR #1365 -> #1375,
where a squash merge landed before three review-thread fixes were on the
branch, requiring a follow-up PR to land the omitted fixes).

Ownership: Platform Governance. Troubleshooting: see
docs/runbooks/operational/governance-gates-troubleshooting.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable


def load_expected_checks(config_path: Path) -> list[str]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    checks = payload.get("required_status_checks")
    if not isinstance(checks, list) or not all(isinstance(item, str) for item in checks):
        raise ValueError("config.required_status_checks must be a list of strings")
    return checks


def load_conditional_checks(config_path: Path) -> list[str]:
    """Return contexts that are run/validated conditionally (PR- or path-scoped).

    These are intentionally NOT branch-protection universal required checks:
    they are not emitted on every merge-eligible run (e.g. merge_group), so
    requiring them would permanently stall merges on unrelated PRs. They must
    not appear in required_status_checks.
    """
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    entries = payload.get("conditional_status_checks")
    if entries is None:
        return []
    if not isinstance(entries, list) or not all(
        isinstance(item, dict) and isinstance(item.get("context"), str) for item in entries
    ):
        raise ValueError("config.conditional_status_checks must be a list of {context: str}")
    return [item["context"] for item in entries]


def load_gap_file(gap_path: Path | None) -> dict[str, object]:
    """Load the branch-protection migration gap ledger.

    Returns {'gaps': [], 'conditional_contexts': [], 'review_policy_gaps': []}
    when no file is given (strict mode: any declared-but-unenforced context is a
    failure).
    """
    if gap_path is None:
        return {"gaps": [], "conditional_contexts": [], "review_policy_gaps": []}
    if not gap_path.exists():
        raise ValueError(f"--gap-file {gap_path} does not exist")
    payload = json.loads(gap_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{gap_path} must contain a JSON object")
    gaps = payload.get("gaps")
    if not isinstance(gaps, list) or not all(
        isinstance(item, dict) and isinstance(item.get("context"), str) for item in gaps
    ):
        raise ValueError(str(gap_path) + ".gaps must be a list of {context: str} entries")
    conditional = payload.get("conditional_contexts")
    if conditional is not None and (
        not isinstance(conditional, list)
        or not all(isinstance(item, dict) and isinstance(item.get("context"), str) for item in conditional)
    ):
        raise ValueError(str(gap_path) + ".conditional_contexts must be a list of {context: str} entries")
    if conditional is None:
        conditional = []
    review_policy = payload.get("review_policy_gaps")
    if review_policy is not None and (
        not isinstance(review_policy, list)
        or not all(
            isinstance(item, dict) and isinstance(item.get("policy"), str) for item in review_policy
        )
    ):
        raise ValueError(str(gap_path) + ".review_policy_gaps must be a list of {policy: str} entries")
    if review_policy is None:
        review_policy = []
    return {
        "gaps": gaps,
        "conditional_contexts": conditional,
        "review_policy_gaps": review_policy,
    }


def load_enforced_checks(api_payload: dict) -> list[str]:
    required = api_payload.get("required_status_checks") or {}
    checks = required.get("checks") or []
    names = [
        item.get("context", item.get("name"))
        for item in checks
        if isinstance(item, dict) and isinstance(item.get("context", item.get("name")), str)
    ]
    return names


def compute_diff(expected: Iterable[str], enforced: Iterable[str]) -> tuple[list[str], list[str]]:
    expected_set = set(expected)
    enforced_set = set(enforced)
    missing = sorted(expected_set - enforced_set)
    unexpected = sorted(enforced_set - expected_set)
    return missing, unexpected


def load_expected_review_policy(config_path: Path) -> dict[str, object]:
    """Return expected PR review/conversation policy from canonical config.

    Keys: required_approving_review_count (int>=1), dismiss_stale_reviews (bool),
    require_code_owner_reviews (bool), required_conversation_resolution (bool).
    Returns {} when the config does not specify review policy (legacy configs).
    """
    payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    policy: dict[str, object] = {}
    rpr = payload.get("required_pull_request_reviews")
    if isinstance(rpr, dict):
        policy["required_approving_review_count"] = rpr.get("required_approving_review_count")
        policy["dismiss_stale_reviews"] = rpr.get("dismiss_stale_reviews")
        policy["require_code_owner_reviews"] = rpr.get("require_code_owner_reviews")
    if payload.get("required_conversation_resolution") is not None:
        policy["required_conversation_resolution"] = payload.get("required_conversation_resolution")
    return policy


def load_enforced_review_policy(api_payload: dict) -> dict[str, object]:
    """Extract enforced PR review/conversation policy from branch protection API payload."""
    enforced: dict[str, object] = {}
    rpr = api_payload.get("required_pull_request_reviews") or {}
    enforced["required_approving_review_count"] = rpr.get("required_approving_review_count")
    enforced["dismiss_stale_reviews"] = rpr.get("dismiss_stale_reviews")
    enforced["require_code_owner_reviews"] = rpr.get("require_code_owner_reviews")
    rcr = api_payload.get("required_conversation_resolution") or {}
    enforced["required_conversation_resolution"] = rcr.get("enabled")
    return enforced


def _drift(expected: dict, enforced: dict, key: str, fmt=str) -> str | None:
    """Return a drift message for a policy key when expected != enforced, else None."""
    exp = expected.get(key)
    enf = enforced.get(key)
    if exp is None:
        return None
    if exp is False and enf in (None, False):
        # Absence of a False expectation satisfies the intent (nothing is required).
        return None
    if enf is None:
        return f"{key}: expected {fmt(exp)} but branch protection does not enforce it"
    if exp != enf:
        return f"{key}: expected {fmt(exp)} but enforced {fmt(enf)}"
    return None


def compute_review_policy_drift(
    expected: dict[str, object], enforced: dict[str, object]
) -> list[str]:
    """Compare expected vs enforced PR review policy; return list of drift messages."""
    messages: list[str] = []
    # Review count: require at least the configured minimum.
    exp_count = expected.get("required_approving_review_count")
    enf_count = enforced.get("required_approving_review_count")
    if exp_count is not None:
        if enf_count is None or enf_count < exp_count:
            messages.append(
                f"required_approving_review_count: expected >={exp_count} but enforced {enf_count}"
            )
    for key in ("dismiss_stale_reviews", "require_code_owner_reviews"):
        msg = _drift(expected, enforced, key)
        if msg:
            messages.append(msg)
    # Conversation resolution is the guard against merge-before-review-fix (#1365 -> #1375).
    msg = _drift(expected, enforced, "required_conversation_resolution")
    if msg:
        messages.append(msg)
    return messages


def compute_gap_drift(
    expected: Iterable[str],
    enforced: Iterable[str],
    conditional: Iterable[str],
    gap: dict[str, object],
) -> tuple[list[str], list[str]]:
    """Return (fatal, warnings) for the branch-protection gap reconciliation.

    `gap` is the parsed ledger from --gap-file (or the strict/empty form when
    the flag is absent). Fatal conditions (any => exit 1):

    * a universal expected check is enforced but not declared (unexpected);
    * a universal expected check is missing from GitHub AND not represented
      in the gap ledger (unrepresented migration) -- when --gap-file is not
      given the ledger is empty, so ANY missing check is fatal;
    * the ledger references a context that is no longer declared universal
      (stale entry - the removal was either never applied or never cleaned up);
    * a conditional context leaked into required_status_checks (would stall
      the merge queue) ;
    * a conditional context is enforced by branch protection (would stall
      merges on unrelated PRs).

    Warnings are informational only (missing contexts that ARE represented in
    the ledger -- the migration is tracked and owned, not silent drift).
    """
    expected_set = set(expected)
    enforced_set = set(enforced)
    conditional_set = set(conditional)

    gaps = gap.get("gaps") or []
    gap_contexts = {entry["context"] for entry in gaps}

    fatal: list[str] = []
    warnings: list[str] = []

    unexpected = sorted(enforced_set - expected_set)
    for check in unexpected:
        fatal.append(f"enforced by GitHub but not declared universal: {check}")

    missing = sorted(expected_set - enforced_set)
    for check in missing:
        if check in gap_contexts:
            warnings.append(f"declared but not yet enforced (tracked in gap ledger): {check}")
        else:
            fatal.append(f"declared universal but not enforced and not represented in gap ledger: {check}")

    for check in sorted(gap_contexts - expected_set):
        fatal.append(f"gap ledger references a context no longer declared universal: {check}")

    leaked = sorted(conditional_set & expected_set)
    for check in leaked:
        fatal.append(
            f"conditional context must not be a universal required check: {check}"
        )

    enforced_conditional = sorted(conditional_set & enforced_set)
    for check in enforced_conditional:
        fatal.append(
            f"conditional context must not be enforced by branch protection: {check}"
        )

    return fatal, warnings


def split_policy_drift(
    policy_drift: list[str],
    gap: dict[str, object],
) -> tuple[list[str], list[str]]:
    """Split review-policy drift into (fatal, warnings) against the ledger.

    A policy drift message that matches an entry in gap.review_policy_gaps is a
    tracked, owned migration -> warning. Anything else is silent drift -> fatal.
    When the ledger is empty (strict mode, no --gap-file) every drift message is
    fatal.
    """
    documented = {
        entry["policy"]
        for entry in (gap.get("review_policy_gaps") or [])
        if isinstance(entry, dict) and isinstance(entry.get("policy"), str)
    }
    fatal: list[str] = []
    warnings: list[str] = []
    for message in policy_drift:
        key = message.split(":", 1)[0]
        if key in documented:
            warnings.append("review policy change pending (tracked in gap ledger): " + message)
        else:
            fatal.append(message)
    return fatal, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--api-response-file", type=Path)
    parser.add_argument(
        "--gap-file",
        type=Path,
        help=(
            "Branch-protection migration gap ledger. Pass it on pull_request runs so "
            "pre-existing documented gaps do not fail policy work, while new unrepresented "
            "drift does. Do NOT pass it on the daily scheduled run: any declared-but-not-"
            "enforced context then keeps the job red until the migration is actually applied."
        ),
    )
    args = parser.parse_args()

    expected = load_expected_checks(args.config)
    conditional = load_conditional_checks(args.config)

    if args.api_response_file:
        api_payload = json.loads(args.api_response_file.read_text(encoding="utf-8-sig"))
    else:
        api_payload = json.load(sys.stdin)

    enforced = load_enforced_checks(api_payload)
    missing, unexpected = compute_diff(expected, enforced)
    gap = load_gap_file(args.gap_file)
    gap_fatal, gap_warnings = compute_gap_drift(expected, enforced, conditional, gap)

    expected_policy = load_expected_review_policy(args.config)
    enforced_policy = load_enforced_review_policy(api_payload)
    policy_drift = compute_review_policy_drift(expected_policy, enforced_policy)
    policy_fatal, policy_warnings = split_policy_drift(policy_drift, gap)

    if gap_fatal or unexpected or policy_fatal:
        print("::error::Branch protection drift detected")
        print("Expected (universal) checks from config:")
        for check in sorted(set(expected)):
            print(f"  - {check}")
        print("Conditional (PR/path-scoped) checks from config:")
        if conditional:
            for check in sorted(set(conditional)):
                print(f"  - {check}")
        else:
            print("  - (none)")
        print("Enforced checks from branch protection API:")
        for check in sorted(set(enforced)):
            print(f"  - {check}")
        if gap_fatal:
            print("Gap reconciliation failures:")
            for line in gap_fatal:
                print(f"  - {line}")
        if missing:
            print("Missing expected checks:")
            for check in missing:
                print(f"  - {check}")
        if unexpected:
            print("Unexpected enforced checks:")
            for check in unexpected:
                print(f"  - {check}")
        if policy_fatal:
            print("PR review policy drift (not tracked in gap ledger):")
            for line in policy_fatal:
                print(f"  - {line}")
        if policy_drift and not policy_fatal:
            print("PR review policy drift (tracked in gap ledger):")
            for line in policy_drift:
                print(f"  - {line}")
        return 1

    if gap_warnings or policy_warnings:
        print("PASS Branch protection contract is reconciled (tracked migration pending):")
        for line in gap_warnings:
            print(f"  - {line}")
        for line in policy_warnings:
            print(f"  - {line}")
        return 0

    print("PASS Branch protection required checks exactly match canonical config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
