#!/usr/bin/env python3
"""Validate Fabric_4L production-readiness plan foundations.

This validator intentionally verifies repository-owned foundations only. It does not claim
production PASS for external-provider controls; instead, it checks that each readiness gap has
policy, documentation, and existing implementation evidence with explicit production evidence
requirements.
"""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]

SECRET_VALUE_RE = re.compile(
    r"(?i)(client_secret|api_key|token|password|webhook|stripe|pagerduty).{0,40}"
    r"(:|=)\s*['\"]?(?!external_secret_ref|false|true|null|\[|\{|required|redacted|provider_required)[A-Za-z0-9_./+=:-]{16,}"
)


@dataclass(frozen=True)
class Gate:
    name: str
    priority: str
    policy: str
    docs: tuple[str, ...]
    evidence_patterns: tuple[str, ...]


GATES: tuple[Gate, ...] = (
    Gate(
        "enterprise_oidc_sso",
        "P0",
        "config/production-readiness/oidc_enterprise_requirements.json",
        (
            "docs/governance/production-readiness-p0-foundations.md",
            "docs/runbooks/operational/enterprise-oidc-sso-incident.md",
        ),
        ("*oidc*.py", "*oauth2*.yaml", "*test_oidc*.py"),
    ),
    Gate(
        "model_management",
        "P0",
        "config/production-readiness/model_governance_policy.json",
        (
            "docs/governance/production-readiness-p0-foundations.md",
            "docs/runbooks/operational/model-registry-governance-incident.md",
        ),
        ("*model_registry*.py", "*test_model_registry*.py"),
    ),
    Gate(
        "incident_runbooks",
        "P0",
        "config/production-readiness/compliance_control_policy.json",
        (
            "docs/governance/production-readiness-p0-foundations.md",
            "docs/runbooks/operational/enterprise-oidc-sso-incident.md",
            "docs/runbooks/operational/model-registry-governance-incident.md",
        ),
        ("docs/runbooks/**/*.md", "docs/troubleshooting/runbooks/**/*.md"),
    ),
    Gate(
        "notifications_alerting",
        "P1",
        "config/production-readiness/notification_alert_policy.json",
        ("docs/governance/production-readiness-p1-operational-controls.md",),
        ("*alertmanager*.yml", "*notification*.py", "*test_notification*.py"),
    ),
    Gate(
        "feature_flags",
        "P1",
        "config/production-readiness/feature_flag_rollout_policy.json",
        ("docs/governance/production-readiness-p1-operational-controls.md",),
        ("*feature*flag*.yaml", "*feature_flags*.py", "*test_feature_flags*.py"),
    ),
    Gate(
        "tenant_rate_limits",
        "P1",
        "config/production-readiness/tenant_quota_policy.json",
        ("docs/governance/production-readiness-p1-operational-controls.md",),
        ("*rate_limit*.py", "*rate_limiting*.py", "*test_tenant_rate*.py"),
    ),
    Gate(
        "sdk_cli",
        "P1",
        "config/production-readiness/feature_flag_rollout_policy.json",
        (
            "docs/governance/production-readiness-p1-operational-controls.md",
            "docs/sdk/sdk-cli-production-readiness.md",
        ),
        ("contracts/openapi/*.json", "sdk/python/**/*.py", "scripts/generate_sdk.py"),
    ),
    Gate(
        "billing_metering",
        "P2",
        "config/production-readiness/billing_metering_policy.json",
        ("docs/governance/production-readiness-p2-governance-commercialization.md",),
        ("*billing*.py", "*billing*.md", "*billing*.yml"),
    ),
    Gate(
        "slo_sla",
        "P2",
        "config/production-readiness/slo_sla_policy.json",
        ("docs/governance/production-readiness-p2-governance-commercialization.md",),
        ("docs/slo/**/*.md", "*rules*.yml", "*alert*.yml"),
    ),
    Gate(
        "soc2_iso_controls",
        "P2",
        "config/production-readiness/compliance_control_policy.json",
        ("docs/governance/production-readiness-p2-governance-commercialization.md",),
        ("docs/compliance/**/*.md", ".github/scripts/*control*.sh", ".github/workflows/audit-evidence.yml"),
    ),
)


def git_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, text=True, check=True, capture_output=True
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def matches_any(files: Iterable[str], patterns: Iterable[str]) -> bool:
    all_files = list(files)
    for pattern in patterns:
        if list(ROOT.glob(pattern)):
            return True
        if any(fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern) for path in all_files):
            return True
    return False


def load_policy(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    required = data.get("productionEvidenceRequired")
    if not isinstance(required, list) or not required:
        raise ValueError(f"{path} must define non-empty productionEvidenceRequired")
    if SECRET_VALUE_RE.search(path.read_text(encoding="utf-8")):
        raise ValueError(f"{path} appears to contain an unsafe secret-like value")
    return data


def main() -> int:
    tracked = git_files()
    failures: list[str] = []
    for gate in GATES:
        policy_path = ROOT / gate.policy
        if not policy_path.exists():
            failures.append(f"{gate.name}: missing policy {gate.policy}")
            continue
        try:
            load_policy(policy_path)
        except Exception as exc:  # noqa: BLE001 - print concise CI error
            failures.append(f"{gate.name}: invalid policy {gate.policy}: {exc}")
        for doc in gate.docs:
            if not (ROOT / doc).exists():
                failures.append(f"{gate.name}: missing doc {doc}")
        if not matches_any(tracked, gate.evidence_patterns):
            failures.append(
                f"{gate.name}: no repository evidence matched {', '.join(gate.evidence_patterns)}"
            )
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    for gate in GATES:
        print(f"PASS: {gate.priority} {gate.name} foundation and evidence requirements present")
    print("NOTE: This validator proves repository foundations only; live provider evidence is still required for production PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
