"""Centralized manifest for authentication and authorization guard coverage."""

from __future__ import annotations

import pytest

from tests.security._category_manifest import assert_security_category_manifest

AUTH_GUARD_TESTS = (
    "tests/security/test_auth_boundaries.py",
    "tests/security/test_auth_default_deny.py",
    "tests/security/test_auth_source_validation.py",
    "tests/security/test_adversarial_auth.py",
    "tests/security/test_jwt_config_validation.py",
    "tests/security/test_jwt_validation.py",
    "tests/security/test_l1_metrics_access.py",
    "tests/security/test_l1_ssrf_blocklist.py",
    "tests/security/test_p0_5_api_key_rejection.py",
    "tests/security/test_rbac.py",
    "tests/security/test_websocket_auth.py",
    "packages/shared/src/value_fabric/shared/mcp_gateway/tests/security/test_auth_security.py",
    "services/api/app/tests/test_impersonation_security.py",
)


@pytest.mark.security
@pytest.mark.contract_static
def test_auth_guard_security_coverage_manifest_is_current() -> None:
    assert_security_category_manifest("auth_guards", AUTH_GUARD_TESTS)
