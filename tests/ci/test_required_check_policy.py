from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_required_check_policy_metadata_in_sync() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci/check_required_check_policy.py"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
