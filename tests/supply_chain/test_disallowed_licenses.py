from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_license_policy_documents_forbidden_licenses() -> None:
    policy = (REPO_ROOT / "security/supply_chain/dependency_policy.md").read_text(encoding="utf-8")

    for license_id in ("AGPL-3.0", "GPL-3.0", "LGPL-3.0", "SSPL-1.0"):
        assert license_id in policy


def test_ci_license_check_fails_on_forbidden_licenses_and_uploads_report() -> None:
    workflow = (REPO_ROOT / ".github/workflows/supply-chain.yml").read_text(encoding="utf-8")

    assert "license-check:" in workflow
    assert "forbidden = {\"GPL-3.0\", \"AGPL-3.0\", \"LGPL-3.0\", \"SSPL-1.0\"}" in workflow
    assert "raise SystemExit(1)" in workflow
    assert "license-report-${{ github.sha }}" in workflow
    assert "placeholder" not in workflow.lower()

