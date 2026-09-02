"""Comprehensive unit tests for tasks.py refactored methods.

This test file provides direct coverage for the Celery task pipeline,
addressing the untested hotspot issue identified in health analysis.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from layer1_ingestion.crawler.smart_router import RouteType
from layer1_ingestion.shared.tasks import (
    MAX_DISPATCH_ATTEMPTS,
    _domain_class,
    celery_app,
)


@pytest.fixture(autouse=True)
def _kill_switch_definitively_not_suspended():
    """Default tenant state for these tests: kill switch answered, not suspended.

    Pipeline stages fail closed with TenantKillSwitchUnavailable when the
    switch state is UNKNOWN (no Redis in unit tests). Tests that exercise
    stage behavior patch the seam to a definitive answer, matching
    tests/unit/test_celery_tasks.py; the suspended/unknown paths are governed
    by dedicated kill-switch tests there and in
    tests/tenancy/test_worker_kill_switch_and_idempotency.py.
    """
    with patch(
        "layer1_ingestion.shared.tasks._check_tenant_kill_switch_sync",
        return_value=False,
    ):
        yield


class TestDomainClass:
    """Tests for _domain_class helper function."""

    def test_domain_class_government(self):
        """Test classification of .gov domains."""
        assert _domain_class("https://example.gov") == "regulated"
        assert _domain_class("https://example.edu") == "regulated"

    def test_domain_class_internal(self):
        """Test classification of internal domains."""
        assert _domain_class("https://example.internal") == "internal"
        assert _domain_class("https://example.local") == "internal"

    def test_domain_class_public(self):
        """Test classification of public domains."""
        assert _domain_class("https://example.com") == "public"
        assert _domain_class("https://example.org") == "public"

    def test_domain_class_unknown(self):
        """Test classification of invalid URLs."""
        assert _domain_class("") == "unknown"
        assert _domain_class("not-a-url") == "unknown"


class TestConstants:
    """Tests for module constants."""

    def test_max_dispatch_attempts(self):
        """Test MAX_DISPATCH_ATTEMPTS constant."""
        assert MAX_DISPATCH_ATTEMPTS == 5
        assert isinstance(MAX_DISPATCH_ATTEMPTS, int)


class TestCeleryApp:
    """Tests for Celery application configuration."""

    def test_celery_app_exists(self):
        """Test that Celery app is properly initialized."""
        assert celery_app is not None
        assert celery_app.main == "layer1_ingestion"

    def test_celery_app_broker_configured(self):
        """Test that Celery broker is configured."""
        assert celery_app.conf.broker_url is not None
        assert celery_app.conf.result_backend is not None

    def test_celery_app_task_serializer(self):
        """Test that Celery uses JSON serialization."""
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"

    def test_celery_app_timezone_utc(self):
        """Test that Celery uses UTC timezone."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_app_task_time_limit(self):
        """Test that task time limit is configured."""
        assert celery_app.conf.task_time_limit == 3600  # 1 hour

    def test_celery_app_dead_letter_queue(self):
        """Test that dead letter queue is configured."""
        assert "layer1_dlq" in celery_app.conf.task_queues
        assert celery_app.conf.task_reject_on_worker_lost is True
        assert celery_app.conf.task_acks_late is True

    def test_celery_app_backpressure_config(self):
        """Test backpressure configuration."""
        assert celery_app.conf.worker_max_tasks_per_child == 100
        assert celery_app.conf.worker_max_memory_per_child == 500000

    def test_celery_app_graceful_shutdown(self):
        """Test graceful shutdown configuration."""
        assert celery_app.conf.worker_shutdown_timeout == 30
        assert celery_app.conf.worker_cancel_long_running_tasks_on_shutdown is True


