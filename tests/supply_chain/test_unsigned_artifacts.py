from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_workflow_verifies_signatures_and_provenance() -> None:
    supply_chain = (REPO_ROOT / ".github/workflows/supply-chain-integrity.yml").read_text(encoding="utf-8")
    deploy = (REPO_ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")

    assert "verify-signatures:" in supply_chain
    assert "cosign verify" in supply_chain
    assert "SLSA Provenance" in supply_chain
    assert "cosign verify-attestation" in supply_chain
    assert "cosign verify-blob" in deploy
    assert "Missing Cosign signature or certificate for SBOM artifact" in deploy


def test_sbom_command_generates_evidence_artifacts() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/supply_chain_gate.py", "sbom"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    sbom_path = REPO_ROOT / "artifacts/supply-chain/fabric-4l-source-sbom.cdx.json"
    summary_path = REPO_ROOT / "artifacts/supply-chain/sbom-summary.json"
    assert sbom_path.is_file()
    assert summary_path.is_file()

    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["components"]
    assert summary["component_count"] == len(sbom["components"])


def test_admission_policy_blocks_unsigned_images() -> None:
    policy_files = [
        REPO_ROOT / "k8s/policy/kyverno-verify-signatures.yaml",
        REPO_ROOT / "k8s/policy/kyverno-slsa-provenance.yaml",
    ]

    for policy_file in policy_files:
        text = policy_file.read_text(encoding="utf-8")
        assert "verifyImages" in text or "attestors" in text or "cosign" in text
        assert "ghcr.io" in text
