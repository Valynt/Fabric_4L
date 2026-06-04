"""Centralized authentication/authorization security suite aggregation."""

from __future__ import annotations

import pytest

from tests.security.security_suite_manifest import category_by_key, iter_missing_paths, python_test_paths

CATEGORY = category_by_key("auth_guards")


@pytest.mark.security
@pytest.mark.contract_static
def test_auth_guard_coverage_manifest_is_current() -> None:
    """Auth guard coverage is referenced from existing focused tests."""
    missing = tuple(iter_missing_paths(CATEGORY))
    assert not missing, f"Stale auth guard manifest paths: {missing}"
    assert len(python_test_paths(CATEGORY)) >= 10


@pytest.mark.security
@pytest.mark.contract_static
def test_auth_guard_coverage_references_no_duplicate_modules() -> None:
    """The aggregator must reference existing modules rather than duplicate them."""
    assert len(CATEGORY.paths) == len(set(CATEGORY.paths))
