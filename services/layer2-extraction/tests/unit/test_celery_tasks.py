"""Unit tests for Layer 2 Celery tasks."""

from unittest.mock import AsyncMock, Mock, patch

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

    @pytest.mark.asyncio
    @patch("layer2_extraction.api.main.run_extraction")
    async def test_run_extraction_task_success(self, mock_run_extraction):
        """Test successful extraction task execution."""
        mock_run_extraction.return_value = {"status": "completed"}

        result = await run_extraction_task(
            job_id="test-job-123",
            source_url="https://example.com",
            content="Test content",
            config={"tenant_id": "tenant-1"},
            mark_pipeline_complete=False,
        )

        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        mock_run_extraction.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(run_extraction_task, "retry")
    @patch("layer2_extraction.api.main.run_extraction")
    async def test_run_extraction_task_failure_with_retry(self, mock_run_extraction, mock_retry):
        """Test extraction task failure triggers retry."""
        mock_run_extraction.side_effect = Exception("Extraction failed")
        mock_retry.side_effect = Exception("Retry triggered")

        with pytest.raises(Exception, match="Retry triggered"):
            await run_extraction_task(
                job_id="test-job-123",
                source_url="https://example.com",
                content="Test content",
                config={"tenant_id": "tenant-1"},
            )

        mock_retry.assert_called_once()


class TestExtractEntitiesTask:
    """Test extract_entities_task Celery task."""

    @pytest.mark.asyncio
    @patch("layer2_extraction.extraction.llm_extractor.EntityExtractor")
    @patch("layer2_extraction.extraction.chunker.chunk_markdown")
    async def test_extract_entities_task_success(self, mock_chunk, mock_extractor_class):
        """Test successful entity extraction task."""
        mock_chunk.return_value = ["chunk1", "chunk2"]
        mock_extractor = AsyncMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_entities.return_value = [{"name": "Entity1"}]

        result = await extract_entities_task(
            job_id="test-job-123",
            content="Test content",
            config={"source_url": "https://example.com", "tenant_id": "tenant-1"},
        )

        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        assert result["entity_count"] == 2  # 2 chunks x 1 entity each

    @pytest.mark.asyncio
    @patch.object(extract_entities_task, "retry")
    @patch("layer2_extraction.extraction.llm_extractor.EntityExtractor")
    @patch("layer2_extraction.extraction.chunker.chunk_markdown")
    async def test_extract_entities_task_failure_with_retry(self, mock_chunk, mock_extractor_class, mock_retry):
        """Test entity extraction failure triggers retry."""
        mock_chunk.side_effect = Exception("Chunking failed")
        mock_retry.side_effect = Exception("Retry triggered")

        with pytest.raises(Exception, match="Retry triggered"):
            await extract_entities_task(
                job_id="test-job-123",
                content="Test content",
                config={"source_url": "https://example.com", "tenant_id": "tenant-1"},
            )

        mock_retry.assert_called_once()


class TestExtractRelationshipsTask:
    """Test extract_relationships_task Celery task."""

    @pytest.mark.asyncio
    @patch("layer2_extraction.extraction.llm_extractor.RelationshipExtractor")
    async def test_extract_relationships_task_success(self, mock_extractor_class):
        """Test successful relationship extraction task."""
        mock_extractor = AsyncMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_relationships.return_value = [{"source": "A", "target": "B"}]

        result = await extract_relationships_task(
            job_id="test-job-123",
            entities=[{"name": "Entity1"}],
            config={"tenant_id": "tenant-1"},
        )

        assert result["success"] is True
        assert result["job_id"] == "test-job-123"
        assert result["relationship_count"] == 1

    @pytest.mark.asyncio
    @patch.object(extract_relationships_task, "retry")
    @patch("layer2_extraction.extraction.llm_extractor.RelationshipExtractor")
    async def test_extract_relationships_task_failure_with_retry(self, mock_extractor_class, mock_retry):
        """Test relationship extraction failure triggers retry."""
        mock_extractor = AsyncMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_relationships.side_effect = Exception("Extraction failed")
        mock_retry.side_effect = Exception("Retry triggered")

        with pytest.raises(Exception, match="Retry triggered"):
            await extract_relationships_task(
                job_id="test-job-123",
                entities=[{"name": "Entity1"}],
                config={"tenant_id": "tenant-1"},
            )

        mock_retry.assert_called_once()
