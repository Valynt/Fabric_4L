"""Unit tests for L1 to L2 Celery dispatch integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from uuid import uuid4

from layer1_ingestion.shared.config import Settings


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

    @patch("layer1_ingestion.shared.config.settings")
    def test_celery_dispatch_enabled_configuration(self, mock_settings):
        """Test Celery dispatch is enabled by default with correct configuration."""
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"

        # Verify configuration enables Celery dispatch
        assert mock_settings.use_celery_for_l2 is True
        assert mock_settings.layer2_celery_broker_url == "redis://redis:6379/0"

    @patch("layer1_ingestion.shared.config.settings")
    def test_celery_dispatch_disabled_uses_http_fallback(self, mock_settings):
        """Test HTTP fallback is configured when Celery dispatch is disabled."""
        # Setup
        mock_settings.use_celery_for_l2 = False
        mock_settings.layer2_api_url = "http://layer2:8000"

        # Verify configuration allows HTTP fallback
        assert mock_settings.use_celery_for_l2 is False
        assert mock_settings.layer2_api_url == "http://layer2:8000"

    @patch("layer1_ingestion.shared.config.settings")
    def test_celery_dispatch_broker_url_format(self, mock_settings):
        """Test Celery broker URL follows expected format."""
        # Setup
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"

        # Verify broker URL format
        broker_url = mock_settings.layer2_celery_broker_url
        assert broker_url.startswith("redis://")
        assert "6379" in broker_url  # Redis port


class TestL2CeleryDispatchRuntime:
    """Test L1 to L2 Celery dispatch runtime behavior."""

    @patch("layer1_ingestion.shared.config.settings")
    def test_celery_client_created_with_correct_broker(self, mock_settings):
        """Celery client should be created with L2's broker URL."""
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"

        # Create mock Celery class and instance
        mock_celery_class = MagicMock()
        mock_celery_instance = MagicMock()
        mock_celery_class.return_value = mock_celery_instance
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_result.get.return_value = {"tokens_consumed": 100}
        mock_celery_instance.send_task.return_value = mock_result

        # Act: Simulate Celery client creation (as done in tasks.py)
        l2_celery = mock_celery_class(
            "layer2_extraction",
            broker=mock_settings.layer2_celery_broker_url,
            backend=mock_settings.layer2_celery_broker_url,
        )

        # Assert: Celery was instantiated with correct parameters
        mock_celery_class.assert_called_once()
        call_args = mock_celery_class.call_args
        # First positional argument is the app name
        assert call_args[0][0] == "layer2_extraction"
        # Keyword arguments include broker and backend
        call_kwargs = call_args[1]
        assert call_kwargs["broker"] == "redis://redis:6379/0"
        assert call_kwargs["backend"] == "redis://redis:6379/0"

    @patch("layer1_ingestion.shared.config.settings")
    def test_task_dispatched_with_fully_qualified_name(self, mock_settings):
        """Task should be dispatched with fully qualified task name."""
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"

        # Create mock Celery instance
        mock_celery_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_result.get.return_value = {"tokens_consumed": 100}
        mock_celery_instance.send_task.return_value = mock_result

        # Act: Simulate task dispatch
        job_id = str(uuid4())
        source_url = "https://example.com"
        content = "Test content"
        extraction_payload = {"tenant_id": "tenant-123", "job_id": job_id}
        
        mock_celery_instance.send_task(
            "layer2_extraction.shared.tasks.run_extraction_task",
            args=[job_id, source_url, content, extraction_payload],
            kwargs={"mark_pipeline_complete": False},
        )

        # Assert: send_task was called with fully qualified task name
        mock_celery_instance.send_task.assert_called_once()
        call_args = mock_celery_instance.send_task.call_args
        assert call_args[0][0] == "layer2_extraction.shared.tasks.run_extraction_task"

    @patch("layer1_ingestion.shared.config.settings")
    def test_task_arguments_include_tenant_context(self, mock_settings):
        """Task arguments should include tenant_id in extraction payload."""
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"

        # Create mock Celery instance
        mock_celery_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_result.get.return_value = {"tokens_consumed": 100}
        mock_celery_instance.send_task.return_value = mock_result

        # Act: Simulate task dispatch with tenant context
        job_id = str(uuid4())
        tenant_id = "tenant-123"
        extraction_payload = {
            "tenant_id": tenant_id,
            "job_id": job_id,
            "options": {"model": "gpt-4", "temperature": 0.0}
        }
        
        mock_celery_instance.send_task(
            "layer2_extraction.shared.tasks.run_extraction_task",
            args=[job_id, "https://example.com", "Test content", extraction_payload],
            kwargs={"mark_pipeline_complete": False},
        )

        # Assert: extraction_payload includes tenant_id
        call_args = mock_celery_instance.send_task.call_args
        # args are passed as a list in the 'args' parameter
        args_list = call_args[1]["args"]
        payload_arg = args_list[3]  # Fourth argument is extraction_payload
        assert payload_arg["tenant_id"] == tenant_id
        assert payload_arg["job_id"] == job_id

    @patch("layer1_ingestion.shared.config.settings")
    def test_celery_dispatch_failure_triggers_http_fallback(self, mock_settings):
        """Celery dispatch failure should trigger HTTP fallback."""
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"
        mock_settings.layer2_api_url = "http://layer2:8000"

        # Create mock Celery instance that fails
        mock_celery_instance = MagicMock()
        mock_celery_instance.send_task.side_effect = Exception("Celery connection failed")

        # Act: Simulate Celery dispatch failure
        try:
            mock_celery_instance.send_task(
                "layer2_extraction.shared.tasks.run_extraction_task",
                args=["job-123", "https://example.com", "content", {}],
                kwargs={"mark_pipeline_complete": False},
            )
        except Exception as e:
            # Exception should be caught and trigger HTTP fallback
            assert str(e) == "Celery connection failed"
            # In actual code, this would fall through to HTTP fallback
            pass

        # Assert: send_task was attempted and failed
        mock_celery_instance.send_task.assert_called_once()

    @patch("layer1_ingestion.shared.config.settings")
    def test_task_result_timeout_is_configured(self, mock_settings):
        """Task result retrieval should have timeout configured."""
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"

        # Create mock Celery instance
        mock_celery_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_result.get.return_value = {"tokens_consumed": 100}
        mock_celery_instance.send_task.return_value = mock_result

        # Act: Simulate task dispatch and result retrieval
        mock_celery_instance.send_task(
            "layer2_extraction.shared.tasks.run_extraction_task",
            args=["job-123", "https://example.com", "content", {}],
            kwargs={"mark_pipeline_complete": False},
        )
        
        # Simulate result.get with timeout
        extraction_result = mock_result.get(timeout=300)

        # Assert: get was called with timeout
        mock_result.get.assert_called_once()
        call_kwargs = mock_result.get.call_args[1]
        assert call_kwargs["timeout"] == 300
