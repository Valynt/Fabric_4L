#!/usr/bin/env python3
"""Validate the ops incident-response docs and runbooks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OPS_ROOT = REPO_ROOT / "ops"
INCIDENT_ROOT = OPS_ROOT / "incident"
RUNBOOK_ROOT = INCIDENT_ROOT / "runbooks"

REQUIRED_INCIDENT_FILES = [
    INCIDENT_ROOT / "README.md",
    INCIDENT_ROOT / "severity_matrix.md",
    INCIDENT_ROOT / "escalation_policy.md",
    INCIDENT_ROOT / "customer_comms_template.md",
    INCIDENT_ROOT / "postmortem_template.md",
]

REQUIRED_RUNBOOKS = [
    RUNBOOK_ROOT / "api_outage.md",
    RUNBOOK_ROOT / "database_degradation.md",
    RUNBOOK_ROOT / "queue_backlog.md",
    RUNBOOK_ROOT / "auth_failure.md",
    RUNBOOK_ROOT / "billing_webhook_failure.md",
]

REQUIRED_RUNBOOK_SECTIONS = [
    "## Purpose",
    "## Trigger",
    "## Severity",
    "## Preconditions",
    "## Immediate Actions",
    "## Diagnosis Steps",
    "## Resolution Steps",
    "## Validation",
    "## Rollback / Fallback",
    "## Customer / Stakeholder Communication",
    "## Evidence to Preserve",
    "## Escalation",
    "## Related Runbooks",
    "## Post-Incident Follow-Up",
]

FORBIDDEN_PLACEHOLDERS = ["TBD", "TODO", "FIXME", "REPLACE_ME"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def require_files(errors: list[str]) -> None:
    required = [OPS_ROOT / "README.md", *REQUIRED_INCIDENT_FILES, *REQUIRED_RUNBOOKS]
    for path in required:
        if not path.exists():
            errors.append(f"missing required file: {rel(path)}")


def lint_runbooks(errors: list[str]) -> None:
    require_files(errors)

    for path in REQUIRED_RUNBOOKS:
        if not path.exists():
            continue
        content = read(path)
        for section in REQUIRED_RUNBOOK_SECTIONS:
            if section not in content:
                errors.append(f"{rel(path)} missing section {section}")
        for placeholder in FORBIDDEN_PLACEHOLDERS:
            if placeholder in content:
                errors.append(f"{rel(path)} contains forbidden placeholder {placeholder}")


def check_incident_package(errors: list[str]) -> None:
    require_files(errors)

    if (OPS_ROOT / "README.md").exists():
        ops_readme = read(OPS_ROOT / "README.md")
        if "incident/README.md" not in ops_readme:
            errors.append("ops/README.md must link to incident/README.md")

    if (INCIDENT_ROOT / "README.md").exists():
        incident_readme = read(INCIDENT_ROOT / "README.md")
        for phrase in ["Detect", "Declare", "Triage", "Mitigate", "Communicate", "Resolve", "Postmortem"]:
            if phrase not in incident_readme:
                errors.append(f"ops/incident/README.md missing lifecycle phrase: {phrase}")
        for runbook in REQUIRED_RUNBOOKS:
            if runbook.name not in incident_readme:
                errors.append(f"ops/incident/README.md missing runbook link: {runbook.name}")

    if (INCIDENT_ROOT / "severity_matrix.md").exists():
        severity = read(INCIDENT_ROOT / "severity_matrix.md")
        for sev in ["SEV-1", "SEV-2", "SEV-3", "SEV-4"]:
            if sev not in severity:
                errors.append(f"severity_matrix.md missing {sev}")
        for phrase in ["tenant", "security", "data", "Response target", "Escalation trigger"]:
            if phrase not in severity:
                errors.append(f"severity_matrix.md missing required concept: {phrase}")

    if (INCIDENT_ROOT / "escalation_policy.md").exists():
        escalation = read(INCIDENT_ROOT / "escalation_policy.md")
        for phrase in [
            "Primary on-call",
            "Secondary on-call",
            "Incident commander",
            "Security",
            "Legal/Privacy",
            "Customer Operations",
            "Update Cadence",
        ]:
            if phrase not in escalation:
                errors.append(f"escalation_policy.md missing required concept: {phrase}")

    if (INCIDENT_ROOT / "customer_comms_template.md").exists():
        comms = read(INCIDENT_ROOT / "customer_comms_template.md")
        for phrase in ["Investigating", "Identified", "Monitoring", "Resolved", "Security Or Privacy Holding Statement"]:
            if phrase not in comms:
                errors.append(f"customer_comms_template.md missing template: {phrase}")

    if (INCIDENT_ROOT / "postmortem_template.md").exists():
        postmortem = read(INCIDENT_ROOT / "postmortem_template.md")
        for phrase in ["## Timeline", "## Impact", "## Root Cause", "## Remediation", "Owner", "Due Date"]:
            if phrase not in postmortem:
                errors.append(f"postmortem_template.md missing required field: {phrase}")

    lint_runbooks(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["runbooks-lint", "incident-check"], required=True)
    args = parser.parse_args()

    errors: list[str] = []
    if args.mode == "runbooks-lint":
        lint_runbooks(errors)
    else:
        check_incident_package(errors)

    if errors:
        print("Incident runbook validation: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Incident runbook validation: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
