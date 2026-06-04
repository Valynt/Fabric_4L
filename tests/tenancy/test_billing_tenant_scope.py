from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.tenancy, pytest.mark.production_readiness]


def test_billing_tenant_scope_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/security/test_billing_tenant_boundary.py",
            "tests/recovery/test_restore_billing_state.py",
            "services/layer4-agents/tests/test_billing_tenant_scoped_customer_keys.py",
            "services/layer4-agents/tests/test_billing_security_exceptions.py",
        ),
        label="billing tenant scope coverage",
    )

