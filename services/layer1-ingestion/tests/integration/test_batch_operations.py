"""Tests for batch operations API endpoints."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from layer1_ingestion.api.main import (
    BatchOperationRequest,
    BatchOperationType,
)
from layer1_ingestion.shared.models import (
    JobStatus,
    ScrapingJob,
    ScrapingTarget,
    create_scraping_job,
)

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


@pytest.fixture(autouse=True)
def _mock_process_scraping_job(monkeypatch):
    """Mock Celery task delay so batch tests don't fail when broker is unavailable."""
    import layer1_ingestion.api._batch_and_stats as _app_mod
    monkeypatch.setattr(_app_mod, "process_scraping_job", type("_MockTask", (), {"delay": lambda *a, **k: None})())


@pytest.fixture
def org_id():
    """Sample organization ID for testing."""
    return uuid4()


@pytest.fixture
def user_id():
    """Sample user ID for testing."""
    return uuid4()


@pytest.fixture
def active_target(db: Session, org_id: UUID, user_id: UUID):
    """Create an active scraping target for testing."""
    from layer1_ingestion.shared.models import SourceCategory, TargetType, create_scraping_target
    target = create_scraping_target(
        tenant_id=org_id,
        name="Test Target",
        url="https://example.com",
        target_type=TargetType.SINGLE_PAGE,
        created_by=user_id,
        source_category=SourceCategory.GENERAL,
        extraction_config={"method": "llm"},
    )
    db.add(target)
    db.flush()
    db.refresh(target)
    return target


@pytest.fixture
def failed_job(db: Session, org_id: UUID, active_target: ScrapingTarget):
    """Create a failed scraping job for testing."""
    from layer1_ingestion.shared.models import create_scraping_job
    
    job = create_scraping_job(
        tenant_id=org_id,
        target_id=active_target.id,
        created_by=uuid4(),
        configuration=active_target.extraction_config,
        priority=5,
    )
    job.status = JobStatus.FAILED.value
    db.add(job)
    db.flush()
    db.refresh(job)
    return job


def test_batch_execute_success(
    client, db: Session, org_id: UUID, user_id: UUID, active_target: ScrapingTarget
):
    """Test successful batch execute operation."""
    from layer1_ingestion.shared.models import ScrapingJob
    
    request = BatchOperationRequest(
        operation=BatchOperationType.EXECUTE,
        target_ids=[active_target.id],
    )
    
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["operation"] == "execute"
    assert data["requested"] == 1
    assert data["succeeded"] == 1
    assert data["failed"] == 0
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "succeeded"
    assert data["results"][0]["id"] == str(active_target.id)
    assert data["results"][0]["job_id"] is not None
    
    # Verify job was created
    job_id = UUID(data["results"][0]["job_id"])
    job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
    assert job is not None
    assert job.tenant_id == org_id
    assert job.target_id == active_target.id


def test_batch_cancel_success(
    client, db: Session, org_id: UUID, user_id: UUID, active_target: ScrapingTarget
):
    """Test successful batch cancel operation."""
    
    # Create a running job
    job = create_scraping_job(
        tenant_id=org_id,
        target_id=active_target.id,
        created_by=user_id,
        configuration=active_target.extraction_config,
        priority=5,
    )
    job.status = JobStatus.QUEUED.value
    db.add(job)
    db.flush()
    db.refresh(job)
    
    request = BatchOperationRequest(
        operation=BatchOperationType.CANCEL,
        job_ids=[job.id],
    )
    
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["operation"] == "cancel"
    assert data["requested"] == 1
    assert data["succeeded"] == 1
    assert data["failed"] == 0
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "succeeded"
    assert data["results"][0]["id"] == str(job.id)
    
    # Verify job was cancelled
    db.refresh(job)
    assert job.status == JobStatus.CANCELLED.value


def test_batch_retry_success(
    client, db: Session, org_id: UUID, user_id: UUID, failed_job: ScrapingJob
):
    """Test successful batch retry operation."""
    request = BatchOperationRequest(
        operation=BatchOperationType.RETRY,
        job_ids=[failed_job.id],
    )
    
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["operation"] == "retry"
    assert data["requested"] == 1
    assert data["succeeded"] == 1
    assert data["failed"] == 0
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "succeeded"
    assert data["results"][0]["id"] == str(failed_job.id)
    assert data["results"][0]["job_id"] is not None
    assert data["results"][0]["job_id"] != str(failed_job.id)  # New job created


