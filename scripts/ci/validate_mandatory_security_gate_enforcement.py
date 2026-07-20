#!/usr/bin/env python3
"""Validate the effective GitHub merge control for mandatory security regression."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "config/ci/mandatory-security-regression-contract.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _enabled(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return value is True or (isinstance(value, dict) and value.get("enabled") is True)


def validate(protection: dict[str, Any], rulesets: list[dict[str, Any]], contract: dict[str, Any]) -> list[str]:
    """Return every unsafe effective-setting deviation from the checked-in contract."""
    errors: list[str] = []
    canonical = contract["canonical_check"]
    expected_context = canonical["check_context"]
    expected_app_id = canonical["github_app_id"]
    policy = contract["branch_protection"]

    required_status_checks = protection.get("required_status_checks") or {}
    if required_status_checks.get("strict") is not policy["strict"]:
        errors.append("required status checks must enforce strict up-to-date branch status")

    checks = required_status_checks.get("checks") or []
    matching = [
        item
        for item in checks
        if isinstance(item, dict) and item.get("context") == expected_context
    ]
    if len(matching) != 1:
        errors.append(f"required status checks must contain exactly one {expected_context!r} context")
    elif matching[0].get("app_id") != expected_app_id:
        errors.append(
            f"required context {expected_context!r} must be restricted to GitHub App {expected_app_id}"
        )

    if _enabled(protection, "enforce_admins") is not policy["enforce_administrators"]:
        errors.append("branch protection must enforce administrators")

    reviews = protection.get("required_pull_request_reviews") or {}
    if reviews.get("require_code_owner_reviews") is not policy["require_code_owner_reviews"]:
        errors.append("branch protection must require CODEOWNER reviews")
    if int(reviews.get("required_approving_review_count") or 0) < policy["required_approving_review_count"]:
        errors.append("branch protection must require the governed approving-review count")

    if _enabled(protection, "required_conversation_resolution") is not policy["require_conversation_resolution"]:
        errors.append("branch protection must require conversation resolution")

    if "allow_force_pushes" not in protection:
        errors.append("branch protection payload missing allow_force_pushes setting")
    elif _enabled(protection, "allow_force_pushes") is not policy["allow_force_pushes"]:
        errors.append("branch protection force-push setting drifted")

    if "allow_deletions" not in protection:
        errors.append("branch protection payload missing allow_deletions setting")
    elif _enabled(protection, "allow_deletions") is not policy["allow_deletions"]:
        errors.append("branch protection deletion setting drifted")

    active_rulesets = [ruleset for ruleset in rulesets if ruleset.get("enforcement") == "active"]
    if not active_rulesets:
        errors.append("repository must retain an active branch ruleset")
    for ruleset in active_rulesets:
        bypass_actors = ruleset.get("bypass_actors") or []
        if bypass_actors:
            errors.append(f"active ruleset {ruleset.get('name', '<unnamed>')!r} has bypass actors")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch-protection-file", required=True, type=Path)
    parser.add_argument("--ruleset-file", required=True, type=Path)
    args = parser.parse_args()

    protection = _load(args.branch_protection_file)
    rulesets = _load(args.ruleset_file)
    contract = _load(CONTRACT_PATH)
    if not isinstance(protection, dict) or not isinstance(rulesets, list) or not isinstance(contract, dict):
        print("::error::invalid enforcement validation input", file=sys.stderr)
        return 1

    errors = validate(protection, rulesets, contract)
    if errors:
        for error in errors:
            print(f"::error::{error}", file=sys.stderr)
        return 1

    context = contract["canonical_check"]["check_context"]
    print(f"PASS mandatory security enforcement: {context}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
