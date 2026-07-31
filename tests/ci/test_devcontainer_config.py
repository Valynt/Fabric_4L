"""Behavior tests for the canonical Dev Container topology contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts" / "ci" / "check_devcontainer_config.py"


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
