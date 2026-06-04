from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage


pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


def test_environment_parity_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/config/test_environment_matrix.py",
            "tests/ci/test_env_contract_validator_i01.py",
            "tests/ci/test_bunnyshell_environment_contract.py",
        ),
        label="environment parity coverage",
    )


def test_production_readiness_policy_matrix_is_validated() -> None:
    assert_contains_all(
        "scripts/ci/validate_policy_enforcement_matrix.py",
        ("POLICY_DIR", "config/production-readiness", "matrix covers"),
        label="production readiness policy matrix validator",
    )

