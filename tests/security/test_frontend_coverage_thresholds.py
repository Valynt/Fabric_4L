"""P1-002: Frontend Coverage Thresholds

Ensures frontend test configs enforce at least 60% lines/functions/statements
and at least 50% branches.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VITEST_CONFIG = REPO_ROOT / "apps" / "web" / "vitest.config.ts"
VITE_CONFIG = REPO_ROOT / "apps" / "web" / "vite.config.ts"


@pytest.mark.security
@pytest.mark.contract_static
def test_vitest_config_has_minimum_coverage_thresholds():
    _assert_minimum_coverage_thresholds(VITEST_CONFIG)


@pytest.mark.security
@pytest.mark.contract_static
def test_vite_config_has_minimum_coverage_thresholds():
    _assert_minimum_coverage_thresholds(VITE_CONFIG)


def _assert_minimum_coverage_thresholds(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    assert "thresholds:" in content
    thresholds = {
        key: int(value)
        for key, value in re.findall(
            r"\b(lines|functions|statements|branches):\s*(\d+)\b",
            content,
        )
    }
    assert thresholds["lines"] >= 60
    assert thresholds["functions"] >= 60
    assert thresholds["statements"] >= 60
    assert thresholds["branches"] >= 50


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
