from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_e2e_constants_in_production_paths() -> None:
    result = subprocess.run(
        ["python", "scripts/ci/check_no_e2e_constants_in_production.py"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
