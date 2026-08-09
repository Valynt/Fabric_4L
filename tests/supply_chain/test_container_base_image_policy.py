from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/ci/supply_chain_gate.py"


def load_gate_module():
    spec = importlib.util.spec_from_file_location("supply_chain_gate", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_production_dockerfile_base_images_are_pinned() -> None:
    gate = load_gate_module()

    for dockerfile in gate.PRODUCTION_DOCKERFILES:
        refs = gate.from_references(dockerfile)
        assert refs, dockerfile
        for ref in refs:
            assert gate.is_pinned_image(ref), f"{dockerfile}: {ref}"


def test_production_dockerfiles_have_non_root_runtime_and_healthcheck() -> None:
    gate = load_gate_module()

    errors = gate.check_container_policy()
    assert errors == []


def test_container_scan_gate_passes_static_policy_checks() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/supply_chain_gate.py", "container"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_ci_container_scans_use_blocking_high_critical_policy() -> None:
    security_gates = (REPO_ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")

    assert "trivy-image-scan:" in security_gates
    assert "exit-code: '1'" in security_gates
    assert "severity: 'HIGH,CRITICAL'" in security_gates
    assert "scanners: 'vuln,secret,config'" in security_gates


def test_hadolint_uses_matrix_dockerfile_or_context_dockerfile() -> None:
    pr_checks = (REPO_ROOT / ".github/workflows/pr-checks.yml").read_text(encoding="utf-8")

    assert "dockerfile: ${{ matrix.context }}/${{ matrix.dockerfile }}" not in pr_checks
    assert "dockerfile: ${{ matrix.dockerfile || format('{0}/Dockerfile', matrix.context) }}" in pr_checks


def test_python_runtime_dockerfiles_upgrade_os_and_pip_packages() -> None:
    scanned_layer_dockerfiles = [
        REPO_ROOT / "services" / layer / "Dockerfile"
        for layer in (
            "layer1-ingestion",
            "layer2-extraction",
            "layer3-knowledge",
            "layer4-agents",
            "layer5-ground-truth",
            "layer6-benchmarks",
        )
    ]

    for dockerfile in scanned_layer_dockerfiles:
        content = dockerfile.read_text(encoding="utf-8")
        assert "apt-get update && apt-get upgrade -y && apt-get install" in content, dockerfile
        assert "pip install --no-cache-dir --upgrade pip setuptools wheel" in content, dockerfile
