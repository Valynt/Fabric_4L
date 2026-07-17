#!/usr/bin/env python3
"""Validate GitHub branch protection required status checks against canonical config."""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--api-response-file", type=Path)
    args = parser.parse_args()

    expected = load_expected_checks(args.config)

    if args.api_response_file:
        api_payload = json.loads(args.api_response_file.read_text(encoding="utf-8"))
    else:
        api_payload = json.load(sys.stdin)

    enforced = load_enforced_checks(api_payload)
    missing, unexpected = compute_diff(expected, enforced)

    if missing or unexpected:
        print("::error::Branch protection required status checks mismatch detected")
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
        return 1

    print("PASS Branch protection required checks exactly match canonical config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
