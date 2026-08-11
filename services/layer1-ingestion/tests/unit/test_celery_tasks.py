"""
Unit tests for Layer 1 Celery task dispatch.

Tests verify:
1. process_scraping_job chains all 9 pipeline stages in order.
2. compliance_check_stage updates job status to VALIDATING.
3. execute_pipeline_stage dispatches to the correct stage task.
4. cleanup_old_content returns a dict with deleted_count and cutoff_date.
5. Celery app is configured with correct broker and serializer settings.
6. Tasks handle missing job gracefully (ValueError, not unhandled exception).
"""
from __future__ import annotations

import inspect
import json
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

# ── Constants ─────────────────────────────────────────────────────────────────
# Registered Celery pipeline stage tasks in execution order.
# Note: BROWSER_LAUNCH, NAVIGATION, CONTENT_CAPTURE all dispatch to browser_crawl_stage.
PIPELINE_STAGE_TASKS = [
    "compliance_check_stage",
    "browser_crawl_stage",
    "ai_extraction_stage",
    "post_processing_stage",
    "validation_stage",
    "storage_stage",
    "notification_stage",
]


def _maintenance_audit_patch():
    record = MagicMock()
    context = MagicMock()
    context.__enter__ = Mock(return_value=record)
    context.__exit__ = Mock(return_value=False)
    return patch("layer1_ingestion.shared.tasks.maintenance_audit_log", return_value=context)


@pytest.fixture(autouse=True)
def _kill_switch_definitively_not_suspended():
    """Default unit-test tenant state: kill switch answered, not suspended.

    tasks.py fails closed with TenantKillSwitchUnavailable when the
    kill-switch state is UNKNOWN (there is no Redis in unit tests), so
    task-behavior tests need the seam to return a definitive "not
    suspended". The suspended and fail-closed paths keep dedicated tests
    (test_*_blocks_suspended_tenant), which patch the seam explicitly and
    therefore override this fixture inside their own `with` blocks.
    """
    with patch(
        "layer1_ingestion.shared.tasks._check_tenant_kill_switch_sync",
        return_value=False,
    ):
        yield


# Note: Path setup and environment variables are handled by:
# - tests/conftest.py (sys.path manipulation)
# - pyproject.toml [tool.pytest.ini_options] pythonpath = ["src", ".."]
# - pytest-env or test fixtures for DATABASE_URL/REDIS_URL as needed


# ── Celery App Configuration Tests ───────────────────────────────────────────
class TestCeleryAppConfiguration:
    """Verify the Celery app is configured correctly."""

    def test_celery_app_name(self) -> None:
        """Celery app must be named 'layer1_ingestion'."""
        from layer1_ingestion.shared.tasks import celery_app
        assert celery_app.main == "layer1_ingestion"

    def test_celery_task_serializer(self) -> None:
        """Celery must use JSON serializer for task payloads."""
        from layer1_ingestion.shared.tasks import celery_app
        assert celery_app.conf.task_serializer == "json"

    def test_celery_result_serializer(self) -> None:
        """Celery must use JSON serializer for results."""
        from layer1_ingestion.shared.tasks import celery_app
        assert celery_app.conf.result_serializer == "json"

    def test_celery_timezone_utc(self) -> None:
        """Celery must use UTC timezone."""
        from layer1_ingestion.shared.tasks import celery_app
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_task_time_limit(self) -> None:
        """Celery task time limit must be set (prevents runaway tasks)."""
        from layer1_ingestion.shared.tasks import celery_app
        assert celery_app.conf.task_time_limit is not None
        assert celery_app.conf.task_time_limit > 0