def test_batch_mixed_success_failure(
    client, db: Session, org_id: UUID, user_id: UUID, active_target: ScrapingTarget
):
    """Test batch operation with mixed success and failure."""
    
    # Create a failed job
    failed_job = create_scraping_job(
        tenant_id=org_id,
        target_id=active_target.id,
        created_by=user_id,
        configuration=active_target.extraction_config,
        priority=5,
    )
    failed_job.status = JobStatus.FAILED.value
    db.add(failed_job)
    db.flush()
    
    # Use invalid job ID
    invalid_job_id = uuid4()
    
    request = BatchOperationRequest(
        operation=BatchOperationType.RETRY,
        job_ids=[failed_job.id, invalid_job_id],
    )
    
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["requested"] == 2
    assert data["succeeded"] == 1
    assert data["failed"] == 1
    assert len(data["results"]) == 2
    
    # Check results
    succeeded_result = next(r for r in data["results"] if r["status"] == "succeeded")
    failed_result = next(r for r in data["results"] if r["status"] == "skipped")
    assert succeeded_result["id"] == str(failed_job.id)
    assert failed_result["id"] == str(invalid_job_id)
    assert "not found" in failed_result["error"]


def test_batch_wrong_identifier_type(
    client, org_id: UUID, user_id: UUID
):
    """Test batch operation with wrong identifier type for operation."""
    # Execute operation requires target_ids, not job_ids
    request = BatchOperationRequest(
        operation=BatchOperationType.EXECUTE,
        job_ids=[uuid4()],  # Wrong for execute
    )
    
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 422
    assert "target_ids required for execute operation" in response.json()["error"]["message"]
    
    # Cancel operation requires job_ids, not target_ids
    request = BatchOperationRequest(
        operation=BatchOperationType.CANCEL,
        target_ids=[uuid4()],  # Wrong for cancel
    )
    
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 422
    assert "job_ids required for cancel/retry operations" in response.json()["error"]["message"]


def test_batch_cross_tenant_access_denied(
    client, db: Session, org_id: UUID, user_id: UUID
):
    """Test that cross-tenant access is denied."""
    from layer1_ingestion.shared.models import SourceCategory, TargetType, create_scraping_target
    other_org_id = uuid4()
    
    # Create a target belonging to a different tenant
    other_target = create_scraping_target(
        tenant_id=other_org_id,
        name="Other Tenant Target",
        url="https://example.com",
        target_type=TargetType.SINGLE_PAGE,
        created_by=user_id,
        source_category=SourceCategory.GENERAL,
        extraction_config={"method": "llm"},
    )
    other_target.status = "ACTIVE"
    db.add(other_target)
    db.flush()
    db.refresh(other_target)
    
    request = BatchOperationRequest(
        operation=BatchOperationType.EXECUTE,
        target_ids=[other_target.id],  # Target belongs to other_org_id
    )
    
    # Client is authenticated as org_id, trying to access other_org_id's target
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["requested"] == 1
    assert data["succeeded"] == 0
    assert data["failed"] == 1
    assert data["results"][0]["status"] == "skipped"
    assert "not found or access denied" in data["results"][0]["error"]


def test_batch_empty_rejected(
    client, org_id: UUID, user_id: UUID
):
    """Test that empty batch is rejected."""
    request = BatchOperationRequest(
        operation=BatchOperationType.EXECUTE,
        target_ids=[],
    )
    
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 422
    assert "target_ids required for execute operation" in response.json()["error"]["message"]


def test_batch_excessive_size_rejected(
    client, org_id: UUID, user_id: UUID
):
    """Test that batch size exceeding maximum is rejected."""
    # Create batch with 101 target IDs (exceeds MAX_BATCH_SIZE of 100)
    request = BatchOperationRequest(
        operation=BatchOperationType.EXECUTE,
        target_ids=[uuid4() for _ in range(101)],
    )
    
    response = client.post(
        "/api/v1/ingestion/jobs/batch",
        json=request.model_dump(mode='json'),
        headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
    )
    
    assert response.status_code == 422
    assert "exceeds maximum of 100" in response.json()["error"]["message"]
