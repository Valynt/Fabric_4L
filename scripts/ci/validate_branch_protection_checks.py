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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--api-response-file", type=Path)
    args = parser.parse_args()

    expected = load_expected_checks(args.config)

    if args.api_response_file:
        api_payload = json.loads(args.api_response_file.read_text(encoding="utf-8-sig"))
    else:
        api_payload = json.load(sys.stdin)

    enforced = load_enforced_checks(api_payload)
    missing, unexpected = compute_diff(expected, enforced)

    expected_policy = load_expected_review_policy(args.config)
    enforced_policy = load_enforced_review_policy(api_payload)
    policy_drift = compute_review_policy_drift(expected_policy, enforced_policy)

    if missing or unexpected or policy_drift:
        print("::error::Branch protection drift detected")
        print("Expected checks from config:")
        for check in sorted(set(expected)):
            print(f"  - {check}")
        print("Enforced checks from branch protection API:")
        for check in sorted(set(enforced)):
            print(f"  - {check}")
        if missing:
            print("Missing expected checks:")
            for check in missing:
                print(f"  - {check}")
        if unexpected:
            print("Unexpected enforced checks:")
            for check in unexpected:
                print(f"  - {check}")
        if policy_drift:
            print("PR review policy drift:")
            for line in policy_drift:
                print(f"  - {line}")
        return 1

    print("PASS Branch protection required checks exactly match canonical config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
