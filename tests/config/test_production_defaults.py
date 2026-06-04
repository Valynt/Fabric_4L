from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage


pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


def test_production_default_guardrails_are_covered() -> None:
    assert_pytest_coverage(
        (
            "tests/config/test_environment_matrix.py",
            "tests/config/test_database_tls_validation.py",
            "tests/security/test_production_bypass_guardrails.py",
            "tests/security/test_dev_bypass.py",
        ),
        label="production default guardrail coverage",
    )


def test_config_policy_blocks_dev_bypass_flags_in_production() -> None:
    assert_contains_all(
        "contracts/config-policy/config_policy.yml",
        (
            "DEV_AUTH_BYPASS",
            "ALLOW_DEV_AUTH_BYPASS",
            "environment: production",
            "deny",
        ),
        label="config policy production bypass controls",
    )

