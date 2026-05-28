"""Unit tests for Layer 2 Celery tasks."""

import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

# Check if celery is available before importing
try:
    import celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CELERY_AVAILABLE, reason="celery not installed")

if CELERY_AVAILABLE:
    from layer2_extraction.shared.tasks import celery_app, run_extraction_task, extract_entities_task, extract_relationships_task


class TestCeleryAppConfiguration:
    """Test Celery app configuration."""

    def test_celery_app_name(self) -> None:
        """Celery app must be named 'layer2_extraction'."""
        assert celery_app.main == "layer2_extraction"

    def test_celery_task_serializer(self) -> None:
        """Celery must use JSON serialization."""
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]

    def test_celery_timezone(self) -> None:
        """Celery must use UTC timezone."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_task_time_limit(self) -> None:
        """Celery tasks must have a time limit."""
        assert celery_app.conf.task_time_limit == 3600  # 1 hour

    def test_celery_retry_configuration(self) -> None:
        """Celery must be configured for retries."""
        assert celery_app.conf.task_max_retries == 3
        assert celery_app.conf.task_default_retry_delay == 60


class TestRunExtractionTask:
    """Test run_extraction_task Celery task."""

    @patch("layer2_extraction.shared.tasks.asyncio")
    @patch("layer2_extraction.shared.tasks.run_extraction")
    def test_run_extraction_task_success(self, mock_run_extraction, mock_asyncio):
        """Test successful extraction task execution."""
        # Setup
        mock_run_extraction.return_value = {"status": "completed"}
        mock_asyncio.run.return_value = {"status": "completed"}

        # Execute
        result = run_extraction_task(
            job_id="test-job-123",
            source_url="https://example.com",
            content="Test content",
            config={"tenant_id": "tenant-1"},
            mark_pipeline_complete=False,
        )

        # Verify
        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        mock_asyncio.run.assert_called_once()

    @patch("layer2_extraction.shared.tasks.asyncio")
    @patch("layer2_extraction.shared.tasks.run_extraction")
    def test_run_extraction_task_failure_with_retry(self, mock_run_extraction, mock_asyncio):
        """Test extraction task failure triggers retry."""
        # Setup
        mock_run_extraction.side_effect = Exception("Extraction failed")
        mock_asyncio.run.side_effect = Exception("Extraction failed")

        # Create mock task self
        task_self = Mock()
        task_self.request.retries = 0

        # Execute and verify retry
        with pytest.raises(Exception):
            run_extraction_task(
                task_self,
                job_id="test-job-123",
                source_url="https://example.com",
                content="Test content",
                config={"tenant_id": "tenant-1"},
            )

        # Verify retry was called
        task_self.retry.assert_called_once()


class TestExtractEntitiesTask:
    """Test extract_entities_task Celery task."""

    @patch("layer2_extraction.shared.tasks.asyncio")
    @patch("layer2_extraction.shared.tasks.EntityExtractor")
    @patch("layer2_extraction.shared.tasks.chunk_markdown")
    def test_extract_entities_task_success(self, mock_chunk, mock_extractor_class, mock_asyncio):
        """Test successful entity extraction task."""
        # Setup
        mock_chunk.return_value = ["chunk1", "chunk2"]
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_entities.return_value = [{"name": "Entity1"}]
        mock_asyncio.run.return_value = [{"name": "Entity1"}]

        # Execute
        result = extract_entities_task(
            job_id="test-job-123",
            content="Test content",
            config={"source_url": "https://example.com"},
        )

        # Verify
        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        assert result["entity_count"] == 2  # 2 chunks x 1 entity each

    @patch("layer2_extraction.shared.tasks.asyncio")
    @patch("layer2_extraction.shared.tasks.EntityExtractor")
    @patch("layer2_extraction.shared.tasks.chunk_markdown")
    def test_extract_entities_task_failure_with_retry(self, mock_chunk, mock_extractor_class, mock_asyncio):
        """Test entity extraction failure triggers retry."""
        # Setup
        mock_chunk.side_effect = Exception("Chunking failed")
        mock_asyncio.run.side_effect = Exception("Chunking failed")

        # Create mock task self
        task_self = Mock()
        task_self.request.retries = 0

        # Execute and verify retry
        with pytest.raises(Exception):
            extract_entities_task(
                task_self,
                job_id="test-job-123",
                content="Test content",
                config={"source_url": "https://example.com"},
            )

        # Verify retry was called
        task_self.retry.assert_called_once()


class TestExtractRelationshipsTask:
    """Test extract_relationships_task Celery task."""

    @patch("layer2_extraction.shared.tasks.asyncio")
    @patch("layer2_extraction.shared.tasks.RelationshipExtractor")
    def test_extract_relationships_task_success(self, mock_extractor_class, mock_asyncio):
        """Test successful relationship extraction task."""
        # Setup
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_relationships.return_value = [{"source": "A", "target": "B"}]
        mock_asyncio.run.return_value = [{"source": "A", "target": "B"}]

        # Execute
        result = extract_relationships_task(
            job_id="test-job-123",
            entities=[{"name": "Entity1"}],
            config={},
        )

        # Verify
        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        assert result["relationship_count"] == 1

    @patch("layer2_extraction.shared.tasks.asyncio")
    @patch("layer2_extraction.shared.tasks.RelationshipExtractor")
    def test_extract_relationships_task_failure_with_retry(self, mock_extractor_class, mock_asyncio):
        """Test relationship extraction failure triggers retry."""
        # Setup
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_relationships.side_effect = Exception("Extraction failed")
        mock_asyncio.run.side_effect = Exception("Extraction failed")

        # Create mock task self
        task_self = Mock()
        task_self.request.retries = 0

        # Execute and verify retry
        with pytest.raises(Exception):
            extract_relationships_task(
                task_self,
                job_id="test-job-123",
                entities=[{"name": "Entity1"}],
                config={},
            )

        # Verify retry was called
        task_self.retry.assert_called_once()
