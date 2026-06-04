from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_entitlement_sync_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/contract/test_billing_contracts.py",
            "tests/integration/billing_entitlements/test_billing_entitlements_regression.py",
            "services/layer4-agents/tests/test_plan_version_billing.py",
        ),
        label="entitlement sync coverage",
    )

