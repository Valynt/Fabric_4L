from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_paths_exist, assert_pytest_coverage


pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


def test_secret_reference_policy_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/shared/secrets/test_infisical_bootstrap.py",
            "tests/security/test_secret_handling.py",
            "tests/security/test_secrets_protection.py",
            "tests/release/test_secret_policy.py",
        ),
        label="secret reference coverage",
    )


def test_external_secret_manifests_are_present_for_runtime_layers() -> None:
    assert_paths_exist(
        (
            "k8s/external-secrets/layer1-secrets.yaml",
            "k8s/external-secrets/layer2-secrets.yaml",
            "k8s/external-secrets/layer3-secrets.yaml",
            "k8s/external-secrets/layer4-secrets.yaml",
            "k8s/external-secrets/layer5-secrets.yaml",
            "k8s/external-secrets/layer6-secrets.yaml",
            "k8s/external-secrets/cluster-secret-store.yaml",
        ),
        label="external secret manifests",
    )


def test_env_example_points_to_secret_manager_bootstrap() -> None:
    assert_contains_all(
        ".env.example",
        ("INFISICAL_CLIENT_ID=", "INFISICAL_PROJECT_ID=", "INFISICAL_ENVIRONMENT=", "INFISICAL_HOST="),
        label="Infisical env reference",
    )

