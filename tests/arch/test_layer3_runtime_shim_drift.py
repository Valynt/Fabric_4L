"""Architecture check for Layer 3 runtime compatibility shim drift."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "services/layer3-knowledge/scripts/check_runtime_shim_drift.py"


def test_layer3_runtime_shim_drift_script_passes() -> None:
    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Layer 3 runtime shim drift check failed.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
