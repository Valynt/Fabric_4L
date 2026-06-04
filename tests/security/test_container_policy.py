"""Centralized manifest for container and deployment policy coverage."""

from __future__ import annotations

import pytest

from tests.security._category_manifest import assert_security_category_manifest

CONTAINER_POLICY_TESTS = (
    "tests/security/test_dockerfile_lockfile_fix.py",
    "tests/security/test_supply_chain.py",
    "tests/k8s/test_security_policies.py",
    "tests/ci/test_bunnyshell_environment_contract.py",
)


@pytest.mark.security
@pytest.mark.contract_static
def test_container_policy_security_coverage_manifest_is_current() -> None:
    assert_security_category_manifest("container_policy", CONTAINER_POLICY_TESTS)
