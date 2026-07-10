#!/usr/bin/env python3
"""Validate repository-owned final-testing launch gate requirements.

This validator intentionally proves only the checks available from the repository. It must not
claim production go-live readiness for environment-dependent controls such as live SSO, telemetry,
notifications, billing, rollback drills, or production-like E2E rehearsals.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCS = (
    "docs/validation/final_testing_launch_gate_design.md",
    "docs/launch/final-testing-launch-checklist.md",
    "docs/launch/launch-blocker-register.md",
    "docs/launch/environment-dependent-evidence-matrix.md",
    "docs/launch/evidence-manifest.example.yaml",
)

REQUIRED_CLASSIFICATIONS = ("P0 Launch Blocker", "P1 Launch Blocker", "P2 Follow-Up")
REQUIRED_ENVIRONMENT_GATES = (
    "Production-like E2E launch rehearsal",
    "Enterprise SSO/OIDC provider validation",
    "Notification and alert receiver validation",
    "Telemetry dashboard and alert validation",
    "Billing and metering provider validation",
    "Rollback and restore drill",
    "Performance and reliability smoke test",
)

SECRET_SCAN_PATHS = (
    "docs/launch",
    "docs/validation/final_testing_launch_gate_design.md",
    "docs/validation/production_readiness_execution_status.md",
    "docs/validation/production_readiness_prioritized_execution_plan.md",
    "config/production-readiness",
)

SAFE_PLACEHOLDER_RE = re.compile(
    r"(?i)(redacted|placeholder|example|external_secret_ref|secret_ref|provider_required|"
    r"requires_environment|todo|tbd|not_applicable|none|required)"
)
UNSAFE_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|client[_-]?secret|secret|password|token|webhook|private[_-]?key)\b"
        r"\s*[:=]\s*['\"]?([^'\"\s`|]{12,})"
    ),
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def run_command(name: str, command: list[str]) -> CheckResult:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode == 0:
        detail = (result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "completed")
        return CheckResult(name, True, detail)
    detail_parts = []
    if result.stdout.strip():
        detail_parts.append(result.stdout.strip())
    if result.stderr.strip():
        detail_parts.append(result.stderr.strip())
    detail = "\n".join(detail_parts)[-1200:] or f"exit code {result.returncode}"
    return CheckResult(name, False, detail)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_docs() -> CheckResult:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).exists()]
    if missing:
        return CheckResult("required_launch_documents", False, "missing: " + ", ".join(missing))
    return CheckResult("required_launch_documents", True, f"{len(REQUIRED_DOCS)} launch gate documents present")


def check_blocker_taxonomy() -> CheckResult:
    combined = "\n".join(read_text(ROOT / path) for path in REQUIRED_DOCS if (ROOT / path).exists())
    missing = [classification for classification in REQUIRED_CLASSIFICATIONS if classification not in combined]
    if missing:
        return CheckResult("blocker_taxonomy", False, "missing classifications: " + ", ".join(missing))
    return CheckResult("blocker_taxonomy", True, "P0/P1/P2 blocker taxonomy present")


def check_environment_gate_separation() -> CheckResult:
    matrix_path = ROOT / "docs/launch/environment-dependent-evidence-matrix.md"
    if not matrix_path.exists():
        return CheckResult("environment_gate_separation", False, "missing environment-dependent evidence matrix")
    content = read_text(matrix_path)
    missing_gates = [gate for gate in REQUIRED_ENVIRONMENT_GATES if gate not in content]
    if missing_gates:
        return CheckResult("environment_gate_separation", False, "missing gates: " + ", ".join(missing_gates))
    overclaimed_lines = [
        line.strip()
        for line in content.splitlines()
        if line.startswith("|")
        and any(gate in line for gate in REQUIRED_ENVIRONMENT_GATES)
        and "REQUIRES_ENVIRONMENT" not in line
    ]
    if overclaimed_lines:
        return CheckResult(
            "environment_gate_separation",
            False,
            "environment-dependent gates must remain REQUIRES_ENVIRONMENT: " + " ; ".join(overclaimed_lines[:5]),
        )
    return CheckResult("environment_gate_separation", True, "environment-dependent gates are not overclaimed")


def iter_scan_files(paths: Iterable[str]) -> Iterable[Path]:
    for relative in paths:
        path = ROOT / relative
        if path.is_file():
            yield path
        elif path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file() and candidate.suffix.lower() in {".md", ".json", ".yaml", ".yml", ".txt"}:
                    yield candidate


def check_secret_hygiene() -> CheckResult:
    findings: list[str] = []
    for path in iter_scan_files(SECRET_SCAN_PATHS):
        text = read_text(path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if SAFE_PLACEHOLDER_RE.search(line):
                continue
            for pattern in UNSAFE_SECRET_PATTERNS:
                match = pattern.search(line)
                if match:
                    findings.append(f"{path.relative_to(ROOT)}:{line_number}: {match.group(0)[:80]}")
                    break
    if findings:
        return CheckResult("launch_artifact_secret_hygiene", False, "unsafe secret-like values: " + " ; ".join(findings[:10]))
    return CheckResult("launch_artifact_secret_hygiene", True, "no unsafe secret-like values found in launch artifacts")


def main() -> int:
    checks: list[CheckResult] = [
        check_required_docs(),
        check_blocker_taxonomy(),
        check_environment_gate_separation(),
        check_secret_hygiene(),
        run_command("core_ga_launch_evidence_guard", [sys.executable, "scripts/ci/validate_core_ga_launch_evidence.py"]),
        run_command("production_readiness_foundations", [sys.executable, "scripts/ci/validate_production_readiness_plan.py"]),
        run_command("platform_contract_lint", [sys.executable, "scripts/ci/platform_contract_lint.py"]),
        run_command("dependabot_coverage", [sys.executable, "scripts/ci/check_dependabot_coverage.py"]),
        run_command(
            "launch_evidence_manifest_schema",
            [
                sys.executable,
                "scripts/ci/validate_launch_evidence_manifest.py",
                "docs/launch/evidence-manifest.example.yaml",
            ],
        ),
    ]

    failed = [check for check in checks if not check.passed]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status}: {check.name}: {check.detail}")
    print(
        "NOTE: This gate validates repository-owned final-testing readiness only; "
        "live production PASS still requires environment evidence."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