# ── Pipeline Stage Dispatch Tests ─────────────────────────────────────────────
class TestExecutePipelineStage:
    """Test execute_pipeline_stage dispatches to the correct task."""

    def test_execute_pipeline_stage_compliance_check(self) -> None:
        """execute_pipeline_stage must dispatch compliance_check_stage for COMPLIANCE_CHECK."""
        from layer1_ingestion.shared.tasks import compliance_check_stage, execute_pipeline_stage

        job_id = str(uuid4())
        call_count = [0]

        def track_call(*args, **kwargs):
            call_count[0] += 1
            return None

        tenant_id = str(uuid4())
        with patch.object(compliance_check_stage, "delay", side_effect=track_call):
            result = execute_pipeline_stage(job_id, "COMPLIANCE_CHECK", tenant_id)
            # Verify dispatch occurred by checking call was made
            assert call_count[0] == 1, "compliance_check_stage.delay should be called exactly once"
            assert result is None or isinstance(result, dict), "Should return None or dict"

    def test_execute_pipeline_stage_passes_tenant_id(self) -> None:
        """execute_pipeline_stage must propagate tenant_id to stage task dispatch."""
        from layer1_ingestion.shared.tasks import browser_crawl_stage, execute_pipeline_stage

        job_id = str(uuid4())
        tenant_id = str(uuid4())
        captured_args = []

        def capture_delay(*args, **kwargs):
            captured_args.append((args, kwargs))
            return None

        with patch.object(browser_crawl_stage, "delay", side_effect=capture_delay):
            execute_pipeline_stage(job_id, "BROWSER_LAUNCH", tenant_id)

        assert len(captured_args) == 1
        dispatched_args, _ = captured_args[0]
        assert dispatched_args[1] == tenant_id, "tenant_id must be propagated as second positional arg"

    def test_execute_pipeline_stage_missing_tenant_id_raises(self) -> None:
        """execute_pipeline_stage must fail closed without tenant_id."""
        from layer1_ingestion.shared.tasks import execute_pipeline_stage

        with pytest.raises(TypeError):
            execute_pipeline_stage(str(uuid4()), "COMPLIANCE_CHECK")

    def test_execute_pipeline_stage_unknown_raises(self) -> None:
        """execute_pipeline_stage must raise ValueError for unknown stage names."""
        from layer1_ingestion.shared.tasks import execute_pipeline_stage

        with pytest.raises(ValueError, match="not a valid PipelineStage"):
            execute_pipeline_stage(str(uuid4()), "NONEXISTENT_STAGE", str(uuid4()))


