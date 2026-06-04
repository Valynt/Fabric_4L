from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.audit, pytest.mark.production_readiness]


def test_auth_event_audit_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/security/test_auth_logging.py",
            "tests/security/test_audit_event_emission.py",
            "services/api/app/tests/test_audit_middleware.py",
        ),
        label="auth event audit coverage",
    )

