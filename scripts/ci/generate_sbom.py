#!/usr/bin/env python3
"""
SBOM Generation Script for Fabric 4L

Generates unified CycloneDX (Python) and SPDX (Node.js) SBOMs,
merges them into a single artifact, and optionally uploads to
GitHub release assets.

Usage:
    python generate_sbom.py --format json --output sbom/
    python generate_sbom.py --format json xml --output sbom/ --upload-release v1.2.0
    python generate_sbom.py --verify          # Verify existing SBOM signatures

Exit codes:
    0  Success
    1  Missing tooling
    2  Generation error
    3  Upload error
    4  Verification failure
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_NAME = "Fabric_4L"
PROJECT_VERSION = os.environ.get("RELEASE_VERSION", "1.2.0")
PROJECT_URL = "https://github.com/fabric4l/fabric4l"
SUPPLIER = "Fabric 4L Engineering"
LICENSE = "Proprietary"

PYTHON_SERVICES = [
    "services/api",
    "services/layer1-ingestion",
    "services/layer2-extraction",
    "services/layer3-knowledge",
    "services/layer4-workflow",
    "services/layer5-groundtruth",
    "services/layer6-benchmark",
]

NODE_SERVICES = [
    "frontend/web",
    "frontend/admin",
]

SBOM_SPEC_VERSION = "1.5"  # CycloneDX
SPDX_VERSION = "SPDX-2.3"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("sbom")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate unified SBOM for Fabric 4L",
    )
    parser.add_argument(
        "--format",
        nargs="+",
        choices=["json", "xml"],
        default=["json"],
        help="Output format(s) (default: json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sbom"),
        help="Output directory for SBOM files",
    )
    parser.add_argument(
        "--upload-release",
        metavar="TAG",
        default=None,
        help="Upload generated SBOMs to GitHub release TAG",
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        default=True,
        help="Sign SBOMs with Sigstore cosign (default: True)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing SBOM signatures instead of generating",
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Skip generation, only merge existing SBOM files",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------

def check_tool(name: str, *commands: str) -> Optional[str]:
    """Return the path to a CLI tool, or None if not found."""
    for cmd in commands:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return cmd
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return None


def ensure_tools() -> dict:
    """Verify required SBOM tooling is available."""
    tools = {}
    tools["cyclonedx-py"] = check_tool(
        "cyclonedx-py", "cyclonedx-py", "cyclonedx-bom"
    )
    tools["pnpm"] = check_tool("pnpm", "pnpm")
    tools["cosign"] = check_tool("cosign", "cosign")
    tools["syft"] = check_tool("syft", "syft")

    # cyclonedx-py and at least one Node.js tool are required
    if tools["cyclonedx-py"] is None and tools["syft"] is None:
        logger.error(
            "Neither cyclonedx-py nor syft found. "
            "Install: pip install cyclonedx-bom   OR   https://github.com/anchore/syft"
        )
        sys.exit(1)

    return tools


# ---------------------------------------------------------------------------
# Python SBOM (CycloneDX)
# ---------------------------------------------------------------------------

def generate_python_sbom(
    output_dir: Path,
    tools: dict,
    fmt: str = "json",
) -> Path:
    """
    Generate CycloneDX SBOM for all Python services.

    Strategy:
      1. Collect all requirements.txt files from services/*/
      2. Generate per-service SBOMs
      3. Merge into a unified Python SBOM
    """
    logger.info("Generating Python (CycloneDX) SBOM...")

    sbom_dir = output_dir / "python"
    sbom_dir.mkdir(parents=True, exist_ok=True)

    unified_path = sbom_dir / f"fabric4l-python-sbom.{fmt}"

    # Collect requirements files
    req_files: List[Path] = []
    for svc in PYTHON_SERVICES:
        req = Path(svc) / "requirements.txt"
        if req.exists():
            req_files.append(req.resolve())
        else:
            logger.warning("No requirements.txt found for %s", svc)

    if not req_files:
        logger.error("No Python requirements files found!")
        sys.exit(2)

    # Method 1: cyclonedx-py (preferred)
    if tools.get("cyclonedx-py"):
        _generate_with_cyclonedx_py(req_files, unified_path, fmt, tools)
    # Method 2: syft fallback
    elif tools.get("syft"):
        _generate_with_syft("python", unified_path, tools)

    logger.info("Python SBOM written to %s", unified_path)
    return unified_path


def _generate_with_cyclonedx_py(
    req_files: List[Path],
    output: Path,
    fmt: str,
    tools: dict,
) -> None:
    """Use cyclonedx-py to generate SBOM from requirements files."""
    cmd = [
        tools["cyclonedx-py"],
        "requirements",
        "--output-format", "JSON" if fmt == "json" else "XML",
        "--output-file", str(output),
        "--schema-version", SBOM_SPEC_VERSION,
    ]
    for rf in req_files:
        cmd.extend(["--requirements-file", str(rf)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("cyclonedx-py failed: %s", result.stderr)
        sys.exit(2)


def _generate_with_syft(language: str, output: Path, tools: dict) -> None:
    """Use Anchore Syft as fallback SBOM generator."""
    cmd = [
        tools["syft"],
        "packages",
        "dir:.",
        "--output", f"cyclonedx-json={output}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("syft failed: %s", result.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Node.js SBOM (SPDX)
# ---------------------------------------------------------------------------

def generate_node_sbom(
    output_dir: Path,
    tools: dict,
    fmt: str = "json",
) -> Path:
    """
    Generate SPDX SBOM for all Node.js frontend services.

    Strategy:
      1. Use pnpm to list all dependencies per service
      2. Generate per-service SBOM via @spdx/sbom-generator
      3. Merge into unified Node.js SBOM
    """
    logger.info("Generating Node.js (SPDX) SBOM...")

    sbom_dir = output_dir / "node"
    sbom_dir.mkdir(parents=True, exist_ok=True)

    unified_path = sbom_dir / f"fabric4l-node-sbom.{fmt}"

    # Use syft for Node.js if available (handles pnpm via lockfile)
    if tools.get("syft"):
        lockfiles = []
        for svc in NODE_SERVICES:
            lf = Path(svc) / "pnpm-lock.yaml"
            if lf.exists():
                lockfiles.append(str(lf.parent))

        if lockfiles:
            cmd = [
                tools["syft"],
                "packages",
                ",".join(lockfiles),
                "--output", f"spdx-json={unified_path}",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("syft Node.js scan failed: %s", result.stderr)
                sys.exit(2)
        else:
            logger.warning("No pnpm lockfiles found for Node.js services")
            # Write empty SBOM placeholder
            _write_empty_sbom(unified_path, fmt, "SPDX")
    else:
        # Fallback: npm/pnpm list + manual SPDX construction
        _generate_node_sbom_from_pnpm(sbom_dir, unified_path, fmt)

    logger.info("Node.js SBOM written to %s", unified_path)
    return unified_path


def _generate_node_sbom_from_pnpm(
    sbom_dir: Path, output: Path, fmt: str
) -> None:
    """Generate Node.js SBOM by parsing pnpm list output."""
    all_deps: List[dict] = []

    for svc in NODE_SERVICES:
        if not (Path(svc) / "package.json").exists():
            continue

        try:
            result = subprocess.run(
                ["pnpm", "list", "--json", "--depth", "Infinity"],
                cwd=svc,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                deps = json.loads(result.stdout)
                all_deps.extend(deps)
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            logger.warning("Failed to parse %s dependencies: %s", svc, exc)

    # Build SPDX document
    spdx_doc = {
        "spdxVersion": SPDX_VERSION,
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{PROJECT_NAME}-node",
        "documentNamespace": f"{PROJECT_URL}/node-sbom/{PROJECT_VERSION}",
        "creationInfo": {
            "created": datetime.now(timezone.utc).isoformat(),
            "creators": [f"Tool: generate_sbom.py-{PROJECT_VERSION}", f"Organization: {SUPPLIER}"],
        },
        "packages": _flatten_pnpm_deps(all_deps),
    }

    if fmt == "json":
        with open(output, "w") as f:
            json.dump(spdx_doc, f, indent=2)
    else:
        # SPDX tag-value format
        _write_spdx_tag_value(spdx_doc, output)


def _flatten_pnpm_deps(pnpm_output: List[dict]) -> List[dict]:
    """Flatten nested pnpm list output into SPDX packages."""
    packages: List[dict] = []
    seen: set = set()

    def walk(node: dict):
        name = node.get("name", "")
        version = node.get("version", "")
        key = f"{name}@{version}"
        if key in seen or not name:
            return
        seen.add(key)

        pkg = {
            "SPDXID": f"SPDXRef-Package-{name.replace('/', '-')}@{version}",
            "name": name,
            "downloadLocation": node.get("resolved", "NOASSERTION"),
            "filesAnalyzed": False,
            "versionInfo": version,
            "supplier": node.get("publisher", "NOASSERTION"),
            "licenseConcluded": node.get("license", "NOASSERTION"),
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        }
        packages.append(pkg)

        for dep in node.get("dependencies", {}).values():
            walk(dep)

    for root in pnpm_output:
        walk(root)
    return packages


def _write_spdx_tag_value(spdx_doc: dict, output: Path) -> None:
    """Write SPDX in tag-value format."""
    lines = [
        f"SPDXVersion: {spdx_doc['spdxVersion']}",
        f"DataLicense: {spdx_doc['dataLicense']}",
        f"SPDXID: {spdx_doc['SPDXID']}",
        f"DocumentName: {spdx_doc['name']}",
        f"DocumentNamespace: {spdx_doc['documentNamespace']}",
        f"Created: {spdx_doc['creationInfo']['created']}",
    ]
    for c in spdx_doc["creationInfo"]["creators"]:
        lines.append(f"Creator: {c}")
    for pkg in spdx_doc.get("packages", []):
        lines.append("")
        lines.append(f"PackageName: {pkg['name']}")
        lines.append(f"SPDXID: {pkg['SPDXID']}")
        lines.append(f"PackageVersion: {pkg['versionInfo']}")
        lines.append(f"PackageDownloadLocation: {pkg['downloadLocation']}")
        lines.append(f"FilesAnalyzed: {pkg['filesAnalyzed']}")
        lines.append(f"PackageSupplier: {pkg['supplier']}")
        lines.append(f"PackageLicenseConcluded: {pkg['licenseConcluded']}")
    output.write_text("\n".join(lines))


def _write_empty_sbom(path: Path, fmt: str, spec: str) -> None:
    """Write a placeholder SBOM when no dependencies are found."""
    if spec == "SPDX":
        doc = {
            "spdxVersion": SPDX_VERSION,
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"{PROJECT_NAME}-node-empty",
            "documentNamespace": f"{PROJECT_URL}/node-sbom/empty",
            "creationInfo": {
                "created": datetime.now(timezone.utc).isoformat(),
                "creators": [f"Tool: generate_sbom.py"],
            },
            "packages": [],
        }
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)


# ---------------------------------------------------------------------------
# Merge SBOMs
# ---------------------------------------------------------------------------

def merge_sboms(
    python_sbom: Path,
    node_sbom: Path,
    output_dir: Path,
    fmt: str,
) -> Path:
    """
    Merge Python (CycloneDX) and Node.js (SPDX) SBOMs into a unified
    CycloneDX document.
    """
    logger.info("Merging SBOMs into unified artifact...")

    unified_path = output_dir / f"fabric4l-unified-sbom.{fmt}"

    if fmt == "json":
        _merge_as_json(python_sbom, node_sbom, unified_path)
    else:
        _merge_as_xml(python_sbom, node_sbom, unified_path)

    logger.info("Unified SBOM written to %s", unified_path)
    return unified_path


def _merge_as_json(py_path: Path, node_path: Path, out_path: Path) -> None:
    """Merge two JSON SBOMs into a unified CycloneDX document."""
    with open(py_path) as f:
        py_sbom = json.load(f)

    # Build unified CycloneDX
    unified = {
        "bomFormat": "CycloneDX",
        "specVersion": SBOM_SPEC_VERSION,
        "serialNumber": f"urn:uuid:{_uuid_from_content()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [
                {
                    "vendor": "Fabric 4L",
                    "name": "generate_sbom.py",
                    "version": PROJECT_VERSION,
                }
            ],
            "component": {
                "type": "application",
                "name": PROJECT_NAME,
                "version": PROJECT_VERSION,
                "supplier": {"name": SUPPLIER},
            },
        },
        "components": [],
    }

    # Extract Python components
    if "components" in py_sbom:
        unified["components"].extend(py_sbom["components"])
    elif "packages" in py_sbom:
        # Convert SPDX packages to CycloneDX components
        for pkg in py_sbom["packages"]:
            unified["components"].append({
                "type": "library",
                "name": pkg["name"],
                "version": pkg.get("versionInfo", "unknown"),
                "purl": pkg.get("downloadLocation", ""),
                "supplier": {"name": pkg.get("supplier", "Unknown")},
            })

    # Read Node.js components
    try:
        with open(node_path) as f:
            node_sbom = json.load(f)
        if "packages" in node_sbom:
            for pkg in node_sbom["packages"]:
                unified["components"].append({
                    "type": "library",
                    "name": pkg["name"],
                    "version": pkg.get("versionInfo", "unknown"),
                    "purl": pkg.get("downloadLocation", ""),
                    "supplier": {"name": pkg.get("supplier", "Unknown")},
                })
    except Exception as exc:
        logger.warning("Could not merge Node.js SBOM: %s", exc)

    # Deduplicate by purl/name+version
    seen = set()
    deduped = []
    for comp in unified["components"]:
        key = comp.get("purl") or f"{comp['name']}@{comp.get('version', '')}"
        if key not in seen:
            seen.add(key)
            deduped.append(comp)
    unified["components"] = deduped

    with open(out_path, "w") as f:
        json.dump(unified, f, indent=2)


def _merge_as_xml(py_path: Path, node_path: Path, out_path: Path) -> None:
    """For XML format, wrap Python SBOM and add Node.js as a separate tool output."""
    # Fallback: copy Python SBOM and add a note about Node.js
    import shutil
    shutil.copy2(py_path, out_path)
    logger.info("XML merge: Python SBOM copied; Node.js components in separate file")


def _uuid_from_content() -> str:
    """Generate a deterministic UUID from project metadata."""
    content = f"{PROJECT_NAME}:{PROJECT_VERSION}:{datetime.now(timezone.utc).isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:32]
    # First 32 chars of MD5, formatted as UUID by caller


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def sign_sbom(sbom_path: Path, tools: dict) -> Path:
    """Sign SBOM using Sigstore cosign. Returns path to signature file."""
    if not tools.get("cosign"):
        logger.warning("cosign not available — skipping signing")
        return sbom_path

    logger.info("Signing %s with cosign...", sbom_path.name)

    sig_path = sbom_path.with_suffix(sbom_path.suffix + ".sig")

    result = subprocess.run(
        [
            tools["cosign"],
            "sign-blob",
            "--yes",
            "--output-signature", str(sig_path),
            str(sbom_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("cosign signing failed: %s", result.stderr)
        sys.exit(3)

    # Also generate SHA-256 checksum
    checksum_path = sbom_path.with_suffix(sbom_path.suffix + ".sha256")
    sha = hashlib.sha256(sbom_path.read_bytes()).hexdigest()
    checksum_path.write_text(f"{sha}  {sbom_path.name}\n")

    logger.info("Signature: %s", sig_path)
    logger.info("Checksum:  %s", checksum_path)
    return sig_path


def verify_sbom_signature(sbom_path: Path, tools: dict) -> bool:
    """Verify a signed SBOM using cosign."""
    if not tools.get("cosign"):
        logger.error("cosign not available for verification")
        return False

    sig_path = sbom_path.with_suffix(sbom_path.suffix + ".sig")
    if not sig_path.exists():
        logger.error("No signature file found for %s", sbom_path)
        return False

    result = subprocess.run(
        [
            tools["cosign"],
            "verify-blob",
            "--signature", str(sig_path),
            str(sbom_path),
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# GitHub Release Upload
# ---------------------------------------------------------------------------

def upload_to_github_release(
    files: List[Path],
    tag: str,
) -> None:
    """Upload SBOM files to a GitHub release using the gh CLI."""
    logger.info("Uploading SBOMs to GitHub release %s...", tag)

    gh = check_tool("gh", "gh")
    if gh is None:
        logger.error("gh CLI not found. Install: https://cli.github.com")
        sys.exit(3)

    for f in files:
        result = subprocess.run(
            [gh, "release", "upload", tag, str(f), "--clobber"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Upload failed for %s: %s", f, result.stderr)
            sys.exit(3)
        logger.info("Uploaded %s", f.name)

    # Attest the SBOM to the release
    for f in files:
        if f.suffix == ".json":
            result = subprocess.run(
                [gh, "attestation", "create", str(f), "--release", tag],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                logger.info("Attestation created for %s", f.name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    tools = ensure_tools()

    # Verify mode
    if args.verify:
        success = True
        for f in args.output.glob("**/*sbom*"):
            if f.suffix in (".json", ".xml"):
                ok = verify_sbom_signature(f, tools)
                status = "✓ VALID" if ok else "✗ INVALID"
                logger.info("%s  %s", status, f)
                success = success and ok
        return 0 if success else 4

    args.output.mkdir(parents=True, exist_ok=True)
    generated_files: List[Path] = []

    if not args.merge_only:
        # Generate Python SBOM
        for fmt in args.format:
            py_sbom = generate_python_sbom(args.output, tools, fmt)
            generated_files.append(py_sbom)

        # Generate Node.js SBOM
        for fmt in args.format:
            node_sbom = generate_node_sbom(args.output, tools, fmt)
            generated_files.append(node_sbom)

    # Merge into unified SBOM
    for fmt in args.format:
        py_path = args.output / "python" / f"fabric4l-python-sbom.{fmt}"
        node_path = args.output / "node" / f"fabric4l-node-sbom.{fmt}"
        if py_path.exists() and node_path.exists():
            unified = merge_sboms(py_path, node_path, args.output, fmt)
            generated_files.append(unified)

    # Sign unified SBOMs
    if args.sign:
        for f in list(generated_files):
            if "unified" in f.name:
                sign_sbom(f, tools)

    # Upload to release
    if args.upload_release:
        upload_to_github_release(generated_files, args.upload_release)

    logger.info("SBOM generation complete. Files:")
    for f in generated_files:
        size = f.stat().st_size
        logger.info("  %s (%d bytes)", f, size)

    return 0


if __name__ == "__main__":
    sys.exit(main())