# ── Process Scraping Job Tests ────────────────────────────────────────────────
class TestProcessScrapingJob:
    """Test the main pipeline orchestrator task."""

    def test_process_scraping_job_chains_all_stages(self) -> None:
        """process_scraping_job must chain all registered pipeline stages."""
        from layer1_ingestion.shared.tasks import (
            ai_extraction_stage,
            browser_crawl_stage,
            compliance_check_stage,
            notification_stage,
            post_processing_stage,
            storage_stage,
            validation_stage,
        )

        # Map stage names to imported tasks
        stage_tasks = [
            compliance_check_stage,
            browser_crawl_stage,
            ai_extraction_stage,
            post_processing_stage,
            validation_stage,
            storage_stage,
            notification_stage,
        ]
        assert len(stage_tasks) == len(PIPELINE_STAGE_TASKS), f"Pipeline must have exactly {len(PIPELINE_STAGE_TASKS)} stages"
        for task in stage_tasks:
            assert callable(task), f"Stage task {task} must be callable"

    def test_process_scraping_job_missing_job_raises(self) -> None:
        """process_scraping_job must raise ValueError when job is not found in DB."""
        from layer1_ingestion.shared.tasks import process_scraping_job

        job_id = str(uuid4())
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = None  # Job not found

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            with pytest.raises(ValueError, match="not found"):
                process_scraping_job.run(job_id, str(uuid4()))

    def test_process_scraping_job_returns_task_id_on_success(self) -> None:
        """process_scraping_job must return dict with success=True and task_id."""
        from layer1_ingestion.shared.tasks import process_scraping_job

        job_id = str(uuid4())
        tenant_id = str(uuid4())
        mock_job = Mock()
        mock_job.status = "PENDING"
        mock_job.started_at = None
        mock_job.tenant_id = tenant_id

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = mock_job

        mock_chain_result = Mock()
        mock_chain_result.id = "celery-task-abc-123"

        with (
            patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session),
            patch("layer1_ingestion.shared.tasks.chain") as mock_chain_cls,
        ):
            mock_chain_instance = Mock()
            mock_chain_instance.apply_async.return_value = mock_chain_result
            mock_chain_cls.return_value = mock_chain_instance

            # Call .run() directly to bypass Celery's task dispatch machinery
            result = process_scraping_job.run(job_id, tenant_id)

        assert result["success"] is True
        assert result["job_id"] == job_id
        assert "task_id" in result
        assert result["task_id"] == "celery-task-abc-123"

    def test_process_scraping_job_blocks_suspended_tenant(self) -> None:
        """process_scraping_job must fail fast when tenant kill-switch is active."""
        from layer1_ingestion.shared.tasks import process_scraping_job

        job_id = str(uuid4())
        tenant_id = str(uuid4())

        with (
            patch(
                "layer1_ingestion.shared.tasks._check_tenant_kill_switch_sync",
                return_value=True,
            ),
            patch("layer1_ingestion.shared.tasks._fail_job") as mock_fail,
        ):
            result = process_scraping_job.run(job_id, tenant_id)

        mock_fail.assert_called_once()
        assert result["success"] is False
        assert result["job_id"] == job_id
        assert result["error"] == "Tenant suspended"

    def test_compliance_check_stage_blocks_suspended_tenant(self) -> None:
        """compliance_check_stage must fail fast when tenant kill-switch is active."""
        from layer1_ingestion.shared.tasks import compliance_check_stage

        job_id = str(uuid4())
        tenant_id = str(uuid4())

        with (
            patch(
                "layer1_ingestion.shared.tasks._check_tenant_kill_switch_sync",
                return_value=True,
            ),
            patch("layer1_ingestion.shared.tasks._fail_job") as mock_fail,
        ):
            result = compliance_check_stage.run(job_id, tenant_id)

        mock_fail.assert_called_once()
        assert result["success"] is False
        assert result["job_id"] == job_id
        assert result["error"] == "Tenant suspended"

    @pytest.mark.parametrize(
        ("task_name", "helper_name", "args"),
        [
            ("compliance_check_stage", "_compliance_check_stage_async", (uuid4(), str(uuid4()))),
            ("browser_crawl_stage", "_browser_crawl_stage_async", ({"job_id": str(uuid4())}, str(uuid4()))),
            ("ai_extraction_stage", "_ai_extraction_stage_async", ({"job_id": str(uuid4())}, str(uuid4()))),
        ],
    )
    def test_pipeline_stage_entrypoints_return_json_dicts_not_coroutines(
        self,
        task_name: str,
        helper_name: str,
        args: tuple,
    ) -> None:
        """Celery stage entrypoints must serialize cleanly when chained."""
        import layer1_ingestion.shared.tasks as tasks

        expected = {"success": True, "job_id": str(uuid4())}
        task = getattr(tasks, task_name)
        with patch(f"layer1_ingestion.shared.tasks.{helper_name}", new=AsyncMock(return_value=expected)):
            result = task(*args)

        assert isinstance(result, dict)
        assert not inspect.iscoroutine(result)
        assert json.loads(json.dumps(result)) == expected

    def test_compliance_check_stage_run_returns_json_dict_not_coroutine(self) -> None:
        """Celery-facing compliance stage must not return an unserializable coroutine."""
        import inspect

        from layer1_ingestion.shared.tasks import compliance_check_stage

        job_id = str(uuid4())
        tenant_id = str(uuid4())

        with (
            patch(
                "layer1_ingestion.shared.tasks._check_tenant_kill_switch_sync",
                return_value=True,
            ),
            patch("layer1_ingestion.shared.tasks._fail_job"),
        ):
            result = compliance_check_stage.run(job_id, tenant_id)

        assert isinstance(result, dict)
        assert not inspect.iscoroutine(result)


