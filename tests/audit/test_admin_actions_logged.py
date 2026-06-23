from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.audit, pytest.mark.production_readiness]


def test_admin_action_audit_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/integration/test_admin_audit_journey.py",
            "tests/security/test_privileged_audit.py",
            "tests/security/test_sensitive_route_audit_coverage.py",
        ),
        label="admin action audit coverage",
    )

