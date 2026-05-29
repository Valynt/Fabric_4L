"""Tests for auth mode — dev auth bypass permanently removed (F-23)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from value_fabric.shared.identity.auth_mode import (
    assert_safe_jwt_and_bypass_configuration,
    is_dev_bypass_enabled,
    validate_dev_bypass_configuration,
)


def test_is_dev_bypass_enabled_always_false() -> None:
    """Dev auth bypass has been permanently removed; always returns False."""
    with patch.dict(os.environ, {"DEV_AUTH_BYPASS": "true"}, clear=True):
        assert is_dev_bypass_enabled() is False


def test_validate_dev_bypass_configuration_never_raises() -> None:
    """validate_dev_bypass_configuration is a no-op after removal."""
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEV_AUTH_BYPASS": "true",
            "ALLOW_DEV_AUTH_BYPASS": "I_UNDERSTAND_RISK",
        },
        clear=True,
    ):
        # Should not raise — bypass mechanism is removed
        validate_dev_bypass_configuration()


def test_assert_safe_jwt_and_bypass_configuration_never_raises() -> None:
    """assert_safe_jwt_and_bypass_configuration is a no-op after removal."""
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEV_AUTH_BYPASS": "true",
            "ALLOW_DEV_AUTH_BYPASS": "I_UNDERSTAND_RISK",
        },
        clear=True,
    ):
        # Should not raise — bypass mechanism is removed
        assert_safe_jwt_and_bypass_configuration()


def test_add_governance_middleware_adds_middleware_without_raising() -> None:
    from fastapi import FastAPI
    from value_fabric.shared.fastapi_framework.middleware import add_governance_middleware

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
        middleware_classes = [m.cls for m in app.user_middleware]
        from value_fabric.shared.identity.middleware import GovernanceMiddleware
        assert GovernanceMiddleware in middleware_classes