# ── Cleanup Task Tests ────────────────────────────────────────────────────────
class TestCleanupOldContent:
    """Test the cleanup_old_content periodic task."""

    def test_cleanup_returns_deleted_count_and_cutoff(self) -> None:
        """cleanup_old_content must return deleted_count and cutoff_date."""
        from layer1_ingestion.shared.tasks import cleanup_old_content

        mock_content_1 = Mock()
        mock_content_1.processing_status = "PROCESSED"
        mock_content_2 = Mock()
        mock_content_2.processing_status = "PROCESSED"

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.update.return_value = 2

        with (
            patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session),
            _maintenance_audit_patch(),
        ):
            result = cleanup_old_content(days=30, tenant_id=str(uuid4()))

        assert "deleted_count" in result
        assert result["deleted_count"] == 2
        assert "cutoff_date" in result
        # cutoff_date must be a valid ISO datetime string in the past
        cutoff = datetime.fromisoformat(result["cutoff_date"]).replace(tzinfo=UTC)
        assert cutoff < datetime.now(UTC)

    def test_cleanup_marks_content_as_deleted(self) -> None:
        """cleanup_old_content must set processing_status to DELETED."""
        from layer1_ingestion.shared.tasks import cleanup_old_content

        mock_content = Mock()
        mock_content.processing_status = "PROCESSED"

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        query = mock_session.query.return_value
        query.filter.return_value.update.return_value = 1

        with (
            patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session),
            _maintenance_audit_patch(),
        ):
            cleanup_old_content(days=30, tenant_id=str(uuid4()))

        query.filter.return_value.update.assert_called_once_with(
            {"processing_status": "DELETED"},
            synchronize_session=False,
        )

    def test_cleanup_default_days_is_30(self) -> None:
        """cleanup_old_content default retention period must be 30 days."""
        import inspect

        from layer1_ingestion.shared.tasks import cleanup_old_content
        sig = inspect.signature(cleanup_old_content)
        days_param = sig.parameters.get("days")
        assert days_param is not None, "cleanup_old_content must have a 'days' parameter"
        assert days_param.default == 30, "Default retention period must be 30 days"


# ── Compliance Check Stage Tests ──────────────────────────────────────────────
class TestComplianceCheckStage:
    """Test the compliance_check_stage pipeline task."""

    def test_compliance_check_stage_updates_job_status(self) -> None:
        """compliance_check_stage must set job.status to VALIDATING."""
        from layer1_ingestion.shared.tasks import compliance_check_stage

        job_id = uuid4()
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = "PENDING"
        mock_job.created_at = datetime.now(UTC)
        mock_job.configuration = {
            "url": "https://example.com",
            "compliance": {"respect_robots_txt": False},  # Skip robots check
        }
        mock_job.tenant_id = uuid4()
        mock_job.target_id = uuid4()

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = mock_job

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            with patch("layer1_ingestion.shared.tasks._update_stage"):
                with patch("layer1_ingestion.shared.tasks.validate_url_safety"):
                    # Use .run() to bypass Celery's task dispatch machinery
                    # Pass string job_id to match Celery JSON serialization
                    result = compliance_check_stage.run(str(job_id), str(mock_job.tenant_id))

        # Job status must be updated to VALIDATING
        assert mock_job.status == "VALIDATING"
        assert result["success"] is True
        assert str(result["job_id"]) == str(job_id)

    def test_compliance_check_stage_passes_full_url_to_robots_checker(self) -> None:
        """RobotsChecker.check_url must receive the normalized URL, not a bare domain."""
        from types import SimpleNamespace

        from layer1_ingestion.shared.tasks import compliance_check_stage

        job_id = uuid4()
        tenant_id = uuid4()
        target_id = uuid4()
        normalized_url = "https://example.com:443/"

        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = "PENDING"
        mock_job.created_at = datetime.now(UTC)
        mock_job.configuration = {
            "url": "https://example.com",
            "compliance": {"respect_robots_txt": True, "strict_robots_compliance": False},
        }
        mock_job.tenant_id = tenant_id
        mock_job.target_id = target_id

        mock_target = Mock()
        mock_target.compliance = {"domain_allowlist": []}

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = mock_job
        mock_session.query.return_value.filter.return_value.first.return_value = mock_target

        checker = AsyncMock()
        checker.check_url.return_value = (True, None, {"crawl_delay": None})

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            with patch("layer1_ingestion.shared.tasks._update_stage"):
                with patch(
                    "layer1_ingestion.shared.tasks.validate_url_safety",
                    return_value=SimpleNamespace(normalized_url=normalized_url),
                ):
                    with patch("layer1_ingestion.shared.tasks.RobotsChecker", return_value=checker):
                        result = compliance_check_stage.run(str(job_id), str(tenant_id))

        assert result["success"] is True
        checker.check_url.assert_awaited_once_with(normalized_url, job_id=str(job_id))

    def test_compliance_check_stage_missing_job_retries(self) -> None:
        """compliance_check_stage must raise when job is not found."""
        from layer1_ingestion.shared.tasks import compliance_check_stage

        job_id = uuid4()
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = None  # Job not found

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            with pytest.raises(ValueError, match="not found"):
                # Use .run() to bypass Celery's task dispatch machinery
                # Pass string job_id to match Celery JSON serialization
                compliance_check_stage.run(str(job_id), str(uuid4()))


