import subprocess
import sys
from pathlib import Path


def test_layer4_route_contract_matrix_is_current():
    """The Layer 4 route contract matrix must cover OpenAPI and discovered routes."""
    result = subprocess.run(
        [sys.executable, "scripts/ci/check_layer4_route_contract_matrix.py"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    assert result.returncode == 0, result.stdout + result.stderr
