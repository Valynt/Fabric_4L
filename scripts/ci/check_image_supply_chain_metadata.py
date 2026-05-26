#!/usr/bin/env python3
"""Fail CI if expected image artifacts miss SBOM and (when required) signing metadata."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

EXPECTED_SERVICES = [
    "layer1-ingestion",
    "layer2-extraction",
    "layer3-knowledge",
    "layer4-agents",
    "layer5-ground-truth",
    "layer6-benchmarks",
]


def check_files(artifact_root: Path, sha: str, mode: str) -> list[str]:
    errors: list[str] = []
    require_signing = mode == "release"

    for service in EXPECTED_SERVICES:
        service_dir = artifact_root / f"scan-{service}-{sha}"
        sbom = service_dir / f"sbom-{service}-{sha}.cdx.json"
        if not sbom.exists() or sbom.stat().st_size == 0:
            errors.append(f"{service}: missing SBOM artifact {sbom}")

        if require_signing:
            signing = service_dir / f"signing-{service}-{sha}.json"
            attestation = service_dir / f"attestation-{service}-{sha}.json"
            if not signing.exists() or signing.stat().st_size == 0:
                errors.append(f"{service}: missing signing metadata {signing}")
            if not attestation.exists() or attestation.stat().st_size == 0:
                errors.append(f"{service}: missing attestation metadata {attestation}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--mode", choices=["pr", "release"], required=True)
    args = parser.parse_args()

    errors = check_files(Path(args.artifact_root), args.sha, args.mode)
    if errors:
        print("Supply-chain metadata policy check failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"Supply-chain metadata policy check passed for mode={args.mode}, sha={args.sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
