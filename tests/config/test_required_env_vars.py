from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage


pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


def test_required_environment_variable_coverage_is_centralized() -> None:
    assert_pytest_coverage(
        (
            "tests/config/test_startup_validation.py",
            "tests/config/test_startup_tenant_validation.py",
            "tests/config/test_environment_matrix.py",
        ),
        label="required environment variable config coverage",
    )


def test_env_example_documents_required_runtime_inputs() -> None:
    assert_contains_all(
        ".env.example",
        (
            "JWT_SECRET=",
            "REDIS_URL=",
            "NEO4J_URI=",
            "NEO4J_USER=",
            "NEO4J_PASSWORD=",
            "LAYER1_DATABASE_URL=",
            "LAYER2_DATABASE_URL=",
            "LAYER4_DATABASE_URL=",
            "LAYER5_DATABASE_URL=",
            "LAYER6_DATABASE_URL=",
            "LAYER7_DATABASE_URL=",
        ),
        label=".env.example required runtime inputs",
    )

