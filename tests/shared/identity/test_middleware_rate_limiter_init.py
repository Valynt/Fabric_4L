from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from jose import (
    jwt as _jose_jwt,  # noqa: F401 — mandatory dep; python-jose already in layer4 dependencies
)
from value_fabric.shared.identity.middleware import (
    GovernanceMiddleware,
    RateLimiterConfigurationError,
)


@pytest.mark.parametrize("env_name", ["production", "prod", "staging"])
def test_prod_like_env_requires_redis(env_name: str) -> None:
    with patch.dict(os.environ, {"APP_ENV": env_name}, clear=False):
        with patch("value_fabric.shared.identity.middleware._get_worker_count", return_value=1):
            with pytest.raises(RateLimiterConfigurationError, match="Redis backend is required"):
                GovernanceMiddleware(app=MagicMock(), rate_limiter=None)


@pytest.mark.parametrize("env_name", ["development", "dev", "local", "test", "testing"])
def test_local_env_allows_memory_fallback(env_name: str) -> None:
    """Development environments allow memory backend fallback for rate limiting."""
    with patch.dict(os.environ, {"APP_ENV": env_name}, clear=False):
        with patch("value_fabric.shared.identity.middleware._get_worker_count", return_value=1):
            middleware = GovernanceMiddleware(app=MagicMock(), rate_limiter=None)
            assert middleware._rate_limiter_backend == "memory"


def test_unknown_env_without_redis_fails_closed() -> None:
    with patch.dict(os.environ, {"APP_ENV": "qa"}, clear=False):
        with patch("value_fabric.shared.identity.middleware._get_worker_count", return_value=1):
            with pytest.raises(RateLimiterConfigurationError):
                GovernanceMiddleware(app=MagicMock(), rate_limiter=None)


def test_startup_logs_selected_backend() -> None:
    """Startup logging records which rate limiter backend was selected."""
    with patch.dict(os.environ, {"APP_ENV": "development"}, clear=False):
        with patch("value_fabric.shared.identity.middleware._get_worker_count", return_value=1):
            with patch("value_fabric.shared.identity.middleware.logger.info") as mock_info:
                GovernanceMiddleware(app=MagicMock(), rate_limiter=None)
                assert mock_info.called
                log_line = mock_info.call_args[0][0]
                assert "rate_limiter_backend_selected" in log_line
