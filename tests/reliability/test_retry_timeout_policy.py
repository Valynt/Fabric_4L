from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.reliability, pytest.mark.production_readiness]


def test_retry_and_timeout_failure_modes_are_covered() -> None:
    assert_pytest_coverage(
        (
            "tests/chaos/test_external_dependency_failure.py",
            "tests/chaos/test_database_failure.py",
            "tests/chaos/test_redis_failure.py",
            "tests/shared/identity/test_oidc_discover_retry.py",
        ),
        label="retry and timeout reliability coverage",
    )

