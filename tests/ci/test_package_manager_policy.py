from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_POLICY = REPO_ROOT / "scripts" / "ci" / "check_package_manager_policy.mjs"
ENFORCE_POLICY = REPO_ROOT / "scripts" / "ci" / "enforce-package-manager.cjs"
CANONICAL_PNPM_VERSION = "10.34.5"


def _run_repo_script(
    script: Path,
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(script)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(env or {})},
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_package_manager_fixture(
    root: Path,
    *,
    workflow_body: str = "jobs:\n  verify:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: pnpm/action-setup@v3\n",
    tool_versions_pnpm: str = CANONICAL_PNPM_VERSION,
    security_suite_pnpm: str = CANONICAL_PNPM_VERSION,
) -> None:
    package_json = {
        "name": "fixture-root",
        "private": True,
        "packageManager": f"pnpm@{CANONICAL_PNPM_VERSION}",
        "scripts": {"preinstall": "node scripts/enforce-package-manager.cjs"},
    }
    web_package_json = {
        "name": "fixture-web",
        "private": True,
        "packageManager": f"pnpm@{CANONICAL_PNPM_VERSION}",
        "scripts": {"preinstall": "node ./scripts/enforce-package-manager.cjs"},
    }

    _write(root / "package.json", json.dumps(package_json, indent=2) + "\n")
    _write(root / "apps" / "web" / "package.json", json.dumps(web_package_json, indent=2) + "\n")
    _write(root / ".npmrc", f"engine-strict=true\npackage-manager=pnpm@{CANONICAL_PNPM_VERSION}\n")
    _write(root / ".codex" / "setup.sh", f"corepack use pnpm@{CANONICAL_PNPM_VERSION}\n")
    _write(root / ".codex" / "setup.ps1", f"corepack use pnpm@{CANONICAL_PNPM_VERSION}\n")
    _write(root / ".devcontainer" / "devcontainer.json", f'{{"features": {{"node": {{"pnpmVersion": "{CANONICAL_PNPM_VERSION}"}}}}}}\n')
    _write(root / ".devcontainer" / "post-create.sh", f"corepack prepare pnpm@{CANONICAL_PNPM_VERSION} --activate\n")
    _write(root / "Makefile", f"corepack prepare pnpm@{CANONICAL_PNPM_VERSION} --activate\n")
    _write(
        root / "apps" / "web" / "Dockerfile",
        "\n".join(
            (
                f"RUN npm install --global pnpm@{CANONICAL_PNPM_VERSION}",
                f"RUN npm install --global pnpm@{CANONICAL_PNPM_VERSION}",
                "",
            )
        ),
    )
    _write(root / "apps" / "web" / "Dockerfile.dev", f"RUN corepack prepare pnpm@{CANONICAL_PNPM_VERSION} --activate\n")
    _write(
        root / "apps" / "web" / "Dockerfile.playwright",
        f"RUN corepack prepare pnpm@{CANONICAL_PNPM_VERSION} --activate\n",
    )
    _write(
        root / "apps" / "web" / "scripts" / "playwright-docker-entrypoint.sh",
        f"corepack prepare pnpm@{CANONICAL_PNPM_VERSION} --activate\n",
    )
    _write(
        root / "tools" / "ci" / "security-suite" / "Dockerfile",
        f"ARG PNPM_VERSION={security_suite_pnpm}\n",
    )
    _write(
        root / ".tool-versions",
        "\n".join(
            (
                "python 3.11.10",
                "nodejs 22.22.2",
                f"pnpm {tool_versions_pnpm}",
                "uv 0.11.6",
                "",
            )
        ),
    )
    for action_path in (
        root / ".github" / "actions" / "setup-fabric-ci" / "action.yml",
        root / ".depot" / "actions" / "setup-fabric-ci" / "action.yml",
    ):
        _write(
            action_path,
            "\n".join(
                (
                    "name: Setup Fabric CI",
                    "inputs:",
                    "  pnpm-version:",
                    f"    default: '{CANONICAL_PNPM_VERSION}'",
                    "",
                )
            ),
        )
    for workflow_path in (
        root / ".github" / "workflows" / "policy.yml",
        root / ".depot" / "workflows" / "policy.yml",
    ):
        _write(workflow_path, workflow_body)

    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)


def test_package_manager_enforcer_accepts_repo_policy() -> None:
    result = _run_repo_script(
        ENFORCE_POLICY,
        REPO_ROOT,
        env={"npm_config_user_agent": f"pnpm/{CANONICAL_PNPM_VERSION}"},
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_package_manager_policy_accepts_canonical_pnpm_setup(tmp_path: Path) -> None:
    _write_package_manager_fixture(tmp_path)

    result = _run_repo_script(CHECK_POLICY, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_package_manager_policy_rejects_stale_canonical_pnpm_version(tmp_path: Path) -> None:
    _write_package_manager_fixture(tmp_path, tool_versions_pnpm="10.34.4")

    result = _run_repo_script(CHECK_POLICY, tmp_path)

    assert result.returncode == 1
    assert ".tool-versions" in result.stderr
    assert CANONICAL_PNPM_VERSION in result.stderr


def test_package_manager_policy_rejects_stale_security_suite_pnpm_version(tmp_path: Path) -> None:
    _write_package_manager_fixture(tmp_path, security_suite_pnpm="10.18.1")

    result = _run_repo_script(CHECK_POLICY, tmp_path)

    assert result.returncode == 1
    assert "tools/ci/security-suite/Dockerfile" in result.stderr
    assert CANONICAL_PNPM_VERSION in result.stderr


def test_package_manager_policy_rejects_hard_coded_workflow_pnpm_version(tmp_path: Path) -> None:
    _write_package_manager_fixture(
        tmp_path,
        workflow_body=(
            "jobs:\n"
            "  verify:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: pnpm/action-setup@v3\n"
            "        with:\n"
            "          version: \"10.34.5\"\n"
        ),
    )

    result = _run_repo_script(CHECK_POLICY, tmp_path)

    assert result.returncode == 1
    assert "hard-code a pnpm version" in result.stderr


def test_package_manager_policy_ignores_commented_workflow_pnpm_text(tmp_path: Path) -> None:
    _write_package_manager_fixture(
        tmp_path,
        workflow_body=(
            "# allowed docs mention pnpm@10.34.5 and PNPM_VERSION: 10.34.5\n"
            "jobs:\n"
            "  verify:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: pnpm/action-setup@v3\n"
        ),
    )

    result = _run_repo_script(CHECK_POLICY, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
