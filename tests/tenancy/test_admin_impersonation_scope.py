from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.tenancy, pytest.mark.production_readiness]


def test_admin_impersonation_scope_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "services/api/app/tests/test_impersonation_security.py",
            "tests/security/test_privileged_audit.py",
            "tests/integration/test_admin_audit_journey.py",
        ),
        label="admin impersonation tenant scope coverage",
    )

