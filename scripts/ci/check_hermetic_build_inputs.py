#!/usr/bin/env python3
"""Hard-fail policy checks for hermetic CI build inputs."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = [
    ROOT / ".github/workflows/build-deploy.yml",
    ROOT / ".github/workflows/supply-chain.yml",
    ROOT / ".github/workflows/pr-checks.yml",
    ROOT / ".github/workflows/critical-gates.yml",
]
# Only check Dockerfiles used in production CI builds.
# Alternate variants (Dockerfile.uv, Dockerfile.full, Dockerfile.live, Dockerfile.dev)
# are for local development or experimental use and are not built in CI.
DOCKERFILES = []
for service_dir in (ROOT / "services").iterdir():
    default_df = service_dir / "Dockerfile"
    if default_df.exists():
        DOCKERFILES.append(default_df)
web_df = ROOT / "apps/web/Dockerfile"
if web_df.exists():
    DOCKERFILES.append(web_df)
BUILD_SCRIPTS = list((ROOT / "scripts/ci").glob("*.sh")) + list((ROOT / "scripts/ci").glob("*.py")) + list((ROOT / ".github/scripts").glob("*.sh"))
APPROVED_DOMAINS = {
    "docker.io",
    "ghcr.io",
    "mcr.microsoft.com",
    "registry.value-fabric.internal",
    "localhost",
    "127.0.0.1",
    # Kubernetes cluster-internal service DNS names used in post-deploy smoke tests
    "layer1-ingestion",
    "layer2-extraction",
    "layer3-knowledge",
    "layer4-agents",
    "layer5-ground-truth",
    "frontend",
    # Existing CI scripts reference these domains for local testing, examples,
    # project schema metadata, or GitHub API interactions.
    "readiness.local",
    "compose-contract.clerk.example.com",
    "valuefabric.ai",
    "github.com",
    "api.github.com",
    # scripts/ci/run_pip_audit.py references the SARIF schema registry
    "json.schemastore.org",
    # scripts/ci/coverage_trends.py emits an SVG trend chart; the SVG namespace
    # URI is a required W3C standard identifier and is not fetched at runtime.
    "www.w3.org",
    # scripts/ci/generate_sbom.py references the GitHub CLI installation URL in
    # an error message when the `gh` binary is missing.
    "cli.github.com",
}

ACTION_REF_RE = re.compile(r"^\s*-\s*uses:\s*([^@\s]+)@([^\s#]+)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FROM_RE = re.compile(r"^\s*FROM\s+([^\s]+)", re.IGNORECASE)
URL_RE = re.compile(r"https?://([A-Za-z0-9.-]+)")
RAW_DOMAIN_RE = re.compile(r"\b([a-z0-9.-]+\.[a-z]{2,})(?::\d+)?\b")

def domain_from_image(image: str) -> str:
    image = image.split("@", 1)[0]  # strip digest before parsing domain
    first = image.split("/", 1)[0]
    if "." not in first and ":" not in first:
        return "docker.io"
    return first


def check_workflows(violations: list[str]) -> None:
    for wf in WORKFLOWS:
        for i, line in enumerate(wf.read_text(encoding="utf-8").splitlines(), start=1):
            m = ACTION_REF_RE.match(line)
            if not m:
                continue
            ref = m.group(2)
            if not SHA_RE.fullmatch(ref):
                violations.append(f"{wf.relative_to(ROOT)}:{i} unpinned action ref '{ref}'")


def check_dockerfiles(violations: list[str]) -> None:
    for dockerfile in DOCKERFILES:
        for i, line in enumerate(dockerfile.read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith("# syntax=docker/dockerfile:"):
                violations.append(
                    f"{dockerfile.relative_to(ROOT)}:{i} Dockerfile frontend must not be pulled at build time: {line}"
                )
            m = FROM_RE.match(line)
            if not m:
                continue
            image = m.group(1)
            if ":latest" in image or image.endswith(":latest"):
                violations.append(f"{dockerfile.relative_to(ROOT)}:{i} latest tag forbidden: {image}")
            if "@sha256:" not in image:
                violations.append(f"{dockerfile.relative_to(ROOT)}:{i} base image must be pinned by digest: {image}")
            domain = domain_from_image(image)
            if domain not in APPROVED_DOMAINS:
                violations.append(f"{dockerfile.relative_to(ROOT)}:{i} unapproved registry domain: {domain}")


def check_build_scripts(violations: list[str]) -> None:
    for script in BUILD_SCRIPTS:
        for i, line in enumerate(script.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip().startswith("#"):
                continue
            for match in URL_RE.finditer(line):
                domain = match.group(1).lower()
                if domain == "...":
                    continue
                if domain not in APPROVED_DOMAINS:
                    violations.append(f"{script.relative_to(ROOT)}:{i} unapproved external URL domain: {domain}")
            if "docker pull " in line or "docker build " in line:
                for match in RAW_DOMAIN_RE.finditer(line):
                    domain = match.group(1).lower()
                    if domain not in APPROVED_DOMAINS:
                        violations.append(f"{script.relative_to(ROOT)}:{i} unapproved external domain in build context: {domain}")


def main() -> int:
    violations: list[str] = []
    check_workflows(violations)
    check_dockerfiles(violations)
    check_build_scripts(violations)

    if violations:
        print("Hermetic build input policy violations detected:")
        for violation in violations:
            print(f" - {violation}")
        return 1

    print("Hermetic build input policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
