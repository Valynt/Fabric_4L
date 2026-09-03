from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_package_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _version_tuple(version: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    assert match, f"Unable to parse version from {version!r}"
    return tuple(int(part) for part in match.groups())


def _locked_version(lock_text: str, package: str) -> tuple[int, int, int]:
    match = re.search(
        rf"(?m)^{re.escape(package)}==(?P<version>\d+\.\d+\.\d+)\s+\\$",
        lock_text,
    )
    assert match, f"Unable to find locked version for {package}"
    return _version_tuple(match["version"])


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

    workflow = (REPO_ROOT / ".github/workflows/supply-chain-integrity.yml").read_text(
        encoding="utf-8"
    )
    assert "pnpm --dir apps/web install --frozen-lockfile" in workflow
    assert "LOCK_HASH_BEFORE=$(sha256sum apps/web/pnpm-lock.yaml" in workflow
    assert "LOCK_HASH_AFTER=$(sha256sum apps/web/pnpm-lock.yaml" in workflow
    assert 'if [ "$LOCK_HASH_BEFORE" != "$LOCK_HASH_AFTER" ]; then' in workflow
    assert "apps/web/pnpm-lock.yaml drifted during pnpm install" in workflow
    assert "git diff --exit-code -- apps/web/pnpm-lock.yaml" not in workflow


def test_audit_ci_gate_passes_static_policy_checks() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/supply_chain_gate.py", "audit"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_security_dependency_floors_stay_in_sync() -> None:
    root_pkg = load_package_json(REPO_ROOT / "package.json")
    web_pkg = load_package_json(REPO_ROOT / "apps/web/package.json")
    test_requirements = (REPO_ROOT / "tests/requirements-test.txt").read_text(encoding="utf-8")
    test_lock = (REPO_ROOT / "tests/requirements-test.lock").read_text(encoding="utf-8")
    pytest_policy = (REPO_ROOT / "config/ci/pytest_policy.yaml").read_text(encoding="utf-8")
    layer3_pyproject = (REPO_ROOT / "services/layer3-knowledge/pyproject.toml").read_text(
        encoding="utf-8"
    )
    web_lock = (REPO_ROOT / "apps/web/pnpm-lock.yaml").read_text(encoding="utf-8")

    assert web_pkg["packageManager"] == root_pkg["packageManager"]
    assert _version_tuple(web_pkg["dependencies"]["axios"]) >= (1, 18, 0)

    for requirement in ("aiohttp>=3.14.3", "protego>=0.6.2", "msgpack>=1.2.1"):
        assert requirement in test_requirements

    assert "aiohttp>=3.14.3" in pytest_policy
    assert '"msgpack>=1.2.1"' in layer3_pyproject

    for package, minimum in {
        "aiohttp": (3, 14, 3),
        "protego": (0, 6, 2),
        "msgpack": (1, 2, 1),
    }.items():
        assert _locked_version(test_lock, package) >= minimum

    match = re.search(
        r"(?m)^      axios:\n        specifier: (?P<specifier>\S+)\n"
        r"        version: (?P<version>\d+\.\d+\.\d+)$",
        web_lock,
    )
    assert match, "Unable to find the web lockfile axios importer entry"
    assert match["specifier"] == web_pkg["dependencies"]["axios"]
    assert _version_tuple(match["version"]) >= (1, 18, 0)


def test_archived_manifest_invariant_is_encoded_in_package_manager_policy() -> None:
    policy = (REPO_ROOT / "scripts/ci/check_package_manager_policy.mjs").read_text(encoding="utf-8")

    assert "Archived evidence manifests/lockfiles are forbidden outside approved immutable exceptions" in policy
    assert "Grandfathered archived manifests are immutable evidence and must not be modified" in policy
    assert "docs/archive/frontend-root-2026-05-02/source-snapshot/package.json" in policy
    assert "docs/archive/frontend-root-2026-05-02/source-snapshot/pnpm-lock.yaml" in policy