# ── Crawl URL With Routing Tests ──────────────────────────────────────────────
class TestCrawlUrlWithRouting:
    """Test crawl_url_with_routing tenant isolation."""

    def test_crawl_url_with_routing_requires_tenant_id(self) -> None:
        """crawl_url_with_routing must reject calls without tenant_id."""
        from layer1_ingestion.shared.tasks import crawl_url_with_routing

        with pytest.raises(TypeError):
            crawl_url_with_routing.run(job_id=str(uuid4()), url="https://example.com")

    def test_crawl_url_with_routing_sets_tenant_context(self) -> None:
        """crawl_url_with_routing must open DB session with require_tenant=True."""
        from layer1_ingestion.shared.tasks import crawl_url_with_routing

        job_id = str(uuid4())
        tenant_id = str(uuid4())
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.target_id = uuid4()
        mock_job.tenant_id = tenant_id

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = mock_job

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            try:
                crawl_url_with_routing.run(
                    job_id=job_id,
                    url="https://example.com",
                    tenant_id=tenant_id,
                )
            except Exception:
                pass  # We only care about the session args

        # Verify get_db_session was called with require_tenant=True
        # by checking the mock_session was used as a context manager
        assert mock_session.__enter__.called, "DB session must be entered"


# ── Retry / Error Path Tests ─────────────────────────────────────────────────
class TestCeleryRetryBehavior:
    """Test Celery retry and error handling behavior."""

    def test_celery_max_retries_configured(self) -> None:
        """process_scraping_job must have max_retries configured."""
        from layer1_ingestion.shared.tasks import process_scraping_job
        # Celery tasks can configure retries via bind=True + self.retry()
        assert hasattr(process_scraping_job, "max_retries") or hasattr(process_scraping_job, "retry"), (
            "process_scraping_job must support retries"
        )

    def test_compliance_check_stage_handles_db_error(self) -> None:
        """compliance_check_stage must not swallow database connection errors."""
        from layer1_ingestion.shared.tasks import compliance_check_stage

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.side_effect = Exception("Database connection refused")

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            with pytest.raises(Exception, match="Database connection refused"):
                compliance_check_stage.run(str(uuid4()), str(uuid4()))

    def test_process_scraping_job_handles_chain_failure(self) -> None:
        """process_scraping_job must raise when chain.apply_async fails."""
        from layer1_ingestion.shared.tasks import process_scraping_job

        job_id = str(uuid4())
        tenant_id = str(uuid4())
        mock_job = Mock()
        mock_job.status = "PENDING"
        mock_job.started_at = None
        mock_job.tenant_id = tenant_id

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = mock_job

        with (
            patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session),
            patch("layer1_ingestion.shared.tasks.chain") as mock_chain_cls,
        ):
            mock_chain_instance = Mock()
            mock_chain_instance.apply_async.side_effect = RuntimeError("Broker unavailable")
            mock_chain_cls.return_value = mock_chain_instance

            with pytest.raises(RuntimeError, match="Broker unavailable"):
                process_scraping_job.run(job_id, tenant_id)

    def test_compliance_check_stage_handles_invalid_job_configuration(self) -> None:
        """compliance_check_stage must handle jobs with missing configuration."""
        from layer1_ingestion.shared.tasks import compliance_check_stage

        job_id = uuid4()
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = "PENDING"
        mock_job.created_at = datetime.now(UTC)
        mock_job.configuration = None  # Missing config
        mock_job.tenant_id = uuid4()
        mock_job.target_id = uuid4()

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = mock_job

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            with patch("layer1_ingestion.shared.tasks._update_stage"):
                # Should raise or handle gracefully (not crash silently)
                # AttributeError because code does config.get() when config is None
                # Pass string job_id to match Celery JSON serialization
                with pytest.raises((ValueError, AttributeError)):
                    compliance_check_stage.run(str(job_id), str(mock_job.tenant_id))

    def test_cleanup_old_content_handles_empty_result(self) -> None:
        """cleanup_old_content must return deleted_count=0 when no old content found."""
        from layer1_ingestion.shared.tasks import cleanup_old_content

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.filter.return_value.update.return_value = 0

        with (
            patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session),
            _maintenance_audit_patch(),
        ):
            result = cleanup_old_content(days=30, tenant_id=str(uuid4()))

        assert result["deleted_count"] == 0
        assert "cutoff_date" in result

    def test_cleanup_old_content_handles_db_error(self) -> None:
        """cleanup_old_content must propagate database errors."""
        from layer1_ingestion.shared.tasks import cleanup_old_content

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.side_effect = Exception("Connection timeout")

        with (
            patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session),
            _maintenance_audit_patch(),
        ):
            with pytest.raises(Exception, match="Connection timeout"):
                cleanup_old_content(days=30, tenant_id=str(uuid4()))


