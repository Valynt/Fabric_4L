"""Centralized manifest for secret handling and redaction coverage."""

from __future__ import annotations

import pytest

from tests.security._category_manifest import assert_security_category_manifest

SECRET_HANDLING_TESTS = (
    "tests/security/test_secrets_protection.py",
    "tests/security/test_production_bypass_guardrails.py",
    "tests/security/test_dev_bypass.py",
    "tests/security/test_startup_bypass_nonzero_exit.py",
    "tests/security/test_h03_service_startup_validation.py",
    "packages/shared/src/value_fabric/shared/security/tests/test_production_safety.py",
    "tests/security/test_cross_stack_jwt_contract.py",
    "tests/security/test_jwt_rotation.py",
    "tests/ci/test_bunnyshell_environment_contract.py",
    "services/api/app/tests/test_bcrypt_security.py",
)


@pytest.mark.security
@pytest.mark.contract_static
def test_secret_handling_security_coverage_manifest_is_current() -> None:
    assert_security_category_manifest("secret_handling", SECRET_HANDLING_TESTS)
