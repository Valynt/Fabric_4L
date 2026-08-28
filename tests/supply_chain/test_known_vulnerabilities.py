from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_vulnerability_policy_blocks_critical_and_high_findings() -> None:
    policy = (REPO_ROOT / "security/supply_chain/vulnerability_triage_sla.md").read_text(encoding="utf-8")
    security_gates = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")
    supply_chain = (REPO_ROOT / ".github/workflows/supply-chain-integrity.yml").read_text(encoding="utf-8")

    assert "Critical" in policy
    assert "High" in policy
    assert "Blocks merge and promotion" in policy
    assert "severity: \"HIGH,CRITICAL\"" in security_gates
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
    supply_chain = (REPO_ROOT / ".github/workflows/supply-chain-integrity.yml").read_text(encoding="utf-8")
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
    assert 'bash "${{ github.workspace }}/scripts/ci/run_pip_audit.sh"' in pr_checks


def test_repo_hygiene_does_not_duplicate_secret_scanning() -> None:
    repo_hygiene = (REPO_ROOT / ".github/workflows/repo-hygiene.yml").read_text(encoding="utf-8")
    security_gates = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")

    assert "infisical scan" not in repo_hygiene
    assert "Secret Detection (gitleaks)" in security_gates


def test_node_audit_overrides_patch_known_transitive_advisories() -> None:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    overrides = package_json["pnpm"]["overrides"]

    assert overrides["brace-expansion@^1.1.7"] == "5.0.9"
    assert overrides["brace-expansion@^2.0.1"] == "5.0.9"
    assert overrides["brace-expansion@^5.0.0"] == "5.0.9"
    assert overrides["systeminformation@<=5.31.6"] == "5.31.7"

    root_lockfile = (REPO_ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8")
    web_lockfile = (REPO_ROOT / "apps/web/pnpm-lock.yaml").read_text(encoding="utf-8")

    # Workspace lockfile is the install authority and must resolve only 5.0.9.
    assert "brace-expansion@5.0.9:" in root_lockfile
    for vulnerable_version in ("1.1.14", "2.1.1", "2.1.2", "2.1.0", "5.0.6", "5.0.7", "5.0.8"):
        assert f"brace-expansion@{vulnerable_version}:" not in root_lockfile

    # Nested apps/web lockfile must not resolve the GHSA-vulnerable 1.x/2.x/5.0.6-7 line.
    for vulnerable_version in ("1.1.14", "2.1.1", "2.1.2", "2.1.0", "5.0.6", "5.0.7"):
        assert f"brace-expansion@{vulnerable_version}:" not in web_lockfile
    assert (
        "brace-expansion@5.0.9:" in web_lockfile
        or "brace-expansion@5.0.8:" in web_lockfile
    )
    assert overrides["body-parser@<1.20.6"] == "1.20.6"



def test_flagged_ci_and_test_images_run_as_non_root() -> None:
    expectations = {
        "apps/web/Dockerfile.dev": "USER node",
        "apps/web/Dockerfile.playwright": "USER pwuser",
        "tools/ci/security-suite/Dockerfile": "USER 1001:1001",
    }
    for relative_path, directive in expectations.items():
        dockerfile = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert directive in dockerfile


def test_security_gates_builds_frontend_sbom_from_workspace_root() -> None:
    workflow = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")

    assert 'if [ "${{ matrix.layer }}" = "apps-web" ]; then' in workflow
    assert "-f apps/web/Dockerfile" in workflow
    assert "services/${{matrix.layer}}" in workflow


def test_release_evidence_security_tests_install_root_policy_dependencies() -> None:
    workflow = (REPO_ROOT / ".github/workflows/release-evidence-bundle.yml").read_text(encoding="utf-8")

    assert "uv pip install --system --requirement tests/requirements-test.lock" in workflow


def test_release_evidence_bandit_matches_security_gate_policy() -> None:
    workflow = (REPO_ROOT / ".github/workflows/release-evidence-bundle.yml").read_text(encoding="utf-8")

    assert "bandit -r services/ -ll -ii -x '*/tests/*,*/migrations/*' -f json" in workflow
    assert "bandit -r services/ -ll -ii -x '*/tests/*,*/migrations/*' -f txt" in workflow



def test_osv_pr_scan_does_not_use_reusable_workflow_outputs() -> None:
    workflow = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")
    pr_job = workflow.split("  osv-scanner-pr:", 1)[1].split("  # OSV-Scanner full scan", 1)[0]

    assert "osv-scanner-reusable-pr.yml" not in pr_job
    assert "old-results" not in pr_job
    assert "new-results" not in pr_job
    assert "osv-scanner-pr.sarif" in pr_job

def test_unhashed_test_requirements_keep_osv_safe_minimums() -> None:
    requirements = (REPO_ROOT / "tests/requirements.txt").read_text(encoding="utf-8").lower()

    for requirement in (
        "pyjwt>=2.13.0",
        "pytest>=9.1.1",
        "idna>=3.15",
        "pygments>=2.20.0",
        "starlette>=1.3.1",
        "schemathesis>=4.24.2",
    ):
        assert requirement in requirements


def test_docs_and_platform_requirements_keep_osv_safe_minimums() -> None:
    docs_requirements = (
        REPO_ROOT / "docs-site/requirements-docs.txt"
    ).read_text(encoding="utf-8").lower()
    platform_requirements = (
        REPO_ROOT / "packages/platform-contract/requirements-test.txt"
    ).read_text(encoding="utf-8").lower()

    for requirement in ("idna>=3.15", "pillow>=12.3.0"):
        assert requirement in docs_requirements

    assert "pygments>=2.20.0" in platform_requirements


def test_service_image_locks_exclude_recent_trivy_blockers() -> None:
    vulnerable_tokens = (
        'name = "click"\nversion = "8.3.2"',
        'name = "lxml-html-clean"\nversion = "0.4.4"',
        'name = "setuptools"\nversion = "82.0.1"',
    )

    violations: list[str] = []
    for lockfile in (REPO_ROOT / "services").glob("*/uv.lock"):
        content = lockfile.read_text(encoding="utf-8")
        for token in vulnerable_tokens:
            if token in content:
                violations.append(f"{lockfile.relative_to(REPO_ROOT)} contains {token!r}")

    assert not violations, (
        "Service image lockfiles contain Trivy-blocked package versions: "
        + "; ".join(violations)
    )
