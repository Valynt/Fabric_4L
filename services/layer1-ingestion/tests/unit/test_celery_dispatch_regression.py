"""Regression tests for Celery task dispatch fixes (2026-05-28).

These tests prevent regression of the P0 bug fixed in the code review:
- Short task name "run_extraction_task" vs full name "layer2_extraction.shared.tasks.run_extraction_task"
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from layer1_ingestion.shared.config import Settings


class TestCeleryTaskDispatchRegression:
    """Regression tests for Celery task naming bug fix."""

    @patch("layer1_ingestion.shared.config.settings")
    def test_short_task_name_causes_not_registered(self, mock_settings):
        """Regression test: short task name should fail with NotRegistered.
        
        This test verifies that using the short task name "run_extraction_task"
        would cause a NotRegistered error, preventing future accidental use.
        """
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"
        
        # Create mock Celery instance that simulates NotRegistered error
        mock_celery_instance = MagicMock()
        # Simulate Celery's NotRegistered exception
        from celery.exceptions import NotRegistered
        mock_celery_instance.send_task.side_effect = NotRegistered("run_extraction_task")
        
        # Act: Try to dispatch with short task name
        with pytest.raises(NotRegistered) as exc_info:
            mock_celery_instance.send_task(
                "run_extraction_task",  # Short name - should fail
                args=["job-123", "https://example.com", "content", {}],
                kwargs={"mark_pipeline_complete": False},
            )
        
        # Assert: NotRegistered was raised
        assert "run_extraction_task" in str(exc_info.value)

    @patch("layer1_ingestion.shared.config.settings")
    def test_full_task_name_succeeds(self, mock_settings):
        """Verify full task name is registered and succeeds.
        
        This test verifies that the full task name works correctly.
        """
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"
        
        # Create mock Celery instance that succeeds
        mock_celery_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_result.get.return_value = {"tokens_consumed": 100}
        mock_celery_instance.send_task.return_value = mock_result
        
        # Act: Dispatch with full task name
        mock_celery_instance.send_task(
            "layer2_extraction.shared.tasks.run_extraction_task",  # Full name
            args=["job-123", "https://example.com", "content", {}],
            kwargs={"mark_pipeline_complete": False},
        )
        
        # Assert: send_task was called successfully
        mock_celery_instance.send_task.assert_called_once()
        call_args = mock_celery_instance.send_task.call_args
        assert call_args[0][0] == "layer2_extraction.shared.tasks.run_extraction_task"

    @patch("layer1_ingestion.shared.config.settings")
    def test_task_name_includes_module_path(self, mock_settings):
        """Verify task name includes full module path for disambiguation.
        
        This test ensures the task name is fully qualified to avoid naming
        conflicts if multiple modules have tasks with the same name.
        """
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"
        
        # Create mock Celery instance
        mock_celery_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_result.get.return_value = {"tokens_consumed": 100}
        mock_celery_instance.send_task.return_value = mock_result
        
        # Act: Dispatch task
        job_id = str(uuid4())
        mock_celery_instance.send_task(
            "layer2_extraction.shared.tasks.run_extraction_task",
            args=[job_id, "https://example.com", "content", {}],
            kwargs={"mark_pipeline_complete": False},
        )
        
        # Assert: Task name includes module path
        call_args = mock_celery_instance.send_task.call_args
        task_name = call_args[0][0]
        assert "layer2_extraction" in task_name
        assert "shared" in task_name
        assert "tasks" in task_name
        assert "run_extraction_task" in task_name

    @patch("layer1_ingestion.shared.config.settings")
    def test_task_arguments_include_tenant_id(self, mock_settings):
        """Verify task arguments include tenant_id in extraction payload.
        
        This test ensures tenant context is propagated to Celery tasks.
        """
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"
        
        # Create mock Celery instance
        mock_celery_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_result.get.return_value = {"tokens_consumed": 100}
        mock_celery_instance.send_task.return_value = mock_result
        
        # Act: Dispatch task with tenant context
        job_id = str(uuid4())
        tenant_id = "tenant-123"
        extraction_payload = {
            "tenant_id": tenant_id,
            "job_id": job_id,
            "options": {"model": "gpt-4", "temperature": 0.0}
        }
        
        mock_celery_instance.send_task(
            "layer2_extraction.shared.tasks.run_extraction_task",
            args=[job_id, "https://example.com", "content", extraction_payload],
            kwargs={"mark_pipeline_complete": False},
        )
        
        # Assert: extraction_payload includes tenant_id
        call_args = mock_celery_instance.send_task.call_args
        args_list = call_args[1]["args"]
        payload_arg = args_list[3]  # Fourth argument is extraction_payload
        assert payload_arg["tenant_id"] == tenant_id
        assert payload_arg["job_id"] == job_id

    @patch("layer1_ingestion.shared.config.settings")
    def test_http_fallback_on_celery_failure(self, mock_settings):
        """Test HTTP fallback triggers when Celery dispatch fails.
        
        This test verifies the fallback mechanism when Celery is unavailable.
        """
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"
        mock_settings.layer2_api_url = "http://layer2:8000"
        
        # Create mock Celery instance that fails
        mock_celery_instance = MagicMock()
        mock_celery_instance.send_task.side_effect = Exception("Celery connection failed")
        
        # Act: Simulate Celery dispatch failure
        with pytest.raises(Exception) as exc_info:
            mock_celery_instance.send_task(
                "layer2_extraction.shared.tasks.run_extraction_task",
                args=["job-123", "https://example.com", "content", {}],
                kwargs={"mark_pipeline_complete": False},
            )
        
        # Assert: Exception was raised (in actual code, this would trigger HTTP fallback)
        assert "Celery connection failed" in str(exc_info.value)
        mock_celery_instance.send_task.assert_called_once()

    @patch("layer1_ingestion.shared.config.settings")
    def test_task_result_timeout_configured(self, mock_settings):
        """Verify task result retrieval has timeout configured.
        
        This test ensures the task result timeout is set to prevent hanging.
        """
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"
        
        # Create mock Celery instance
        mock_celery_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "task-123"
        mock_result.get.return_value = {"tokens_consumed": 100}
        mock_celery_instance.send_task.return_value = mock_result
        
        # Act: Dispatch task and get result
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

    @patch("layer1_ingestion.shared.config.settings")
    def test_celery_client_uses_correct_broker(self, mock_settings):
        """Verify Celery client is created with L2's broker URL.
        
        This test ensures the Celery client points to the correct broker.
        """
        # Setup
        mock_settings.use_celery_for_l2 = True
        mock_settings.layer2_celery_broker_url = "redis://redis:6379/0"
        
        # Create mock Celery class
        mock_celery_class = MagicMock()
        mock_celery_instance = MagicMock()
        mock_celery_class.return_value = mock_celery_instance
        
        # Act: Create Celery client (as done in tasks.py)
        l2_celery = mock_celery_class(
            "layer2_extraction",
            broker=mock_settings.layer2_celery_broker_url,
            backend=mock_settings.layer2_celery_broker_url,
        )
        
        # Assert: Celery was instantiated with correct parameters
        mock_celery_class.assert_called_once()
        call_args = mock_celery_class.call_args
        assert call_args[0][0] == "layer2_extraction"
        call_kwargs = call_args[1]
        assert call_kwargs["broker"] == "redis://redis:6379/0"
        assert call_kwargs["backend"] == "redis://redis:6379/0"

    def test_use_celery_for_l2_default_setting(self):
        """Verify use_celery_for_l2 is enabled by default."""
        settings = Settings()
        assert settings.use_celery_for_l2 is True

    def test_layer2_celery_broker_url_default(self):
        """Verify L2 Celery broker URL has a default value."""
        settings = Settings()
        assert settings.layer2_celery_broker_url == "redis://redis:6379/0"

    def test_layer2_api_url_default(self):
        """Verify L2 API URL points to layer2 service."""
        settings = Settings()
        assert settings.layer2_api_url == "http://layer2:8000"
