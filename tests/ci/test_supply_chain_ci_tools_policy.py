from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "supply-chain-integrity.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_ci_tools_image_is_digest_qualified() -> None:
    image = _workflow()["env"]["CI_TOOLS_IMAGE"]
    assert re.fullmatch(
        r"ghcr\.io/(value-fabric|valynt)/ci-tools/security-suite@sha256:[0-9a-f]{64}",
        image,
    ), "CI_TOOLS_IMAGE must be the approved digest-qualified GHCR reference"
    assert ":latest" not in image


def test_container_jobs_depend_on_ci_tools_preflight() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    assert "ci-tools-preflight" in jobs
    expected_image = workflow["env"]["CI_TOOLS_IMAGE"]
    users = {
        name
        for name, job in jobs.items()
        if isinstance(job, dict)
        and isinstance(job.get("container"), dict)
        and job["container"].get("image") == expected_image
    }
    assert users == {"sbom-scan", "verify-signatures", "dependency-audit", "license-check"}
    assert all(
        "${{ env." not in job["container"]["image"]
        for job in jobs.values()
        if isinstance(job, dict) and isinstance(job.get("container"), dict)
    ), "job-level container.image cannot use the env context"
    for name in users:
        needs = jobs[name].get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "ci-tools-preflight" in needs, f"{name} must depend on ci-tools-preflight"


def test_preflight_pulls_and_asserts_digest_and_all_versions() -> None:
    job = _workflow()["jobs"]["ci-tools-preflight"]
    rendered = WORKFLOW.read_text(encoding="utf-8")
    assert "docker/login-action@" in rendered
    run_scripts = "\n".join(step.get("run", "") for step in job["steps"] if isinstance(step, dict))
    assert "docker pull" in run_scripts
    assert "RepoDigests" in run_scripts
    for command in (
        "grype version",
        "syft version",
        "cosign version",
        "pip-audit --version",
        "pip-licenses --version",
        "python --version",
        "node --version",
        "pnpm --version",
    ):
        assert command in run_scripts


def test_publisher_uses_pinned_toolchain_and_trusted_identity() -> None:
    dockerfile = (ROOT / "tools" / "ci" / "security-suite" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    for pin in (
        "python:3.14.0-slim-bookworm@sha256:",
        "GRYPE_VERSION=0.104.1",
        "SYFT_VERSION=1.30.0",
        "COSIGN_VERSION=2.5.3",
        "PIP_AUDIT_VERSION=2.9.0",
        "PIP_LICENSES_VERSION=5.0.0",
        "NODE_VERSION=22.17.0",
        "PNPM_VERSION=10.18.1",
    ):
        assert pin in dockerfile
    assert ":latest" not in dockerfile

    publisher = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "publish-ci-tools.yml").read_text(encoding="utf-8")
    )
    assert publisher["permissions"]["packages"] == "write"
    assert publisher["permissions"]["id-token"] == "write"
    publish_step = next(
        step for step in publisher["jobs"]["publish"]["steps"] if step.get("id") == "publish"
    )
    assert publish_step["with"]["provenance"] == "mode=max"
    assert publish_step["with"]["sbom"] is True
    assert publish_step["with"]["tags"].startswith("ghcr.io/valynt/ci-tools/security-suite:")
