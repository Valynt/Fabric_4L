"""P1-002: Frontend Coverage Thresholds

Ensures vitest.config.ts enforces 60% lines/functions/statements
and 50% branches minimum.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VITEST_CONFIG = REPO_ROOT / "apps" / "web" / "vitest.config.ts"
VITE_CONFIG = REPO_ROOT / "apps" / "web" / "vite.config.ts"


@pytest.mark.security
@pytest.mark.contract_static
def test_vitest_config_has_60_percent_thresholds():
    content = VITEST_CONFIG.read_text(encoding="utf-8")
    assert "thresholds:" in content
    assert "lines: 60" in content
    assert "functions: 60" in content
    assert "statements: 60" in content
    assert "branches: 50" in content


@pytest.mark.security
@pytest.mark.contract_static
def test_vite_config_has_60_percent_thresholds():
    content = VITE_CONFIG.read_text(encoding="utf-8")
    assert "thresholds:" in content
    assert "lines: 60" in content
    assert "functions: 60" in content
    assert "statements: 60" in content
    assert "branches: 50" in content


@pytest.mark.security
@pytest.mark.contract_static
def test_vitest_config_excludes_generated_code():
    content = VITEST_CONFIG.read_text(encoding="utf-8")
    assert "src/api/generated/**" in content


@pytest.mark.security
@pytest.mark.contract_static
def test_vite_config_excludes_generated_code():
    content = VITE_CONFIG.read_text(encoding="utf-8")
    assert "src/api/generated/**" in content
