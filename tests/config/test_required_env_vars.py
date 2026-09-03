from __future__ import annotations

import pytest
from tests.config._helpers import read_text
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


RUNTIME_BOOTSTRAP_FILES = (
    "services/api/app/main.py",
    "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
    "services/layer3-knowledge/src/api/main.py",
    "services/layer4-agents/src/layer4_agents/api/startup.py",
    "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
    "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
)

REQUIRED_PRODUCTION_ENV_VARS = (
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "API_KEY_HMAC_SECRET",
    "SERVICE_AUTH_SECRET",
    "CREDENTIALS_MASTER_KEY",
    "CORS_ORIGINS",
    "DEFAULT_TENANT_ID",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
)

CROSS_CUTTING_BOOT_ENV_VARS = (
    "DATABASE_URL",
    "JWT_SECRET",
    "API_KEY_HMAC_SECRET",
    "SERVICE_AUTH_SECRET",
    "CREDENTIALS_MASTER_KEY",
    "CORS_ORIGINS",
    "DEFAULT_TENANT_ID",
)


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
        tuple(f"{name}=" for name in REQUIRED_PRODUCTION_ENV_VARS)
        + (
            "LAYER1_DATABASE_URL=",
            "LAYER2_DATABASE_URL=",
            "LAYER4_DATABASE_URL=",
            "LAYER5_DATABASE_URL=",
            "LAYER6_DATABASE_URL=",
        ),
        label=".env.example required runtime inputs",
    )


def test_runtime_entrypoints_call_shared_production_safety_validator() -> None:
    missing = [
        path
        for path in RUNTIME_BOOTSTRAP_FILES
        if "validate_production_safety" not in read_text(path)
    ]
    assert not missing, (
        "Production boot entrypoints must call the shared fail-closed "
        f"validator; missing in: {missing}"
    )


def test_shared_validator_covers_required_production_domains() -> None:
    source = read_text("packages/shared/src/value_fabric/shared/security/config.py")
    for env_var in CROSS_CUTTING_BOOT_ENV_VARS:
        assert env_var in source, f"ProductionSafetyValidator does not reference {env_var}"
    for method in (
        "validate_authentication",
        "validate_persistence",
        "validate_encryption",
        "validate_api_keys",
        "validate_cors_origins",
        "validate_tenant_isolation",
        "validate_external_providers",
        "validate_debug_flags",
    ):
        assert method in source, f"ProductionSafetyValidator is missing {method}"
