from __future__ import annotations

"""Cross-tenant isolation regression tests for migrated L3 route modules.

Validates that the five modules migrated during Phases 3-6:
- benchmarks.py
- variables.py
- models.py
- formulas.py
- formula_governance.py

have no raw AsyncDriver usage and pass the static Cypher scope scanner.
"""


import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCANNER = REPO_ROOT / "scripts" / "check_layer3_cypher_scope.py"
ROUTES_DIR = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes"

MIGRATED_MODULES = [
    "benchmarks.py",
    "variables.py",
    "models.py",
    "formulas.py",
    "formula_governance.py",
]


@pytest.mark.parametrize("module_name", MIGRATED_MODULES)
def test_no_raw_async_driver(module_name: str) -> None:
    """Raw AsyncDriver dependency injection must not remain in migrated modules."""
    source = (ROUTES_DIR / module_name).read_text(encoding="utf-8")
    assert "AsyncDriver = Depends(get_driver)" not in source, (
        f"{module_name} still contains raw AsyncDriver dependency"
    )
    assert "from neo4j import AsyncDriver" not in source, (
        f"{module_name} still imports AsyncDriver"
    )
    assert "from ...db.driver import get_driver" not in source, (
        f"{module_name} still imports get_driver"
    )


@pytest.mark.mandatory
@pytest.mark.parametrize("module_name", MIGRATED_MODULES)
def test_static_scanner_passes_for_module(module_name: str) -> None:
    """The Cypher scope scanner must report 0 errors for each migrated module."""
    module_path = ROUTES_DIR / module_name
    result = subprocess.run(
        [
            sys.executable,
            str(SCANNER),
            "--root",
            str(REPO_ROOT),
            "--paths",
            str(module_path),
            "--warnings-as-errors",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"Scanner failed for {module_name}:\n{result.stdout}\n{result.stderr}"
    )
    assert "0 error(s)" in result.stdout
    assert "0 warning(s)" in result.stdout
