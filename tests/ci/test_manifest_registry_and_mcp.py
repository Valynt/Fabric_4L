"""Regression tests for integration-stack CI/config findings."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_generated_manifest_registry_uses_posix_paths_and_uv_lock(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "ci" / "generate_manifest_registry.py"
    generated = subprocess.check_output([sys.executable, str(script)], text=True)
    registry = json.loads(generated)

    python_names = {item["name"] for item in registry["python"]}
    assert "shared" not in python_names
    assert "sdk" not in python_names
    assert "platform-contract" not in python_names
    assert "api" in python_names
    assert "layer1-ingestion" in python_names

    for item in registry["python"]:
        path = item["path"]
        assert "\\" not in path
        assert (REPO_ROOT / path / "uv.lock").is_file(), path

    checked_in = json.loads((REPO_ROOT / ".github" / "manifests.json").read_text(encoding="utf-8"))
    assert checked_in == registry


def test_mcp_json_uses_portable_authorization_header() -> None:
    payload = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = payload["mcpServers"]["repowise"]
    assert "bearerTokenEnvVar" not in server
    assert server["type"] == "http"
    assert server["headers"]["Authorization"] == "Bearer ${REPOWISE_API_KEY}"


def test_codeowners_has_no_unsupported_negation() -> None:
    text = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            assert not stripped.startswith("!"), stripped


def test_layer1_packaged_deprecation_register_matches_canonical() -> None:
    canonical = (REPO_ROOT / "docs" / "deprecation_register.json").read_bytes()
    packaged = (REPO_ROOT / "services" / "layer1-ingestion" / "deprecation_register.json").read_bytes()
    assert packaged == canonical


def test_layer1_dockerfiles_install_deprecation_register() -> None:
    default = (REPO_ROOT / "services" / "layer1-ingestion" / "Dockerfile").read_text(encoding="utf-8")
    live = (REPO_ROOT / "services" / "layer1-ingestion" / "Dockerfile.live").read_text(encoding="utf-8")
    assert "deprecation_register.json" in default
    assert "DEPRECATION_REGISTER_PATH" in default
    assert "docs/deprecation_register.json" in live
    assert "DEPRECATION_REGISTER_PATH" in live


def test_dependency_scan_emits_scalar_node_matrix_and_expands_wd() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "dependency-scan.yml").read_text(
        encoding="utf-8"
    )
    assert "json.dumps([item['name'] for item in data['node']])" in workflow
    assert "process.env.AUDIT_BASELINE" in workflow
    assert "readFileSync('${{ github.workspace }}/${WD}/pnpm-audit-base.json'" not in workflow
    assert "pnpm --dir" in workflow
