from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_pytest_coverage

pytestmark = [pytest.mark.abuse, pytest.mark.production_readiness]


def test_rate_limit_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/security/test_rate_limit_safety.py",
            "tests/security/test_rate_limit_window.py",
            "tests/security/test_rate_limit_response.py",
            "tests/shared/identity/test_rate_limit_contract.py",
            "tests/unit/l3/test_rate_limiter_algorithms.py",
        ),
        label="rate limit abuse coverage",
    )

