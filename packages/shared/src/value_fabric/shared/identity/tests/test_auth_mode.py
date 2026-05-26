"""Tests for auth mode startup safety checks."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from value_fabric.shared.fastapi_framework.middleware import add_governance_middleware
from value_fabric.shared.identity.auth_mode import (
    assert_safe_jwt_and_bypass_configuration,
    validate_dev_bypass_configuration,
)


def test_dev_bypass_rejected_outside_development() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEV_AUTH_BYPASS": "true",
            "ALLOW_DEV_AUTH_BYPASS": "I_UNDERSTAND_RISK",
        },
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="only permitted when ENVIRONMENT=development"):
            validate_dev_bypass_configuration()


def test_dev_bypass_requires_explicit_ack_token() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "development",
            "DEV_AUTH_BYPASS": "true",
        },
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="ALLOW_DEV_AUTH_BYPASS=I_UNDERSTAND_RISK"):
            validate_dev_bypass_configuration()


def test_dev_bypass_valid_in_development_with_ack() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "development",
            "DEV_AUTH_BYPASS": "true",
            "ALLOW_DEV_AUTH_BYPASS": "I_UNDERSTAND_RISK",
        },
        clear=True,
    ):
        validate_dev_bypass_configuration()


@pytest.mark.parametrize("environment", ["production", "staging", "prod-like"])
def test_startup_guard_blocks_jwt_with_dev_bypass_toggles(environment: str) -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": environment,
            "DEV_AUTH_BYPASS": "false",
            "ALLOW_DEV_AUTH_BYPASS": "I_UNDERSTAND_RISK",
        },
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="Production-like environment cannot run"):
            assert_safe_jwt_and_bypass_configuration()


def test_add_governance_middleware_adds_middleware_without_raising() -> None:
    from fastapi import FastAPI

    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEV_AUTH_BYPASS": "false",
            "ALLOW_DEV_AUTH_BYPASS": "I_UNDERSTAND_RISK",
        },
        clear=True,
    ):
        app = FastAPI()
        add_governance_middleware(app)
        # GovernanceMiddleware should be registered
        middleware_classes = [m.cls for m in app.user_middleware]
        from value_fabric.shared.identity.middleware import GovernanceMiddleware
        assert GovernanceMiddleware in middleware_classes

