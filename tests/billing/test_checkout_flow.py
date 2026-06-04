from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_paths_exist, assert_readme_documents_gap


pytestmark = [pytest.mark.billing, pytest.mark.production_readiness]


def test_checkout_flow_has_documented_non_credential_gap_and_ui_coverage() -> None:
    assert_paths_exist(
        (
            "apps/web/e2e/journeys/j20-billing-entitlement-gates.spec.ts",
            "services/billing/tests/test_api.py",
            "contracts/openapi/layer7-billing.json",
        ),
        label="checkout flow references",
    )
    assert_readme_documents_gap("tests/billing/README.md", "CHECKOUT_PROVIDER_SANDBOX")

