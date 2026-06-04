"""Centralized dependency and supply-chain security suite aggregation."""

from __future__ import annotations

import pytest

from tests.security.security_suite_manifest import category_by_key, iter_missing_paths, python_test_paths

CATEGORY = category_by_key("dependency_policy")


@pytest.mark.security
@pytest.mark.contract_static
def test_dependency_policy_coverage_manifest_is_current() -> None:
    """Dependency policy coverage is referenced without copying assertions."""
    missing = tuple(iter_missing_paths(CATEGORY))
    assert not missing, f"Stale dependency-policy manifest paths: {missing}"
    assert len(python_test_paths(CATEGORY)) >= 5


@pytest.mark.security
@pytest.mark.contract_static
def test_dependency_policy_includes_non_py_governance_checks() -> None:
    """Supply-chain coverage also points at package-manager/dependabot checks."""
    assert any(path.endswith(".mjs") for path in CATEGORY.paths)
    assert any(path.endswith("validate_dependabot_coverage.py") for path in CATEGORY.paths)
