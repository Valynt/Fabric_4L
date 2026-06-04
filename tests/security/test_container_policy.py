"""Centralized container and deployment security suite aggregation."""

from __future__ import annotations

import pytest

from tests.security.security_suite_manifest import category_by_key, iter_missing_paths, python_test_paths

CATEGORY = category_by_key("container_policy")


@pytest.mark.security
@pytest.mark.contract_static
def test_container_policy_coverage_manifest_is_current() -> None:
    """Container policy coverage is referenced from existing tests and policy files."""
    missing = tuple(iter_missing_paths(CATEGORY))
    assert not missing, f"Stale container-policy manifest paths: {missing}"
    assert len(python_test_paths(CATEGORY)) >= 4


@pytest.mark.security
@pytest.mark.contract_static
def test_container_policy_includes_kubernetes_and_workflow_policy() -> None:
    """Container coverage includes both cluster policy and workflow security gates."""
    assert "k8s/policy/security-hardening.rego" in CATEGORY.paths
    assert ".github/workflows/security-gates.yml" in CATEGORY.paths
