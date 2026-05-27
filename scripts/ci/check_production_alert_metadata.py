#!/usr/bin/env python3
"""Fail if production alerts omit runbook URL or on-call owner metadata."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RULE_FILES = (
    REPO_ROOT / "monitoring/alerting/layer-sli-rules-production.yml",
)


def main() -> int:
    violations: list[str] = []

    for rule_file in RULE_FILES:
        if not rule_file.exists():
            violations.append(f"missing rules file: {rule_file.relative_to(REPO_ROOT)}")
            continue

        payload = yaml.safe_load(rule_file.read_text(encoding="utf-8")) or {}
        for group in payload.get("groups", []):
            for rule in group.get("rules", []):
                alert_name = rule.get("alert", "<unnamed>")
                labels = rule.get("labels") or {}
                annotations = rule.get("annotations") or {}

                if labels.get("environment") != "production":
                    continue

                if not labels.get("oncall_owner"):
                    violations.append(f"{rule_file.relative_to(REPO_ROOT)}:{alert_name} missing labels.oncall_owner")
                if not annotations.get("runbook_url"):
                    violations.append(f"{rule_file.relative_to(REPO_ROOT)}:{alert_name} missing annotations.runbook_url")

    if violations:
        print("Production alert metadata check failed:", file=sys.stderr)
        for violation in violations:
            print(f" - {violation}", file=sys.stderr)
        return 1

    print("Production alert metadata check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
