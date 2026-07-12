from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_pytest_coverage

pytestmark = [pytest.mark.reliability, pytest.mark.production_readiness]


def test_graceful_degradation_paths_are_covered() -> None:
    assert_pytest_coverage(
        (
            "tests/chaos/test_redis_failure.py",
            "tests/chaos/test_llm_failure.py",
            "tests/chaos/test_external_dependency_failure.py",
        ),
        label="graceful degradation coverage",
    )