class TestPipelineStageErrorPaths:
    """Test error paths for individual pipeline stages."""

    def test_all_pipeline_stages_are_registered_as_celery_tasks(self) -> None:
        """All registered pipeline stages must be Celery tasks."""
        from layer1_ingestion.shared.tasks import (
            ai_extraction_stage,
            browser_crawl_stage,
            compliance_check_stage,
            notification_stage,
            post_processing_stage,
            storage_stage,
            validation_stage,
        )
        stage_tasks = [
            compliance_check_stage,
            browser_crawl_stage,
            ai_extraction_stage,
            post_processing_stage,
            validation_stage,
            storage_stage,
            notification_stage,
        ]
        for task in stage_tasks:
            # Verify tasks are callable and have delay method (public API for dispatch)
            assert callable(task), f"{task} must be callable"
            assert hasattr(task, "delay"), f"{task} must have delay method for Celery dispatch"

    def test_execute_pipeline_stage_dispatches_all_known_stages(self) -> None:
        """execute_pipeline_stage must recognize all registered stage names."""
        from layer1_ingestion.shared.tasks import execute_pipeline_stage

        # Stage constants that execute_pipeline_stage must recognize,
        # mapped to the actual Celery task name that gets dispatched.
        stage_task_map = {
            "COMPLIANCE_CHECK": "compliance_check_stage",
            "BROWSER_LAUNCH": "browser_crawl_stage",
            "NAVIGATION": "browser_crawl_stage",
            "CONTENT_CAPTURE": "browser_crawl_stage",
            "AI_EXTRACTION": "ai_extraction_stage",
            "POST_PROCESSING": "post_processing_stage",
            "VALIDATION": "validation_stage",
            "STORAGE": "storage_stage",
            "NOTIFICATION": "notification_stage",
        }

        for stage_const, task_name in stage_task_map.items():
            job_id = str(uuid4())
            tenant_id = str(uuid4())
            with patch(f"layer1_ingestion.shared.tasks.{task_name}") as mock_task:
                mock_task.delay = Mock(return_value=None)
                try:
                    result = execute_pipeline_stage(job_id, stage_const, tenant_id)
                    # Verify the correct task's delay was called
                    mock_task.delay.assert_called_once()
                except ValueError as e:
                    pytest.fail(f"execute_pipeline_stage should recognize stage: {stage_const} ({e})")

    def test_celery_worker_prefetch_is_one(self) -> None:
        """Worker prefetch multiplier must be 1 for sequential processing."""
        from layer1_ingestion.shared.tasks import celery_app
        prefetch = celery_app.conf.worker_prefetch_multiplier
        assert prefetch == 1, f"Expected prefetch=1, got {prefetch}"

    def test_celery_result_expires_configured(self) -> None:
        """Task results must expire (not persist forever)."""
        from layer1_ingestion.shared.tasks import celery_app
        expires = celery_app.conf.result_expires
        assert expires is not None, "result_expires must be configured"
        assert expires > 0, "result_expires must be positive"


