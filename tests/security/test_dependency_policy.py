"""Centralized manifest for dependency and supply-chain policy coverage."""

from __future__ import annotations

import pytest

from tests.security._category_manifest import assert_security_category_manifest

DEPENDENCY_POLICY_TESTS = (
    "tests/security/test_supply_chain.py",
    "tests/security/test_dependency_floor.py",
    "tests/security/test_dockerfile_lockfile_fix.py",
    "tests/security/test_provider_billing_posture.py",
    "tests/security/test_deprecated_l4_db_dependencies.py",
    "tests/security/test_frontend_coverage_thresholds.py",
    "tests/ci/test_bunnyshell_environment_contract.py",
)


@pytest.mark.security
@pytest.mark.contract_static
def test_dependency_policy_security_coverage_manifest_is_current() -> None:
    assert_security_category_manifest("dependency_policy", DEPENDENCY_POLICY_TESTS)
