from __future__ import annotations

import logging

import pytest

from layer4_agents.startup.dependency_verifier import (
    DependencyRule,
    verify_layer4_startup_dependencies,
    verify_startup_dependencies,
)


def test_layer4_production_fails_closed_for_required_dependency() -> None:
    with pytest.raises(RuntimeError, match="layer4_missing_dependency_for_tests"):
        verify_startup_dependencies(
            [
                DependencyRule(
                    module="layer4_missing_dependency_for_tests",
                    required_in_prod=True,
                    remediation="pip install layer4_missing_dependency_for_tests",
                )
            ],
            environment="staging",
        )


def test_layer4_development_allows_optional_dependency(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)

    verify_startup_dependencies(
        [
            DependencyRule(
                module="layer4_missing_optional_dependency_for_tests",
                required_in_prod=False,
                remediation="pip install layer4_missing_optional_dependency_for_tests",
            )
        ],
        environment="development",
    )

    assert "layer4_missing_optional_dependency_for_tests" in caplog.text
    assert "Remediation" in caplog.text


def test_layer4_development_permits_missing_required_dependency(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    verify_startup_dependencies(
        [
            DependencyRule(
                module="layer4_missing_required_dependency_for_dev_tests",
                required_in_prod=True,
                remediation="pip install layer4_missing_required_dependency_for_dev_tests",
            )
        ],
        environment="development",
    )
    assert "layer4_missing_required_dependency_for_dev_tests" in caplog.text


def test_layer4_startup_dependency_catalog_has_prod_and_dev_classification() -> None:
    verify_layer4_startup_dependencies(environment="development")
