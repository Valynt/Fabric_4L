from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

ALLOWED_WRITE_PERMISSIONS: dict[str, dict[str, str]] = {
    "ai-evals-pipeline.yml": {
        "checks": "updates AI evaluation check runs",
        "id-token": "authenticates Infisical-backed evaluation jobs through OIDC",
        "pull-requests": "comments on pull requests with evaluation results",
    },
    "api-changelog.yml": {
        "issues": "creates an advisory issue for detected breaking API changes",
        "releases": "attaches the generated changelog and updates release notes",
    },
    "api-key-rotation.yml": {
        "id-token": "authenticates rotation automation through OIDC",
        "issues": "creates API key rotation tracking issues",
    },
    "backend-integrated-reproducibility.yml": {
        "id-token": "authenticates backend-integrated reproducibility jobs through OIDC",
    },
    "build-deploy.yml": {
        "attestations": "publishes build provenance attestations",
        "contents": "pushes generated SDK updates from the dedicated SDK job",
        "id-token": "uses OIDC for keyless signing",
        "packages": "publishes container images",
        "security-events": "uploads container scan SARIF",
    },
    "bundle-analysis.yml": {
        "pull-requests": "updates pull requests with bundle-size reports",
    },
    "cleanup-repo.yml": {
        "contents": "deletes remote branches selected by the cleanup workflow",
        "pull-requests": "closes pull requests selected by the cleanup workflow",
    },
    "contract-compliance.yml": {
        "issues": "comments drift reports on pull requests",
    },
    "dependency-scan.yml": {
        "security-events": "uploads dependency and container scan SARIF",
    },
    "environment-promotion.yml": {
        "contents": "pushes GitOps promotion branches",
        "id-token": "authenticates deploy automation through OIDC",
        "pull-requests": "opens promotion pull requests",
    },
    "game-day-evidence.yml": {
        "contents": "commits retained game-day evidence artifacts",
    },
    "flakiness-tracker.yml": {
        "issues": "creates scheduled flakiness tracking issues",
    },
    "package-sign.yml": {
        "id-token": "uses OIDC for provenance and keyless signing",
        "packages": "reads and signs package artifacts from GHCR",
    },
    "publish-ci-tools.yml": {
        "attestations": "publishes build provenance and SBOM attestations",
        "id-token": "authenticates GitHub Actions provenance through OIDC",
        "packages": "publishes the pinned CI tools image to GHCR",
    },
    "penetration-testing.yml": {
        "issues": "comments penetration test results on pull requests",
        "security-events": "uploads penetration scan SARIF",
    },
    "pr-performance-gate.yml": {
        "issues": "comments performance gate results on pull requests",
    },
    "publish-sdk.yml": {
        "id-token": "publishes Python packages with trusted publishing",
        "packages": "publishes SDK packages to GitHub Packages",
    },
    "regenerate-sdk.yml": {
        "contents": "pushes regenerated SDK branches",
        "pull-requests": "opens SDK regeneration pull requests",
    },
    "release-evidence-bundle.yml": {
        "attestations": "attests release evidence bundle",
        "contents": "creates release evidence artifacts",
        "id-token": "uses OIDC for evidence signing",
    },
    "repo-hygiene.yml": {
        "contents": "deletes stale branches selected by the cleanup policy",
        "issues": "comments repository hygiene failures on pull requests",
        "pull-requests": "comments repository hygiene failures on pull requests",
    },
    "runbook-validation.yml": {
        "issues": "comments runbook validation failures on pull requests",
    },
    "sbom.yml": {
        "attestations": "publishes SBOM provenance attestations",
        "contents": "uploads generated SBOM files to releases",
        "id-token": "obtains a Sigstore OIDC token for keyless signing",
    },
    "sdk-generation.yml": {
        "contents": "pushes generated SDK branches",
        "pull-requests": "opens generated SDK pull requests",
    },
    "secret-rotation.yml": {
        "id-token": "authenticates secret rotation automation through OIDC",
        "issues": "creates rotation tracking issues",
    },
    "stale.yml": {
        "pull-requests": "labels and closes stale pull requests",
    },
    "terraform-cd.yml": {
        "id-token": "authenticates Terraform deployment jobs through AWS OIDC",
    },
    "security-gates-merged.yml": {
        "security-events": "uploads security scan SARIF",
    },
    "security-gates.yml": {
        "security-events": "uploads security scan SARIF",
        "id-token": "publishes OpenSSF Scorecard results through OIDC",
    },
    "supply-chain.yml": {
        "id-token": "uses OIDC for provenance verification",
        "security-events": "uploads supply-chain scan SARIF",
    },
    "test-reporting.yml": {
        "checks": "updates test report check runs",
        "pull-requests": "comments test reports on pull requests",
    },
    "vault-integration.yml": {
        "id-token": "authenticates to Vault through OIDC",
    },
    "visual-regression.yml": {
        "pull-requests": "updates pull requests with visual regression results",
    },
    "codeql-analysis.yml": {
        "security-events": "uploads CodeQL SARIF results",
    },
    "codeql.yml": {
        "security-events": "uploads CodeQL SARIF results",
    },
    "deploy.yml": {
        "contents": "commits release evidence artifacts in the evidence job",
        "id-token": "authenticates deploy and rollback jobs through cloud/OIDC providers",
    },
    "integration-tests.yml": {
        "id-token": "authenticates integration test jobs through Infisical OIDC",
    },
    "pr-checks.yml": {
        "id-token": "authenticates PR checks that fetch Infisical-managed secrets",
    },
    "public-docs.yml": {
        "pages": "deploys documentation to GitHub Pages",
        "id-token": "authenticates deploy job to GitHub Pages",
    },
    "refresh-testing-kpis.yml": {
        "contents": "pushes KPI snapshot updates to a PR branch",
        "pull-requests": "opens automated KPI refresh pull requests",
    },
}


