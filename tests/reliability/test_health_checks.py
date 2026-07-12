from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_pytest_coverage

pytestmark = [pytest.mark.reliability, pytest.mark.production_readiness]


def test_health_check_contract_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/contract/test_health_contract_and_red_metrics.py",
            "tests/contract/test_service_observability_contracts.py",
            "tests/backend_integrated/test_layer_health_checks.py",
            "tests/ci/test_stack_health_check_contract.py",
        ),
        label="health check reliability coverage",
    )

