"""Behavior tests for the canonical Dev Container topology contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts" / "ci" / "check_devcontainer_config.py"
PR_CHECKS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pr-checks.yml"


def test_checked_in_devcontainer_topology_satisfies_static_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--skip-cli-validation"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dev Container configuration contract passed" in result.stdout


def test_validator_rejects_default_host_socket_mount(tmp_path: Path) -> None:
    devcontainer_dir = tmp_path / ".devcontainer"
    devcontainer_dir.mkdir()
    (devcontainer_dir / "docker-compose.yml").write_text(
        "services:\n  dev:\n    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--repo-root",
            str(tmp_path),
            "--skip-cli-validation",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "default topology must not mount the host Docker socket" in result.stdout


def test_devcontainer_cli_install_activates_pnpm_home_in_current_step() -> None:
    workflow = PR_CHECKS_WORKFLOW.read_text(encoding="utf-8")
    install_step = workflow.split("- name: Install pinned Dev Container CLI", 1)[1].split(
        "- name: Install compose contract dependencies", 1
    )[0]

    export_home = 'export PNPM_HOME="${RUNNER_TEMP}/pnpm"'
    export_path = 'export PATH="${PNPM_HOME}:${PATH}"'
    global_install = "pnpm add --global @devcontainers/cli@0.80.1"

    assert export_home in install_step
    assert export_path in install_step
    assert install_step.index(export_home) < install_step.index(global_install)
    assert install_step.index(export_path) < install_step.index(global_install)
