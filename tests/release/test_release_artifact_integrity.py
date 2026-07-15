"""Release checks for artifact metadata integrity and CI publication."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

BUILD_WORKFLOW = Path(".github/workflows/build-deploy.yml")
PROMOTION_WORKFLOW = Path(".github/workflows/environment-promotion.yml")
RELEASE_WORKFLOW = Path(".github/workflows/release-evidence-bundle.yml")
REGISTRY = Path(".github/workflows/workflow-registry.json")
PACKAGE = Path("package.json")


def test_package_scripts_expose_release_safety_commands() -> None:
    scripts = json.loads(PACKAGE.read_text(encoding="utf-8"))["scripts"]
    assert scripts["release:dry-run"] == (
        "python scripts/ci/generate_release_safety_artifact.py --environment release-candidate --profile release-candidate"
    )
    assert scripts["release:rollback:verify"] == "python scripts/ci/verify_release_rollback.py"


def test_build_promotion_metadata_contract_requires_release_identity() -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/ci/validate_promotion_artifact_contract.py",
            "--build-workflow",
            str(BUILD_WORKFLOW),
            "--promotion-workflow",
            str(PROMOTION_WORKFLOW),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "schema contract passed" in result.stdout.lower()


def test_build_metadata_artifact_contains_required_identity_fields() -> None:
    text = BUILD_WORKFLOW.read_text(encoding="utf-8")
    for marker in (
        '"image_digest"',
        '"published_tag"',
        '"source_commit_sha"',
        '"source_version"',
        '"build_timestamp"',
        '"environment"',
    ):
        assert marker in text
    assert "date -u +%Y-%m-%dT%H:%M:%SZ" in text
    assert "sha-${{ steps.sha.outputs.short }}" in text


def test_release_safety_artifact_upload_is_wired_in_ci_and_registry() -> None:
    workflow_text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "Generate release safety artifact" in workflow_text
    assert "name: release-safety" in workflow_text
    assert "artifacts/release/release-safety.json" in workflow_text

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    release_entry = next(entry for entry in registry["workflows"] if entry["path"] == str(RELEASE_WORKFLOW).replace("\\", "/"))
    assert "artifacts/release/release-safety.json" in release_entry["produced_artifacts"]


def test_release_safety_dry_run_writes_artifact_shape(tmp_path: Path) -> None:
    output = tmp_path / "release-safety.json"
    result = subprocess.run(
        [
            "python",
            "scripts/ci/generate_release_safety_artifact.py",
            "--environment",
            "staging",
            "--profile",
            "tier1-beta-readiness",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+([-.][0-9A-Za-z.-]+)?", payload["version"])
    assert re.fullmatch(r"[0-9a-f]{40}", payload["commit_sha"])
    assert payload["environment"] == "staging"
    assert payload["profile"] == "tier1-beta-readiness"
    assert payload["canary_gates"]["required_checks"] == ["health", "error_rate", "latency"]
    assert payload["rollback_readiness"]["failed_deployment_blocks_promotion"] is True


def test_release_workflow_yaml_is_valid() -> None:
    data = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    assert data["jobs"]["release-readiness-gate"]["steps"]