class TestRunAsync:
    """Tests for _run_async helper function."""

    def test_run_async_without_event_loop(self):
        """Test _run_async when no event loop is running."""
        from layer1_ingestion.shared.tasks import _run_async

        async def simple_coro():
            return "result"

        result = _run_async(simple_coro())
        assert result == "result"

    def test_run_async_with_event_loop(self):
        """Test _run_async when event loop is already running."""
        import asyncio

        from layer1_ingestion.shared.tasks import _run_async

        async def simple_coro():
            return "result"

        async def test_with_loop():
            coro = _run_async(simple_coro())
            # When loop is running, it should return the coroutine
            assert asyncio.iscoroutine(coro)
            result = await coro
            return result

        result = asyncio.run(test_with_loop())
        assert result == "result"


class TestComplianceCheckStage:
    """Tests for compliance_check_stage and helper methods."""

    @pytest.fixture
    def mock_job(self):
        """Create a mock ScrapingJob."""
        job = MagicMock()
        job.id = uuid4()
        job.tenant_id = uuid4()
        job.target_id = uuid4()
        job.status = "PENDING"
        job.created_at = datetime.now(UTC)
        job.configuration = {
            "url": "https://example.com",
            "compliance": {
                "respect_robots_txt": True,
                "strict_robots_compliance": False,
                "user_agent_string": "TestBot",
            },
        }
        return job

    @pytest.fixture
    def mock_target(self):
        """Create a mock ScrapingTarget."""
        target = MagicMock()
        target.id = uuid4()
        target.compliance = {"domain_allowlist": ["example.com"]}
        target.extraction_config = {}
        return target

    @pytest.mark.asyncio
    async def test_compliance_check_stage_success(self, mock_job, mock_target):
        """Test successful compliance check stage."""
        from layer1_ingestion.shared.tasks import _compliance_check_stage_async

        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"

        with patch("layer1_ingestion.shared.tasks.get_db_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session.query.return_value.get.return_value = mock_job
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_session_ctx.return_value.__enter__.return_value = mock_session

            with patch("layer1_ingestion.shared.tasks.validate_url_safety") as mock_validate:
                mock_validate.return_value = MagicMock(normalized_url="https://example.com")

                with patch("layer1_ingestion.shared.tasks.RobotsChecker") as mock_checker_class:
                    mock_checker = AsyncMock()
                    mock_checker.check_url.return_value = (True, "Allowed", {"crawl_delay": None})
                    mock_checker_class.return_value = mock_checker

                    with patch("layer1_ingestion.shared.tasks._update_stage"):
                        with patch("layer1_ingestion.shared.tasks.get_metrics", return_value=None):
                            result = await _compliance_check_stage_async(mock_self, mock_job.id, str(mock_job.tenant_id))

                            assert result["success"] is True
                            assert result["job_id"] == str(mock_job.id)

    @pytest.mark.asyncio
    async def test_compliance_check_stage_url_blocked(self, mock_job):
        """Test compliance check stage when URL is blocked."""
        from layer1_ingestion.compliance.url_safety import URLSafetyError
        from layer1_ingestion.shared.tasks import _compliance_check_stage_async

        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"

        with patch("layer1_ingestion.shared.tasks.get_db_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session.query.return_value.get.return_value = mock_job
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_session_ctx.return_value.__enter__.return_value = mock_session

            with patch("layer1_ingestion.shared.tasks.validate_url_safety") as mock_validate:
                mock_validate.side_effect = URLSafetyError("BLOCKED", "MALICIOUS_DOMAIN")

                with patch("layer1_ingestion.shared.tasks._fail_job"):
                    with patch("layer1_ingestion.shared.tasks.get_metrics", return_value=None):
                        result = await _compliance_check_stage_async(mock_self, mock_job.id, str(mock_job.tenant_id))

                        assert result["success"] is False
                        assert "blocked" in result["error"].lower()


class TestBrowserCrawlStage:
    """Tests for browser_crawl_stage and helper methods."""

    @pytest.fixture
    def mock_job(self):
        """Create a mock ScrapingJob."""
        job = MagicMock()
        job.id = uuid4()
        job.tenant_id = uuid4()
        job.target_id = uuid4()
        job.status = "VALIDATING"
        job.created_at = datetime.now(UTC)
        job.configuration = {
            "url": "https://example.com",
            "browser_config": {"headless": True},
        }
        job.resources_browser_sessions_used = 0
        return job

    @pytest.fixture
    def mock_target(self):
        """Create a mock ScrapingTarget."""
        target = MagicMock()
        target.id = uuid4()
        target.extraction_config = {"crawl_path": "fast"}
        return target

    @pytest.mark.asyncio
    async def test_browser_crawl_stage_fast_path(self, mock_job, mock_target):
        """Test browser crawl stage with fast path routing."""
        from layer1_ingestion.shared.tasks import _browser_crawl_stage_async

        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"

        with patch("layer1_ingestion.shared.tasks.crawl.get_db_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session.query.return_value.get.side_effect = [mock_job, mock_target]
            mock_session_ctx.return_value.__enter__.return_value = mock_session

            with patch("layer1_ingestion.shared.tasks.crawl.SmartRouter") as mock_router_class:
                mock_router = MagicMock()
                mock_decision = MagicMock()
                mock_decision.route = RouteType.FAST
                mock_decision.reason = "static_content"
                mock_router.decide.return_value = mock_decision
                mock_router_class.return_value = mock_router

                with patch("layer1_ingestion.shared.tasks.crawl._execute_fast_path") as mock_execute_fast:
                    mock_fast_result = MagicMock()
                    mock_fast_result.status_code = 200
                    mock_fast_result.html = "<html>test</html>"
                    mock_fast_result.text_content = "test content"
                    mock_fast_result.url = "https://example.com"
                    mock_fast_result.title = "Test Page"
                    mock_fast_result.fetch_time_ms = 100
                    mock_fast_result.is_spa_detected = False
                    mock_fast_result.headers = {}
                    mock_execute_fast.return_value = mock_fast_result

                    with patch("layer1_ingestion.shared.tasks.crawl.QualityGate") as mock_gate_class:
                        mock_gate = MagicMock()
                        mock_gate_class.return_value = mock_gate

                        with patch("layer1_ingestion.shared.tasks.crawl.CrawlDecisionRepository") as mock_repo_class:
                            mock_repo = AsyncMock()
                            mock_repo_class.return_value = mock_repo

                            with patch("layer1_ingestion.shared.tasks.crawl._update_stage"):
                                with patch("layer1_ingestion.shared.tasks.crawl.get_metrics", return_value=None):
                                    result = await _browser_crawl_stage_async(
                                        mock_self, {"job_id": str(mock_job.id)}, str(mock_job.tenant_id)
                                    )

                                    assert result["success"] is True
                                    assert result["job_id"] == str(mock_job.id)


class TestProcessScrapingJob:
    """Tests for process_scraping_job main orchestrator."""

    @pytest.fixture
    def mock_job(self):
        """Create a mock ScrapingJob."""
        job = MagicMock()
        job.id = uuid4()
        job.tenant_id = uuid4()
        job.status = "PENDING"
        job.configuration = {"job_type": "generic_scrape"}
        job.job_type = "generic_scrape"
        return job

    def test_process_scraping_job_success(self, mock_job):
        """Test successful job processing."""
        from layer1_ingestion.shared.tasks import process_scraping_job

        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"

        with patch("layer1_ingestion.shared.tasks._check_tenant_kill_switch_sync", return_value=False):
            with patch("layer1_ingestion.shared.tasks.get_db_session") as mock_session_ctx:
                mock_session = MagicMock()
                mock_session.query.return_value.get.return_value = mock_job
                mock_session_ctx.return_value.__enter__.return_value = mock_session

                with patch("layer1_ingestion.shared.tasks.get_skill", return_value=None):
                    with patch("layer1_ingestion.shared.tasks.chain") as mock_chain:
                        mock_result = MagicMock()
                        mock_result.id = "chain-task-id"
                        mock_chain.return_value.apply_async.return_value = mock_result

                        result = process_scraping_job.run(str(mock_job.id), str(mock_job.tenant_id))

                        assert result["success"] is True
                        assert result["job_id"] == str(mock_job.id)

    def test_process_scraping_job_tenant_suspended(self, mock_job):
        """Test job processing when tenant is suspended."""
        from layer1_ingestion.shared.tasks import process_scraping_job

        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"

        with patch("layer1_ingestion.shared.tasks._check_tenant_kill_switch_sync", return_value=True):
            with patch("layer1_ingestion.shared.tasks._fail_job"):
                result = process_scraping_job.run(str(mock_job.id), str(mock_job.tenant_id))

                assert result["success"] is False
                assert "suspended" in result["error"].lower()


class TestPipelineStageIdempotency:
    """Tests for pipeline stage idempotency."""

    @pytest.fixture
    def mock_job(self):
        """Create a mock ScrapingJob."""
        job = MagicMock()
        job.id = uuid4()
        job.tenant_id = uuid4()
        job.status = "VALIDATING"
        job.created_at = datetime.now(UTC)
        job.configuration = {"url": "https://example.com"}
        return job

    @pytest.fixture
    def mock_completed_stage(self):
        """Create a mock completed stage detail."""
        stage = MagicMock()
        stage.status = "COMPLETED"
        return stage

    @pytest.mark.asyncio
    async def test_compliance_check_idempotent_retry(self, mock_job, mock_completed_stage):
        """Test that compliance check skips if already completed."""
        from layer1_ingestion.shared.tasks import _compliance_check_stage_async

        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"

        with patch("layer1_ingestion.shared.tasks.get_db_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session.query.return_value.get.return_value = mock_job
            mock_session.query.return_value.filter.return_value.first.return_value = mock_completed_stage
            mock_session_ctx.return_value.__enter__.return_value = mock_session

            result = await _compliance_check_stage_async(mock_self, mock_job.id, str(mock_job.tenant_id))

            assert result["success"] is True
            # Should return early without re-executing


class TestMetricsRecording:
    """Tests for metrics recording in pipeline stages."""

    @pytest.fixture
    def mock_metrics(self):
        """Create a mock metrics object."""
        metrics = MagicMock()
        metrics.observe_queue_latency = MagicMock()
        metrics.observe_job_stage_duration = MagicMock()
        metrics.increment_retry_event = MagicMock()
        metrics.increment_url_blocked = MagicMock()
        metrics.increment_crawl_path = MagicMock()
        return metrics

    @pytest.mark.asyncio
    async def test_compliance_check_records_metrics(self, mock_metrics):
        """Test that compliance check records metrics."""
        from layer1_ingestion.shared.tasks import _compliance_check_stage_async

        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job.tenant_id = uuid4()
        mock_job.target_id = uuid4()
        mock_job.status = "PENDING"
        mock_job.configuration = {"url": "https://example.com"}
        mock_job.created_at = datetime.now(UTC)

        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"

        with patch("layer1_ingestion.shared.tasks.get_db_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session.query.return_value.get.return_value = mock_job
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_session_ctx.return_value.__enter__.return_value = mock_session

            with patch("layer1_ingestion.shared.tasks.validate_url_safety") as mock_validate:
                mock_validate.return_value = MagicMock(normalized_url="https://example.com")

                with patch("layer1_ingestion.shared.tasks.RobotsChecker") as mock_checker_class:
                    mock_checker = AsyncMock()
                    mock_checker.check_url.return_value = (True, "Allowed", {"crawl_delay": None})
                    mock_checker_class.return_value = mock_checker

                    with patch("layer1_ingestion.shared.tasks._update_stage"):
                        with patch("layer1_ingestion.shared.tasks.get_metrics", return_value=mock_metrics):
                            await _compliance_check_stage_async(mock_self, mock_job.id, str(mock_job.tenant_id))

                            # Verify metrics were called
                            assert mock_metrics.observe_queue_latency.called
                            assert mock_metrics.observe_job_stage_duration.called