def _workflow_files() -> list[Path]:
    return sorted(
        [
            *WORKFLOW_DIR.glob("*.yml"),
            *WORKFLOW_DIR.glob("*.yaml"),
        ]
    )


def _load_workflow(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} did not parse as a YAML mapping"
    return data


def _permission_scopes(
    workflow_name: str, permissions: Any, location: str
) -> list[tuple[str, str]]:
    assert permissions != "write-all", f"{workflow_name} {location} uses write-all"
    if permissions in (None, "read-all"):
        return []
    assert isinstance(
        permissions, dict
    ), f"{workflow_name} {location} permissions must be a mapping or read-all"
    writes: list[tuple[str, str]] = []
    for scope, level in permissions.items():
        assert level != "write-all", f"{workflow_name} {location} uses write-all"
        if str(level).lower() == "write":
            writes.append((location, str(scope)))
    return writes


def test_every_workflow_has_explicit_top_level_permissions() -> None:
    missing: list[str] = []
    for path in _workflow_files():
        workflow = _load_workflow(path)
        if "permissions" not in workflow:
            missing.append(path.name)
    assert not missing, "workflows missing top-level permissions: " + ", ".join(missing)


def test_no_workflow_uses_write_all() -> None:
    for path in _workflow_files():
        workflow = _load_workflow(path)
        _permission_scopes(path.name, workflow.get("permissions"), "top-level")
        for job_name, job in (workflow.get("jobs") or {}).items():
            if isinstance(job, dict):
                _permission_scopes(path.name, job.get("permissions"), f"job:{job_name}")


def test_write_permissions_are_allowlisted_with_reasons() -> None:
    violations: list[str] = []
    for path in _workflow_files():
        workflow = _load_workflow(path)
        writes = _permission_scopes(path.name, workflow.get("permissions"), "top-level")
        for job_name, job in (workflow.get("jobs") or {}).items():
            if isinstance(job, dict):
                writes.extend(
                    _permission_scopes(path.name, job.get("permissions"), f"job:{job_name}")
                )

        allowed = ALLOWED_WRITE_PERMISSIONS.get(path.name, {})
        for location, scope in writes:
            reason = allowed.get(scope)
            if not reason:
                violations.append(f"{path.name} {location} grants {scope}: write")

    assert not violations, "unallowlisted write permissions: " + "; ".join(violations)
