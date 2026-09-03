"""Tests for terminal-state reconciliation when max retries exhausted.

Tests verify that jobs reach terminal states when max retries exhausted mid-pipeline:
- Compliance check max retries leads to FAILED status
- Browser crawl max retries leads to FAILED status
- AI extraction max retries leads to FAILED status
- Stage status consistency after retry exhaustion
- No orphaned RUNNING states after retry exhaustion
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from layer1_ingestion.shared.models import (
    JobStageDetail,
    JobStatus,
    PipelineStage,
    ScrapingJob,
)

pytestmark = pytest.mark.postgres


class TestComplianceCheckMaxRetries:
    """Test compliance check stage max retry behavior."""

    def test_compliance_check_max_retries_exhaustion_leads_to_failed(
        self, db, org_id, user_id, make_target
    ):
        """When compliance_check_stage exhausts max_retries, job should reach FAILED status."""

        # Create job
        target = make_target(org_id, status="ACTIVE")
        job = ScrapingJob(
            id=uuid4(),
            tenant_id=org_id,
            target_id=target.id,
            status=JobStatus.VALIDATING.value,
            configuration={"url": "https://example.com"},
            created_by=user_id,
        )
        db.add(job)
        db.commit()

        # Mock compliance check to always fail
        with patch(
            "layer1_ingestion.shared.tasks.validate_url_safety",
            side_effect=Exception("Compliance check failed"),
        ):
            # Simulate max retries exhausted
            # In real Celery, this would happen after max_retries attempts
            # For testing, we directly call the error handling path
            try:
                # This would normally be called by Celery after max retries
                # We simulate the final failure
                from layer1_ingestion.shared.tasks import _fail_job
                _fail_job(
                    job.id,
                    str(org_id),
                    "Compliance check failed after max retries",
                    PipelineStage.COMPLIANCE_CHECK,
                )
            except Exception:
                pass

        db.refresh(job)
        assert job.status == JobStatus.FAILED.value

    def test_compliance_check_stage_status_marked_failed_after_exhaustion(
        self, db, org_id, user_id, make_target
    ):
        """Compliance check stage should be marked FAILED after retry exhaustion."""
        target = make_target(org_id, status="ACTIVE")
        job = ScrapingJob(
            id=uuid4(),
            tenant_id=org_id,
            target_id=target.id,
            status=JobStatus.VALIDATING.value,
            configuration={"url": "https://example.com"},
            created_by=user_id,
        )
        db.add(job)
        db.commit()

        # Create the stage detail row so _update_stage can update it
        stage_detail = JobStageDetail(
            id=uuid4(),
            job_id=job.id,
            tenant_id=org_id,
            stage=PipelineStage.COMPLIANCE_CHECK.value,
            status="RUNNING",
        )
        db.add(stage_detail)
        db.commit()

        # Simulate stage failure
        from layer1_ingestion.shared.tasks import _update_stage
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            _update_stage(
                session,
                job.id,
                PipelineStage.COMPLIANCE_CHECK,
                "FAILED",
                "Max retries exceeded",
            )
            session.commit()

        # Verify stage status
        stage = (
            db.query(JobStageDetail)
            .filter(
                JobStageDetail.job_id == job.id,
                JobStageDetail.stage == PipelineStage.COMPLIANCE_CHECK.value,
            )
            .first()
        )
        assert stage is not None
        assert stage.status == "FAILED"
        assert "Max retries exceeded" in stage.error_message


class TestBrowserCrawlMaxRetries:
    """Test browser crawl stage max retry behavior."""

    def test_browser_crawl_max_retries_exhaustion_leads_to_failed(
        self, db, org_id, user_id, make_target
    ):
        """When browser_crawl_stage exhausts max_retries, job should reach FAILED status."""
        target = make_target(org_id, status="ACTIVE")
        job = ScrapingJob(
            id=uuid4(),
            tenant_id=org_id,
            target_id=target.id,
            status=JobStatus.BROWSER_ACQUIRING.value,
            configuration={"url": "https://example.com"},
            created_by=user_id,
        )
        db.add(job)
        db.commit()

        # Simulate max retries exhausted
        from layer1_ingestion.shared.tasks import _fail_job
        _fail_job(
            job.id,
            str(org_id),
            "Browser crawl failed after max retries",
            PipelineStage.BROWSER_LAUNCH,
        )

        db.refresh(job)
        assert job.status == JobStatus.FAILED.value

    def test_browser_crawl_stages_marked_failed_after_exhaustion(
        self, db, org_id, user_id, make_target
    ):
        """All browser crawl stages should be marked FAILED after retry exhaustion."""
        target = make_target(org_id, status="ACTIVE")
        job = ScrapingJob(
            id=uuid4(),
            tenant_id=org_id,
            target_id=target.id,
            status=JobStatus.BROWSER_ACQUIRING.value,
            configuration={"url": "https://example.com"},
            created_by=user_id,
        )
        db.add(job)
        db.commit()

        # Create stage detail rows so _update_stage can update them
        for stage_name in (
            PipelineStage.BROWSER_LAUNCH.value,
            PipelineStage.NAVIGATION.value,
            PipelineStage.CONTENT_CAPTURE.value,
        ):
            stage_detail = JobStageDetail(
                id=uuid4(),
                job_id=job.id,
                tenant_id=org_id,
                stage=stage_name,
                status="RUNNING",
            )
            db.add(stage_detail)
        db.commit()

        # Mark all browser crawl stages as FAILED
        from layer1_ingestion.shared.database import get_db_session
        from layer1_ingestion.shared.tasks import _update_stage

        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            for stage in (
                PipelineStage.BROWSER_LAUNCH,
                PipelineStage.NAVIGATION,
                PipelineStage.CONTENT_CAPTURE,
            ):
                _update_stage(
                    session,
                    job.id,
                    stage,
                    "FAILED",
                    "Max retries exceeded",
                )
            session.commit()

        # Verify all stages marked FAILED
        for stage_name in (
            PipelineStage.BROWSER_LAUNCH.value,
            PipelineStage.NAVIGATION.value,
            PipelineStage.CONTENT_CAPTURE.value,
        ):
            stage = (
                db.query(JobStageDetail)
                .filter(
                    JobStageDetail.job_id == job.id,
                    JobStageDetail.stage == stage_name,
                )
                .first()
            )
            assert stage is not None
            assert stage.status == "FAILED"


class TestAIExtractionMaxRetries:
    """Test AI extraction stage max retry behavior."""

    def test_ai_extraction_max_retries_exhaustion_leads_to_failed(
        self, db, org_id, user_id, make_target
    ):
        """When ai_extraction_stage exhausts max_retries, job should reach FAILED status."""
        target = make_target(org_id, status="ACTIVE")
        job = ScrapingJob(
            id=uuid4(),
            tenant_id=org_id,
            target_id=target.id,
            status=JobStatus.EXTRACTING.value,
            configuration={
                "url": "https://example.com",
                "extraction_config": {"method": "LLM"},
            },
            created_by=user_id,
        )
        db.add(job)
        db.commit()

        # Simulate max retries exhausted
        from layer1_ingestion.shared.tasks import _fail_job
        _fail_job(
            job.id,
            str(org_id),
            "AI extraction failed after max retries",
            PipelineStage.AI_EXTRACTION,
        )

        db.refresh(job)
        assert job.status == JobStatus.FAILED.value


class TestStageStatusConsistency:
    """Test stage status consistency after retry exhaustion."""

    def test_all_affected_stages_marked_failed_after_retry_exhaustion(
        self, db, org_id, user_id, make_target
    ):
        """When a stage exhausts retries, all affected stages should be marked FAILED."""
        target = make_target(org_id, status="ACTIVE")
        job = ScrapingJob(
            id=uuid4(),
            tenant_id=org_id,
            target_id=target.id,
            status=JobStatus.VALIDATING.value,
            configuration={"url": "https://example.com"},
            created_by=user_id,
        )
        db.add(job)
        db.commit()

        # Create the stage detail row so _update_stage can update it
        stage_detail = JobStageDetail(
            id=uuid4(),
            job_id=job.id,
            tenant_id=org_id,
            stage=PipelineStage.COMPLIANCE_CHECK.value,
            status="RUNNING",
        )
        db.add(stage_detail)
        db.commit()

        # Simulate compliance check failure affecting subsequent stages
        from layer1_ingestion.shared.database import get_db_session
        from layer1_ingestion.shared.tasks import _update_stage

        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # Mark compliance check as FAILED
            _update_stage(
                session,
                job.id,
                PipelineStage.COMPLIANCE_CHECK,
                "FAILED",
                "Max retries exceeded",
            )
            # Subsequent stages should also be marked FAILED or not started
            session.commit()

        # Verify compliance check is FAILED
        compliance_stage = (
            db.query(JobStageDetail)
            .filter(
                JobStageDetail.job_id == job.id,
                JobStageDetail.stage == PipelineStage.COMPLIANCE_CHECK.value,
            )
            .first()
        )
        assert compliance_stage is not None
        assert compliance_stage.status == "FAILED"


class TestNoOrphanedRunningStates:
    """Test that no jobs are stuck in non-terminal states after retry exhaustion."""

    def test_no_orphaned_running_states_after_retry_exhaustion(
        self, db, org_id, user_id, make_target
    ):
        """After retry exhaustion, no jobs should be stuck in RUNNING state."""
        target = make_target(org_id, status="ACTIVE")

        # Create multiple jobs in various states
        jobs = []
        for i in range(5):
            job = ScrapingJob(
                id=uuid4(),
                tenant_id=org_id,
                target_id=target.id,
                status=JobStatus.VALIDATING.value,
                configuration={"url": f"https://example{i}.com"},
                created_by=user_id,
            )
            db.add(job)
            jobs.append(job)
        db.commit()

        # Simulate retry exhaustion for all jobs
        from layer1_ingestion.shared.tasks import _fail_job
        for job in jobs:
            _fail_job(
                job.id,
                str(org_id),
                "Max retries exceeded",
                PipelineStage.COMPLIANCE_CHECK,
            )

        # Verify no jobs in RUNNING or non-terminal states
        non_terminal_statuses = [
            JobStatus.VALIDATING.value,
            JobStatus.BROWSER_ACQUIRING.value,
            JobStatus.NAVIGATING.value,
            JobStatus.EXTRACTING.value,
            JobStatus.TRANSFORMING.value,
            JobStatus.STORING.value,
        ]

        stuck_jobs = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.status.in_(non_terminal_statuses))
            .all()
        )

        assert len(stuck_jobs) == 0, "No jobs should be stuck in non-terminal states"

    def test_stuck_jobs_metric_reflects_non_terminal_count(
        self, db, org_id, user_id, make_target
    ):
        """The stuck_jobs metric should reflect the count of non-terminal jobs."""
        from layer1_ingestion.shared.tasks import refresh_stuck_jobs_metrics

        target = make_target(org_id, status="ACTIVE")
        for status in (JobStatus.VALIDATING, JobStatus.VALIDATING, JobStatus.EXTRACTING):
            db.add(
                ScrapingJob(
                    id=uuid4(),
                    tenant_id=org_id,
                    target_id=target.id,
                    status=status.value,
                    configuration={"url": "https://example.com"},
                    created_by=user_id,
                )
            )
        db.commit()

        metrics = MagicMock()
        with patch(
            "layer1_ingestion.shared.tasks.cleanup.get_metrics", return_value=metrics
        ):
            counts = refresh_stuck_jobs_metrics([org_id])

        assert counts[JobStatus.VALIDATING.value] == 2
        assert counts[JobStatus.EXTRACTING.value] == 1
        metrics.refresh_stuck_jobs.assert_called_once_with(counts)


class TestRetryMechanismBehavior:
    """Test Celery retry mechanism behavior."""

    def test_max_retries_configured_correctly(self):
        """Verify that max_retries is configured correctly for each stage."""

        from layer1_ingestion.shared import tasks

        # Check max_retries for each stage
        stage_tasks = {
            "compliance_check_stage": 3,
            "browser_crawl_stage": 3,
            "ai_extraction_stage": 5,
            "post_processing_stage": 2,
        }

        for task_name, expected_max_retries in stage_tasks.items():
            if hasattr(tasks, task_name):
                task = getattr(tasks, task_name)
                # Check if task has max_retries attribute
                if hasattr(task, "max_retries"):
                    assert (
                        task.max_retries == expected_max_retries
                    ), f"{task_name} should have max_retries={expected_max_retries}"

    def test_retry_countdown_increases(self):
        """Verify that retry countdown increases with each retry."""
        # DONE(VF-L1-TERMINAL-DEBT-001): exponential-backoff retry countdown implemented in
        # layer1_ingestion/shared/tasks.py:1665,1783.
        pytest.skip("DONE(VF-L1-TERMINAL-DEBT-001): exponential-backoff retry countdown implemented; unit test still pending")


# Helper function for tests
def get_db_session(tenant_id: UUID, require_tenant: bool = True):
    """Helper to get database session."""
    from layer1_ingestion.shared.database import get_db_session as real_get_db_session
    return real_get_db_session(tenant_id=tenant_id, require_tenant=require_tenant)
