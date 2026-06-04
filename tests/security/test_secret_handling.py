"""Centralized secret-handling security suite aggregation."""

from __future__ import annotations

import pytest

from tests.security.security_suite_manifest import category_by_key, iter_missing_paths, python_test_paths

CATEGORY = category_by_key("secret_handling")


@pytest.mark.security
@pytest.mark.contract_static
def test_secret_handling_coverage_manifest_is_current() -> None:
    """Secret and sensitive-data controls are covered by existing tests."""
    missing = tuple(iter_missing_paths(CATEGORY))
    assert not missing, f"Stale secret-handling manifest paths: {missing}"
    assert len(python_test_paths(CATEGORY)) >= 8


@pytest.mark.security
@pytest.mark.contract_static
def test_secret_handling_coverage_references_no_duplicate_modules() -> None:
    """The aggregator must reference existing modules rather than duplicate them."""
    assert len(CATEGORY.paths) == len(set(CATEGORY.paths))
