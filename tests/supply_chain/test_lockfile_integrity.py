from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_package_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_supply_chain_package_scripts_are_registered() -> None:
    scripts = load_package_json(REPO_ROOT / "package.json")["scripts"]

    assert scripts["sbom"] == "python scripts/ci/supply_chain_gate.py sbom"
    assert scripts["audit:ci"] == "python scripts/ci/supply_chain_gate.py audit"
    assert scripts["container:scan"] == "python scripts/ci/supply_chain_gate.py container"


def test_canonical_lockfiles_exist_and_are_enforced() -> None:
    expected_lockfiles = {
        "pnpm-lock.yaml",
        "apps/web/pnpm-lock.yaml",
        "tests/requirements-test.lock",
        "services/billing/uv.lock",
        "services/layer1-ingestion/uv.lock",
        "services/layer2-extraction/uv.lock",
        "services/layer3-knowledge/uv.lock",
        "services/layer4-agents/uv.lock",
        "services/layer5-ground-truth/uv.lock",
        "services/layer6-benchmarks/uv.lock",
    }

    for relative_path in expected_lockfiles:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    policy = (REPO_ROOT / "scripts/ci/check_package_manager_policy.mjs").read_text(encoding="utf-8")
    for relative_path in expected_lockfiles:
        assert f"'{relative_path}'" in policy


def test_docker_and_ci_installs_use_frozen_lockfiles() -> None:
    dockerfiles = [
        REPO_ROOT / "apps/web/Dockerfile",
        REPO_ROOT / "services/layer1-ingestion/Dockerfile",
        REPO_ROOT / "services/layer2-extraction/Dockerfile",
        REPO_ROOT / "services/layer3-knowledge/Dockerfile",
        REPO_ROOT / "services/layer4-agents/Dockerfile",
        REPO_ROOT / "services/layer5-ground-truth/Dockerfile",
        REPO_ROOT / "services/layer6-benchmarks/Dockerfile",
    ]

    for dockerfile in dockerfiles:
        text = dockerfile.read_text(encoding="utf-8")
        assert "--frozen-lockfile" in text or "uv sync --frozen" in text, dockerfile

    workflow = (REPO_ROOT / ".github/workflows/supply-chain.yml").read_text(encoding="utf-8")
    assert "pnpm --dir apps/web install --frozen-lockfile" in workflow
    assert "git diff --exit-code -- apps/web/pnpm-lock.yaml" in workflow


def test_audit_ci_gate_passes_static_policy_checks() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/supply_chain_gate.py", "audit"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
