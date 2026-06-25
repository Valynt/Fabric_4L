"""Runtime API tests for the async content routes.

These tests prove that the content routes (``get_raw_content``,
``get_extracted_data``, ``list_content``) resolve their DB dependency through
``request.state.governance_context`` using the async-compatible
``get_db_from_context`` dependency, not the sync
``get_db_from_context_sync`` variant.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from layer1_ingestion.shared.database import get_db_from_context
from layer1_ingestion.shared.models import (
    ExtractedData,
    RawContent,
    ScrapingJob,
    ScrapingTarget,
    SourceCategory,
    TargetType,
    create_scraping_job,
    create_scraping_target,
)


def _make_target(tenant_id: UUID, user_id: UUID, db: Session) -> ScrapingTarget:
    target = create_scraping_target(
        tenant_id=tenant_id,
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


def _make_job(tenant_id: UUID, user_id: UUID, target: ScrapingTarget, db: Session) -> ScrapingJob:
    job = create_scraping_job(
        tenant_id=tenant_id,
        target_id=target.id,
        created_by=user_id,
        configuration={"target": {"url": target.url}},
    )
    db.add(job)
    db.flush()
    db.refresh(job)
    return job


def _make_raw_content(
    tenant_id: UUID, job: ScrapingJob, db: Session, *, source_domain: str = "example.com"
) -> RawContent:
    raw = RawContent(
        tenant_id=tenant_id,
        job_id=job.id,
        target_id=job.target_id,
        source_url=f"https://{source_domain}/page",
        source_domain=source_domain,
        source_accessed_at=datetime.now(UTC),
        processing_status="PENDING",
        capture_javascript_executed=True,
        capture_wait_time_ms=0,
        meta_og_tags={},
        meta_structured_data=[],
        created_at=datetime.now(UTC),
    )
    db.add(raw)
    db.flush()
    db.refresh(raw)
    return raw


def _make_extracted_data(
    tenant_id: UUID, job: ScrapingJob, raw: RawContent, db: Session
) -> ExtractedData:
    extracted = ExtractedData(
        tenant_id=tenant_id,
        job_id=job.id,
        raw_content_id=raw.id,
        target_id=job.target_id,
        extraction_method="llm",
        extraction_confidence_score=0.95,
        data={"key": "value"},
        validation_schema_valid=True,
        validation_errors=[],
        provenance_source_url=raw.source_url,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(extracted)
    db.flush()
    db.refresh(extracted)
    return extracted


class _LifecycleSession:
    """Wrapper that delegates to a real session while recording lifecycle calls."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.closed = False
        self.rolled_back = False
        self.committed = False

    def execute(self, *args, **kwargs):
        # The real get_db_from_context executes ``SET LOCAL app.tenant_id``.
        # We cannot run that on SQLite, so intercept the tenant RLS setup
        # and otherwise delegate to the real session.
        if args and "SET LOCAL app.tenant_id" in str(args[0]):
            return MagicMock()
        return self._session.execute(*args, **kwargs)

    def query(self, *args, **kwargs):
        return self._session.query(*args, **kwargs)

    def commit(self) -> None:
        self.committed = True
        # Do not commit the underlying test session; we only need to prove the
        # dependency lifecycle invokes commit. Keeping the test transaction
        # open lets the db fixture roll back at teardown.

    def rollback(self) -> None:
        self.rolled_back = True
        # Do not roll back the underlying test session here; the db fixture
        # handles teardown. We only track that the dependency lifecycle
        # invokes rollback.

    def close(self) -> None:
        self.closed = True
        # Do not close the underlying test session here; the db fixture will
        # close it after rolling back the transaction.


@pytest.fixture()
def client_content(db: Session, org_id: UUID, user_id: UUID):
    """TestClient that routes content endpoints through the async DB dependency.

    Overrides ``get_db_from_context`` so that:
      - every request must have a populated ``request.state.governance_context``;
      - the tenant_id in the context is asserted;
      - the test DB session is yielded, proving the async path resolves end-to-end.
    """
    # Import lazily so the conftest app-level patches are applied first.
    from tests.api.conftest import _get_app, _InjectGovernanceMiddleware

    app = _get_app()

    def _get_db_from_context(request: Request) -> Generator[Session, None, None]:
        ctx = getattr(request.state, "governance_context", None)
        assert ctx is not None, "request.state.governance_context must be set"
        assert str(ctx.tenant_id) == str(org_id)
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db_from_context] = _get_db_from_context

    wrapped = _InjectGovernanceMiddleware(app, tenant_id=org_id, user_id=user_id)
    with TestClient(wrapped) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture()
