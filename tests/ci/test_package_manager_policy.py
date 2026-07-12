from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_package_manager_policy_rejects_forbidden_install_commands() -> None:
    result = subprocess.run(
        ["node", "scripts/ci/enforce-package-manager.cjs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
