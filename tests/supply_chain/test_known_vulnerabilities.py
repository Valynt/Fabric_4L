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
    assert "release-security-evidence-${{ github.sha }}" in security_gates