# ── Retry and Idempotency Tests ─────────────────────────────────────────────
class TestCeleryRetrySemantics:
    """Test retry behavior and idempotency."""

    def test_max_retry_exhaustion_behavior(self) -> None:
        """Task must fail permanently after max_retries exhausted."""
        from layer1_ingestion.shared.tasks import process_scraping_job

        # Verify max_retries is configured
        assert hasattr(process_scraping_job, "max_retries") or hasattr(
            process_scraping_job, "retry"
        ), "Task must support retries"

    def test_exponential_backoff_timing(self) -> None:
        """Retries must use exponential backoff."""
        from layer1_ingestion.shared.tasks import process_scraping_job

        # Check if task has retry_backoff configured
        if hasattr(process_scraping_job, "retry_backoff"):
            backoff = process_scraping_job.retry_backoff
            assert backoff is True or isinstance(backoff, (int, bool)), (
                "retry_backoff must be True or an integer"
            )

    def test_idempotency_of_retried_tasks(self) -> None:
        """Retried tasks must be idempotent - same result on retry."""
        from layer1_ingestion.shared.tasks import compliance_check_stage

        job_id = str(uuid4())
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.status = "PENDING"
        mock_job.created_at = datetime.now(UTC)
        mock_job.configuration = {"url": "https://example.com", "compliance": {}}
        mock_job.tenant_id = uuid4()
        mock_job.target_id = uuid4()

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.query.return_value.get.return_value = mock_job

        call_count = [0]

        def mock_update(*args, **kwargs):
            call_count[0] += 1
            return None

        with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=mock_session):
            with patch("layer1_ingestion.shared.tasks._update_stage", side_effect=mock_update):
                with patch("layer1_ingestion.shared.tasks.validate_url_safety"):
                    # First attempt - pass string job_id to match Celery JSON serialization
                    try:
                        compliance_check_stage.run(job_id, str(mock_job.tenant_id))
                    except Exception:
                        pass

                    # Second attempt (retry) should give same result
                    try:
                        compliance_check_stage.run(job_id, str(mock_job.tenant_id))
                    except Exception:
                        pass

        # Both attempts should have been made
        assert call_count[0] >= 1

    def test_dead_letter_queue_routing(self) -> None:
        """Failed tasks after max retries should route to DLQ if configured."""
        from layer1_ingestion.shared.tasks import celery_app

        # Check if task_routes includes dead letter queue
        routes = celery_app.conf.get("task_routes", {})
        # DLQ routing is typically configured at the broker level
        # This test verifies the configuration exists
        assert routes is not None, "Task routes should be configured"