def client_content_lifecycle(db: Session, org_id: UUID, user_id: UUID):
    """TestClient that records DB session lifecycle through the async dependency."""
    from tests.api.conftest import _get_app, _InjectGovernanceMiddleware

    app = _get_app()
    tracked = _LifecycleSession(db)

    def _get_db_from_context(request: Request) -> Generator[Session, None, None]:
        ctx = getattr(request.state, "governance_context", None)
        assert ctx is not None
        assert str(ctx.tenant_id) == str(org_id)
        try:
            tracked.execute(
                text("SET LOCAL app.tenant_id = :tenant_id"),
                {"tenant_id": str(ctx.tenant_id)},
            )
            yield tracked
            tracked.commit()
        except Exception:
            tracked.rollback()
            raise
        finally:
            tracked.close()

    app.dependency_overrides[get_db_from_context] = _get_db_from_context

    wrapped = _InjectGovernanceMiddleware(app, tenant_id=org_id, user_id=user_id)
    with TestClient(wrapped) as client:
        yield client, tracked

    app.dependency_overrides.clear()


class TestContentAsyncDBDependency:
    def test_get_raw_content_resolves_async_db_dependency(self, client_content, db, org_id, user_id):
        target = _make_target(org_id, user_id, db)
        job = _make_job(org_id, user_id, target, db)
        raw = _make_raw_content(org_id, job, db)

        response = client_content.get(f"/api/v1/ingestion/content/raw/{raw.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(raw.id)
        assert data["source_url"] == raw.source_url

    def test_get_extracted_data_resolves_async_db_dependency(
        self, client_content, db, org_id, user_id
    ):
        target = _make_target(org_id, user_id, db)
        job = _make_job(org_id, user_id, target, db)
        raw = _make_raw_content(org_id, job, db)
        extracted = _make_extracted_data(org_id, job, raw, db)

        response = client_content.get(f"/api/v1/ingestion/content/extracted/{extracted.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(extracted.id)
        assert data["raw_content_id"] == str(raw.id)
        assert data["extraction_method"] == "llm"

    def test_list_content_resolves_async_db_dependency(self, client_content, db, org_id, user_id):
        target = _make_target(org_id, user_id, db)
        job = _make_job(org_id, user_id, target, db)
        _make_raw_content(org_id, job, db, source_domain="example.com")
        _make_raw_content(org_id, job, db, source_domain="example.org")

        response = client_content.get("/api/v1/ingestion/content")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["limit"] == 20
        assert len(data["items"]) == 2

    def test_get_raw_content_missing_returns_404_and_rolls_back(
        self, client_content_lifecycle, db, org_id, user_id
    ):
        client, tracked = client_content_lifecycle
        unknown_id = uuid4()

        response = client.get(f"/api/v1/ingestion/content/raw/{unknown_id}")

        assert response.status_code == 404
        assert tracked.rolled_back is True
        assert tracked.closed is True
        assert tracked.committed is False

    def test_get_raw_content_success_commits_and_closes(
        self, client_content_lifecycle, db, org_id, user_id
    ):
        client, tracked = client_content_lifecycle
        target = _make_target(org_id, user_id, db)
        job = _make_job(org_id, user_id, target, db)
        raw = _make_raw_content(org_id, job, db)

        response = client.get(f"/api/v1/ingestion/content/raw/{raw.id}")

        assert response.status_code == 200
        assert tracked.committed is True
        assert tracked.closed is True
        assert tracked.rolled_back is False


def test_no_sync_db_dependency_in_content_routes():
    """Static guard: main_content_routes.py must never reference the sync variant."""
    from pathlib import Path

    content_routes = Path(__file__).resolve().parents[2] / "src" / "layer1_ingestion" / "api" / "main_content_routes.py"
    source = content_routes.read_text()
    assert "get_db_from_context_sync" not in source
    assert "SyncRequestContext" not in source
