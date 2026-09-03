"""Regression tests for integration-stack CI/config findings."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _version_tuple(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    assert match, f"Unable to parse version from {version!r}"
    return tuple(int(part) for part in match.groups())


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
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "deprecation_register.json" in default
    assert "DEPRECATION_REGISTER_PATH" in default
    assert "COPY services/layer1-ingestion/deprecation_register.json /app/docs/deprecation_register.json" in live
    assert "DEPRECATION_REGISTER_PATH" in live
    assert "**/docs/" in dockerignore
    assert "COPY docs/deprecation_register.json" not in live


def test_layer_mypy_targets_canonical_python_311() -> None:
    for layer in (
        "layer1-ingestion",
        "layer2-extraction",
        "layer3-knowledge",
        "layer4-agents",
        "layer5-ground-truth",
        "layer6-benchmarks",
    ):
        text = (REPO_ROOT / "services" / layer / "pyproject.toml").read_text(encoding="utf-8")
        assert 'python_version = "3.11"' in text, layer
        assert 'python_version = "3.12"' not in text, layer


def test_web_lockfile_pins_patched_nanoid() -> None:
    lock = (REPO_ROOT / "apps" / "web" / "pnpm-lock.yaml").read_text(encoding="utf-8")
    assert "nanoid@5.1.16" in lock
    assert "nanoid@3.3.18" in lock
    assert "nanoid@5.1.11" not in lock
    assert "nanoid@3.3.16" not in lock
    assert "nanoid@3.3.17" not in lock
    assert "tailwindcss>nanoid: 3.3.18" in lock


def test_web_lockfile_pins_patched_axios() -> None:
    package = json.loads(
        (REPO_ROOT / "apps" / "web" / "package.json").read_text(encoding="utf-8")
    )
    lock = (REPO_ROOT / "apps" / "web" / "pnpm-lock.yaml").read_text(encoding="utf-8")
    match = re.search(
        r"(?m)^      axios:\n        specifier: (?P<specifier>\S+)\n"
        r"        version: (?P<version>\d+\.\d+\.\d+)$",
        lock,
    )
    assert match, "Unable to find the web lockfile axios importer entry"
    assert match["specifier"] == package["dependencies"]["axios"]
    assert _version_tuple(match["version"]) >= (1, 18, 0)


def test_dependency_scan_emits_scalar_node_matrix_and_expands_wd() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "dependency-scan.yml").read_text(
        encoding="utf-8"
    )
    assert "json.dumps([item['name'] for item in data['node']])" in workflow
    assert "process.env.AUDIT_BASELINE" in workflow
    assert "readFileSync('${{ github.workspace }}/${WD}/pnpm-audit-base.json'" not in workflow
    assert "pnpm --dir" in workflow
