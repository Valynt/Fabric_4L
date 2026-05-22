from __future__ import annotations

import subprocess


def test_no_e2e_constants_in_production_paths() -> None:
    result = subprocess.run(
        ["python", "scripts/ci/check_no_e2e_constants_in_production.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
