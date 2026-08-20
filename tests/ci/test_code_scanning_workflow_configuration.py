"""Regression contracts for code-scanning workflow compatibility."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECURITY_GATES = ROOT / ".github/workflows/security-gates.yml"
DEPENDENCY_SCAN = ROOT / ".github/workflows/dependency-scan.yml"
CODEQL = ROOT / ".github/workflows/codeql.yml"

CODEQL_V4_SHA = "3ce22a6e336a7fcc318bc58ae1986395bdc83ba7"


def test_trivy_uses_supported_misconfig_scanner_name() -> None:
    workflow = SECURITY_GATES.read_text(encoding="utf-8")

    assert "scanners: 'vuln,secret,config'" not in workflow
    assert workflow.count("scanners: 'vuln,secret,misconfig'") == 2


def test_all_local_sarif_uploads_use_the_reviewed_codeql_v4_action() -> None:
    workflows = (SECURITY_GATES, DEPENDENCY_SCAN, CODEQL)

    for path in workflows:
        workflow = path.read_text(encoding="utf-8")
        upload_refs = [
            line.strip()
            for line in workflow.splitlines()
            if "github/codeql-action/upload-sarif@" in line
        ]
        assert all(CODEQL_V4_SHA in ref for ref in upload_refs), (
            f"{path.relative_to(ROOT)} contains a retired or inconsistent "
            f"CodeQL SARIF uploader: {upload_refs}"
        )
