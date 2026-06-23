from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.reliability, pytest.mark.production_readiness]


def test_dependency_failure_modes_have_deterministic_coverage() -> None:
    assert_pytest_coverage(
        (
            "tests/chaos/test_database_failure.py",
            "tests/chaos/test_redis_failure.py",
            "tests/chaos/test_llm_failure.py",
            "tests/chaos/test_external_dependency_failure.py",
            "tests/backend_integrated/test_operational_resilience_real_services.py",
        ),
        label="dependency failure mode coverage",
    )

