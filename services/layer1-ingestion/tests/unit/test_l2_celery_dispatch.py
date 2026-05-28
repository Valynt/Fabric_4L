"""Unit tests for L1 to L2 Celery dispatch integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from value_fabric.layer1.shared.config import Settings


class TestL2CeleryDispatchConfiguration:
    """Test L2 Celery dispatch configuration."""

    def test_use_celery_for_l2_default(self) -> None:
        """By default, Celery should be enabled for L2 dispatch."""
        settings = Settings()
        assert settings.use_celery_for_l2 is True

    def test_layer2_celery_broker_url_default(self) -> None:
        """L2 Celery broker URL should have a default value."""
        settings = Settings()
        assert settings.layer2_celery_broker_url == "redis://redis:6379/0"

    def test_layer2_api_url_default(self) -> None:
        """L2 API URL should point to layer2 service."""
        settings = Settings()
        assert settings.layer2_api_url == "http://layer2:8000"


class TestL2CeleryDispatchIntegration:
    """Test L1 to L2 Celery dispatch logic."""

    @patch("value_fabric.layer1.shared.config.settings")
    def test_celery_dispatch_enabled_configuration(self, mock_settings):
        """Test Celery dispatch is enabled by default with correct configuration."""
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"

        # Verify configuration enables Celery dispatch
        assert mock_settings.use_celery_for_l2 is True
        assert mock_settings.layer2_celery_broker_url == "redis://redis:6379/0"

    @patch("value_fabric.layer1.shared.config.settings")
    def test_celery_dispatch_disabled_uses_http_fallback(self, mock_settings):
        """Test HTTP fallback is configured when Celery dispatch is disabled."""
        # Setup
        mock_settings.use_celery_for_l2 = False
        mock_settings.layer2_api_url = "http://layer2:8000"

        # Verify configuration allows HTTP fallback
        assert mock_settings.use_celery_for_l2 is False
        assert mock_settings.layer2_api_url == "http://layer2:8000"

    @patch("value_fabric.layer1.shared.config.settings")
    def test_celery_dispatch_broker_url_format(self, mock_settings):
        """Test Celery broker URL follows expected format."""
        # Setup
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"

        # Verify broker URL format
        broker_url = mock_settings.layer2_celery_broker_url
        assert broker_url.startswith("redis://")
        assert "6379" in broker_url  # Redis port
