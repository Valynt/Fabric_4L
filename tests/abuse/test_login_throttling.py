from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_pytest_coverage

pytestmark = [pytest.mark.abuse, pytest.mark.production_readiness]


def test_login_throttling_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/security/test_auth_rate_limiting.py",
            "services/api/app/tests/test_clerk_webhook_idempotency.py",
        ),
        label="login throttling and auth replay coverage",
    )

