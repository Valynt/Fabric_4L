#!/usr/bin/env python3
"""Fail if production alerts omit runbook URL or on-call owner metadata."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RULE_FILES = (
    REPO_ROOT / "monitoring/prometheus/alerting/rules.yml",
    REPO_ROOT / "monitoring/alerting/layer-sli-rules-production.yml",
)
BANNED_RUNBOOK_HOSTS = {
    "docs.valuefabric.internal",
    "wiki.internal",
}


def _validate_runbook_url(url: str, *, rule_file: Path, alert_name: str) -> list[str]:
    violations: list[str] = []
    parsed = urlparse(url)
    if parsed.hostname in BANNED_RUNBOOK_HOSTS:
        violations.append(
            f"{rule_file.relative_to(REPO_ROOT)}:{alert_name} uses unreachable internal runbook host {parsed.hostname}"
        )
        return violations

    github_blob_prefix = "/bmsull560/Fabric_4L/blob/main/"
    if parsed.hostname == "github.com" and parsed.path.startswith(github_blob_prefix):
        relative_path = parsed.path.removeprefix(github_blob_prefix)
        if not (REPO_ROOT / relative_path).is_file():
            violations.append(
                f"{rule_file.relative_to(REPO_ROOT)}:{alert_name} runbook file not found: {relative_path}"
            )
    elif not parsed.scheme and url.endswith(".md"):
        if not (REPO_ROOT / url.lstrip("/")).is_file():
            violations.append(
                f"{rule_file.relative_to(REPO_ROOT)}:{alert_name} runbook file not found: {url}"
            )

    return violations


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

                if labels.get("environment") == "production" and not labels.get("oncall_owner"):
                    violations.append(f"{rule_file.relative_to(REPO_ROOT)}:{alert_name} missing labels.oncall_owner")
                runbook_url = annotations.get("runbook_url")
                if not runbook_url:
                    violations.append(f"{rule_file.relative_to(REPO_ROOT)}:{alert_name} missing annotations.runbook_url")
                else:
                    violations.extend(
                        _validate_runbook_url(str(runbook_url), rule_file=rule_file, alert_name=alert_name)
                    )

    if violations:
        print("Production alert metadata check failed:", file=sys.stderr)
        for violation in violations:
            print(f" - {violation}", file=sys.stderr)
        return 1

    print("Production alert metadata check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
