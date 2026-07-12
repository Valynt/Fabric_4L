from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_pytest_coverage

pytestmark = [pytest.mark.abuse, pytest.mark.production_readiness]


def test_webhook_replay_limit_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/unit/l7/test_webhook_security.py",
            "services/api/app/tests/test_clerk_webhook_idempotency.py",
            "services/layer4-agents/tests/test_webhook_security.py",
            "services/layer4-agents/tests/test_billing_webhook_security_consistency.py",
        ),
        label="webhook replay limit coverage",
    )

