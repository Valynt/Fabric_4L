from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_pytest_coverage, assert_readme_documents_gap

pytestmark = [pytest.mark.audit, pytest.mark.production_readiness]


def test_support_impersonation_audit_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "services/api/app/tests/test_impersonation_security.py",
            "tests/security/test_privileged_audit.py",
        ),
        label="support impersonation audit coverage",
    )
    assert_readme_documents_gap("tests/audit/README.md", "SUPPORT_PROVIDER_SESSION_REPLAY")

