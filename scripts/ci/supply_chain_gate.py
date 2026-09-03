"""Local supply-chain management gate.

The CI workflows run heavyweight scanners (Trivy, Syft/Anchore, Grype, Cosign).
This script provides the local, deterministic companion gate used by package
scripts and static tests. It verifies policy wiring and writes evidence
artifacts without requiring Docker or network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "supply-chain"

POLICY_FILES = (
    REPO_ROOT / "security/supply_chain/README.md",
    REPO_ROOT / "security/supply_chain/sbom_policy.md",
    REPO_ROOT / "security/supply_chain/dependency_policy.md",
    REPO_ROOT / "security/supply_chain/container_policy.md",
    REPO_ROOT / "security/supply_chain/vulnerability_triage_sla.md",
)

LOCKFILES = (
    REPO_ROOT / "pnpm-lock.yaml",
    REPO_ROOT / "apps/web/pnpm-lock.yaml",
    REPO_ROOT / "services/api/uv.lock",
    REPO_ROOT / "services/layer1-ingestion/uv.lock",
    REPO_ROOT / "services/layer2-extraction/uv.lock",
    REPO_ROOT / "services/layer2-5-signal-refinery/uv.lock",
    REPO_ROOT / "services/layer3-knowledge/uv.lock",
    REPO_ROOT / "services/layer4-agents/uv.lock",
    REPO_ROOT / "services/layer5-ground-truth/uv.lock",
    REPO_ROOT / "services/layer6-benchmarks/uv.lock",
)

PRODUCTION_DOCKERFILES = (
    REPO_ROOT / "apps/web/Dockerfile",
    REPO_ROOT / "services/api/Dockerfile",
    REPO_ROOT / "services/layer1-ingestion/Dockerfile",
    REPO_ROOT / "services/layer2-extraction/Dockerfile",
    REPO_ROOT / "services/layer2-5-signal-refinery/Dockerfile",
    REPO_ROOT / "services/layer3-knowledge/Dockerfile",
    REPO_ROOT / "services/layer4-agents/Dockerfile",
    REPO_ROOT / "services/layer5-ground-truth/Dockerfile",
    REPO_ROOT / "services/layer6-benchmarks/Dockerfile",
)

FLOATING_IMAGE_RE = re.compile(
    r"(?P<name>[a-z0-9][a-z0-9./_-]*):(?P<tag>(?:latest|[0-9]+|[0-9]+\.[0-9]+|[0-9]+-[a-z0-9._-]+|[0-9]+\.[0-9]+-[a-z0-9._-]+))$",
    re.IGNORECASE,
)
APPROVED_PACKAGE_MANIFEST_ROOTS = {"apps", "packages", "services", "sdk", "tests"}


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_package_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_approved_package_manifest(manifest: Path) -> bool:
    rel = manifest.resolve().relative_to(REPO_ROOT)
    if rel.as_posix() == "package.json":
        return True

    parts = rel.parts
    return len(parts) == 3 and parts[0] in APPROVED_PACKAGE_MANIFEST_ROOTS and parts[2] == "package.json"


def discover_components() -> list[dict[str, str]]:
    components: list[dict[str, str]] = []

    for manifest in sorted(REPO_ROOT.glob("**/package.json")):
        if "node_modules" in manifest.parts or not is_approved_package_manifest(manifest):
            continue
        payload = load_package_json(manifest)
        components.append(
            {
                "type": "application",
                "name": str(payload.get("name") or manifest.parent.name),
                "version": str(payload.get("version") or "0.0.0"),
                "purl": f"pkg:npm/{payload.get('name') or manifest.parent.name}",
                "scope": repo_relative(manifest),
            }
        )

    for manifest in sorted(REPO_ROOT.glob("services/*/pyproject.toml")):
        payload = tomllib.loads(manifest.read_text(encoding="utf-8"))
        project = payload.get("project", {})
        if not project:
            continue
        components.append(
            {
                "type": "application",
                "name": str(project.get("name") or manifest.parent.name),
                "version": str(project.get("version") or "0.0.0"),
                "purl": f"pkg:pypi/{project.get('name') or manifest.parent.name}",
                "scope": repo_relative(manifest),
            }
        )

    return components


def generate_sbom() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    lockfile_hashes = [
        {"path": repo_relative(path), "sha256": sha256(path)}
        for path in LOCKFILES
        if path.exists()
    ]
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "component": {
                "type": "application",
                "name": "fabric-4l-monorepo",
                "version": load_package_json(REPO_ROOT / "package.json").get("version", "0.0.0"),
            },
            "properties": lockfile_hashes,
            "tools": [{"vendor": "Value Fabric", "name": "supply_chain_gate.py"}],
        },
        "components": discover_components(),
    }
    output = ARTIFACT_DIR / "fabric-4l-source-sbom.cdx.json"
    output.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "sbom": repo_relative(output),
        "component_count": len(sbom["components"]),
        "lockfile_count": len(lockfile_hashes),
        "policy": "security/supply_chain/sbom_policy.md",
    }
    (ARTIFACT_DIR / "sbom-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    provenance = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": "fabric-4l-monorepo",
                "digest": {
                    "sha256": lockfile_hashes[0]["sha256"] if lockfile_hashes else ""
                },
            }
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://fabric4l.dev/release/v1/source-build",
                "externalParameters": {"lockfiles": lockfile_hashes},
                "internalParameters": {
                    "component_count": len(sbom["components"]),
                },
            },
            "runDetails": {
                "builder": {"id": "https://fabric4l.dev/tools/supply_chain_gate.py"},
                "metadata": {
                    "invocationId": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                },
            },
        },
    }
    prov_output = ARTIFACT_DIR / "provenance.json"
    prov_output.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {repo_relative(output)} and {repo_relative(prov_output)}")
    return 0


def check_lockfiles() -> list[str]:
    errors: list[str] = []
    for path in LOCKFILES:
        if not path.is_file():
            errors.append(f"Missing canonical lockfile: {repo_relative(path)}")
    root_scripts = load_package_json(REPO_ROOT / "package.json")["scripts"]
    for script in ("sbom", "audit:ci", "container:scan"):
        if script not in root_scripts:
            errors.append(f"Missing root package script: {script}")
    return errors


def from_references(dockerfile: Path) -> list[str]:
    references: list[str] = []
    for line in dockerfile.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("FROM "):
            references.append(stripped.split()[1])
    return references


def is_pinned_image(reference: str) -> bool:
    if reference.startswith("${"):
        return True
    if "@sha256:" in reference:
        return True
    if ":" not in reference:
        return False
    return not FLOATING_IMAGE_RE.match(reference)


def check_container_policy() -> list[str]:
    errors: list[str] = []
    for dockerfile in PRODUCTION_DOCKERFILES:
        if not dockerfile.is_file():
            errors.append(f"Missing production Dockerfile: {repo_relative(dockerfile)}")
            continue
        refs = from_references(dockerfile)
        if not refs:
            errors.append(f"No FROM reference found: {repo_relative(dockerfile)}")
        for ref in refs:
            if not is_pinned_image(ref):
                errors.append(f"Floating base image in {repo_relative(dockerfile)}: {ref}")
        text = dockerfile.read_text(encoding="utf-8")
        if "\nUSER " not in text:
            errors.append(f"Missing non-root USER in {repo_relative(dockerfile)}")
        if "HEALTHCHECK" not in text:
            errors.append(f"Missing HEALTHCHECK in {repo_relative(dockerfile)}")
    return errors


def check_ci_policy() -> list[str]:
    errors: list[str] = []
    supply_chain = (REPO_ROOT / ".github/workflows/supply-chain-integrity.yml").read_text(encoding="utf-8")
    security_gates = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")

    required_supply_chain_tokens = (
        "source-sbom-scan",
        "sbom-scan",
        "grype sbom:",
        "--fail-on high",
        "cosign verify",
        "license-check",
        "dependency-audit",
        "supply-chain-report.md",
        "actions/upload-artifact@",
    )
    for token in required_supply_chain_tokens:
        if token not in supply_chain:
            errors.append(f"Supply-chain workflow missing token: {token}")

    required_security_tokens = (
        "sbom-policy",
        "trivy-image-scan",
        "frontend-security-audit",
        "dependency-review",
        "release-security-evidence",
    )
    for token in required_security_tokens:
        if token not in security_gates:
            errors.append(f"Security gates workflow missing token: {token}")

    if not re.search(r"severity:\s*['\"]HIGH,CRITICAL['\"]", security_gates):
        errors.append("Security gates workflow missing token: severity: 'HIGH,CRITICAL'")

    for policy_file in POLICY_FILES:
        if not policy_file.is_file():
            errors.append(f"Missing supply-chain policy file: {repo_relative(policy_file)}")

    return errors


def write_vulnerability_summary(errors: list[str]) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "pass" if not errors else "fail",
        "blocking_policy": "critical and high vulnerabilities block production promotion unless an approved time-boxed exception exists",
        "errors": errors,
    }
    (ARTIFACT_DIR / "vulnerability-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def audit_ci() -> int:
    errors = check_lockfiles() + check_ci_policy()
    write_vulnerability_summary(errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Supply-chain dependency and vulnerability CI policy checks passed.")
    return 0


def container_scan() -> int:
    errors = check_container_policy() + check_ci_policy()
    write_vulnerability_summary(errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Container base image, scanning, signing, and artifact policy checks passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("sbom", "audit", "container", "all"))
    args = parser.parse_args(argv)

    if args.mode == "sbom":
        return generate_sbom()
    if args.mode == "audit":
        return audit_ci()
    if args.mode == "container":
        return container_scan()

    sbom_status = generate_sbom()
    errors = check_lockfiles() + check_container_policy() + check_ci_policy()
    write_vulnerability_summary(errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return sbom_status


if __name__ == "__main__":
    raise SystemExit(main())
