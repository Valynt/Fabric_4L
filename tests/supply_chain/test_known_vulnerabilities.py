from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vulnerability_policy_blocks_critical_and_high_findings() -> None:
    policy = (REPO_ROOT / "security/supply_chain/vulnerability_triage_sla.md").read_text(encoding="utf-8")
    security_gates = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")
    supply_chain = (REPO_ROOT / ".github/workflows/supply-chain.yml").read_text(encoding="utf-8")

    assert "Critical" in policy
    assert "High" in policy
    assert "Blocks merge and promotion" in policy
    assert "severity: 'HIGH,CRITICAL'" in security_gates
    assert "--fail-on high" in supply_chain
    assert "grype sbom:" in supply_chain


def test_audit_ci_writes_vulnerability_summary_artifact() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/supply_chain_gate.py", "audit"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary_path = REPO_ROOT / "artifacts/supply-chain/vulnerability-summary.json"
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert "critical and high vulnerabilities block" in summary["blocking_policy"]


def test_ci_publishes_vulnerability_summary_artifacts() -> None:
    supply_chain = (REPO_ROOT / ".github/workflows/supply-chain.yml").read_text(encoding="utf-8")
    security_gates = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")

    assert "source-${{ matrix.layer }}-vulns.sarif" in supply_chain
    assert "${{ matrix.layer }}-vulns.sarif" in supply_chain
    assert "supply-chain-report.md" in supply_chain
    assert "release-security-evidence-${{github.sha}}" in security_gates


def test_pip_audit_ci_uses_supported_flags_and_safe_toolchain() -> None:
    pr_checks = (REPO_ROOT / ".github/workflows/pr-checks.yml").read_text(encoding="utf-8")
    security_gates = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")
    production_readiness = (REPO_ROOT / "scripts/production-readiness-check.sh").read_text(encoding="utf-8")

    combined = "\n".join([pr_checks, security_gates, production_readiness])

    assert "pip-audit --severity" not in combined
    assert '"setuptools>=83.0.0" pip-audit' in security_gates
    assert "uv run pip-audit --exit-code 1" in pr_checks


def test_repo_hygiene_does_not_duplicate_secret_scanning() -> None:
    repo_hygiene = (REPO_ROOT / ".github/workflows/repo-hygiene.yml").read_text(encoding="utf-8")
    security_gates = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")

    assert "infisical scan" not in repo_hygiene
    assert "Secret Detection (gitleaks)" in security_gates

def test_node_audit_overrides_patch_known_transitive_advisories() -> None:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    overrides = package_json["pnpm"]["overrides"]

    assert overrides["brace-expansion@<1.1.16"] == "1.1.16"
    assert overrides["brace-expansion@>=2.0.0 <2.1.2"] == "2.1.2"
    assert overrides["brace-expansion@>=5.0.0 <5.0.7"] == "5.0.7"
    assert overrides["systeminformation@<=5.31.6"] == "5.31.7"
    assert overrides["body-parser@<1.20.6"] == "1.20.6"


def test_release_evidence_bandit_matches_security_gate_policy() -> None:
    workflow = (REPO_ROOT / ".github/workflows/release-evidence-bundle.yml").read_text(encoding="utf-8")

    assert "bandit -r services/ -ll -ii -x '*/tests/*,*/migrations/*' -f json" in workflow
    assert "bandit -r services/ -ll -ii -x '*/tests/*,*/migrations/*' -f txt" in workflow

