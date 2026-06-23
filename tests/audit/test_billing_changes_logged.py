from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_paths_exist, assert_pytest_coverage, assert_readme_documents_gap


pytestmark = [pytest.mark.audit, pytest.mark.production_readiness]


def test_billing_change_audit_gap_is_documented_with_related_coverage() -> None:
    assert_pytest_coverage(
        (
            "tests/recovery/test_restore_billing_state.py",
            "tests/integration/billing_entitlements/test_billing_entitlements_regression.py",
            "services/layer4-agents/tests/test_billing_security_exceptions.py",
        ),
        label="billing change related coverage",
    )
    assert_paths_exist((".github/workflows/audit-evidence.yml",), label="audit evidence workflow")
    assert_readme_documents_gap("tests/audit/README.md", "BILLING_AUDIT_EVENT_FIXTURE")

