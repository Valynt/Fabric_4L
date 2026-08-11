"""Tests for API idempotency replay semantics for /targets/{id}/execute.

Tests verify that /targets/{id}/execute supports idempotency keys and replay semantics:
- Duplicate requests with same idempotency key return same job_id without creating duplicate
- Different idempotency keys create different job_ids
- Missing idempotency key creates job normally
- Idempotency key expiration (if implemented)
- Replay after job completion returns completed job status
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from value_fabric.shared.error_handling.exceptions import ConflictError


class _FakeRedis:
    """Minimal in-memory Redis stand-in for idempotency tests."""

    def __init__(self):
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in self._store:
            return None
        self._store[key] = value
        return True

    def setex(self, key: str, ex: int, value: str) -> bool:
        self._store[key] = value
        return True

    def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0


@pytest.fixture(autouse=True)
def _mock_process_scraping_job_and_redis(monkeypatch):
    """Mock Celery task and Redis so execute tests don't need a broker."""
    import layer1_ingestion.api.main as _app_mod
    import layer1_ingestion.api.target_handlers as _target_handlers_mod
    import layer1_ingestion.shared.database as _db_mod
    monkeypatch.setattr(_app_mod, "process_scraping_job", type("_MockTask", (), {"delay": lambda *a, **k: None, "apply_async": lambda *a, **k: None})())
    monkeypatch.setattr(_target_handlers_mod, "process_scraping_job", type("_MockTask", (), {"delay": lambda *a, **k: None, "apply_async": lambda *a, **k: None})())
    monkeypatch.setattr(_db_mod, "redis_client", _FakeRedis())


class TestIdempotencyKeyBehavior:
    """Test idempotency key behavior for /targets/{id}/execute."""

    def test_duplicate_requests_with_same_idempotency_key_return_same_job(
        self, client, db, org_id, make_target
    ):
        """Endpoint is idempotent: same idempotency key returns the same job."""
        target = make_target(org_id, status="ACTIVE")
        idempotency_key = str(uuid4())

        # First request
        resp1 = client.post(
            f"/api/v1/ingestion/targets/{target.id}/execute",
            json={"idempotency_key": idempotency_key},
        )
        assert resp1.status_code == 202
        job_id_1 = resp1.json().get("job_id")

        # Second request with same idempotency_key returns existing job
        resp2 = client.post(
            f"/api/v1/ingestion/targets/{target.id}/execute",
            json={"idempotency_key": idempotency_key},
        )
        assert resp2.status_code == 202
        job_id_2 = resp2.json().get("job_id")

        assert job_id_1 == job_id_2

        # Only one job was created
        from layer1_ingestion.shared.models import ScrapingJob
        job_count = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.target_id == target.id)
            .count()
        )
        assert job_count == 1

    def test_different_idempotency_keys_create_different_job_ids(
        self, client, db, org_id, make_target
    ):
        """Different idempotency_keys should create different job_ids."""
        target = make_target(org_id, status="ACTIVE")
        idempotency_key_1 = str(uuid4())
        idempotency_key_2 = str(uuid4())

        # First request
        resp1 = client.post(
            f"/api/v1/ingestion/targets/{target.id}/execute",
            json={"idempotency_key": idempotency_key_1},
        )
        assert resp1.status_code == 202
        job_id_1 = resp1.json().get("job_id")

        # Second request with different idempotency_key
        resp2 = client.post(
            f"/api/v1/ingestion/targets/{target.id}/execute",
            json={"idempotency_key": idempotency_key_2},
        )
        assert resp2.status_code == 202
        job_id_2 = resp2.json().get("job_id")

        # Should return different job_ids
        assert job_id_1 != job_id_2

        # Should create two jobs
        from layer1_ingestion.shared.models import ScrapingJob
        job_count = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.target_id == target.id)
            .count()
        )
        assert job_count == 2

    def test_missing_idempotency_key_creates_job_normally(
        self, client, db, org_id, make_target
    ):
        """Request without idempotency_key should create job normally."""
        target = make_target(org_id, status="ACTIVE")

        # Request without idempotency_key
        resp = client.post(
            f"/api/v1/ingestion/targets/{target.id}/execute",
            json={},  # No idempotency_key
        )
        assert resp.status_code == 202
        job_id = resp.json().get("job_id")

        # Should create job
        from layer1_ingestion.shared.models import ScrapingJob
        job = db.query(ScrapingJob).get(UUID(job_id))
        assert job is not None
        assert job.target_id == target.id

    def test_empty_idempotency_key_is_not_persisted(
        self, client, db, org_id, make_target
    ):
        """An empty key has the same semantics as an omitted key."""
        target = make_target(org_id, status="ACTIVE")

        resp = client.post(
            f"/api/v1/ingestion/targets/{target.id}/execute",
            json={"idempotency_key": ""},
        )

        assert resp.status_code == 202
        from layer1_ingestion.shared.models import ScrapingJob

        job = db.query(ScrapingJob).get(UUID(resp.json()["job_id"]))
        assert job.idempotency_key is None

    @pytest.mark.asyncio
    async def test_cross_target_collision_returns_conflict_and_cleans_placeholder(
        self,
        monkeypatch,
        org_id,
    ):
        """A tenant-wide DB collision must not return another target's job."""
        from layer1_ingestion.api import target_handlers
        from layer1_ingestion.api.schemas.target_schemas import ExecuteTargetRequest

        requested_target_id = uuid4()
        existing_target_id = uuid4()
        target = SimpleNamespace(id=requested_target_id, status="ACTIVE")
        existing_job = SimpleNamespace(
            id=uuid4(),
            target_id=existing_target_id,
            status="QUEUED",
            started_at=None,
        )
        target_query = MagicMock()
        target_query.filter.return_value.first.return_value = target
        existing_query = MagicMock()
        existing_query.filter.return_value.first.return_value = existing_job
        db = MagicMock()
        db.query.side_effect = [target_query, existing_query]
        db.commit.side_effect = IntegrityError("duplicate", {}, Exception())

        monkeypatch.setattr(
            target_handlers,
            "_check_idempotency_key",
            AsyncMock(return_value=(None, "placeholder:owned")),
        )
        monkeypatch.setattr(target_handlers, "_build_job_configuration", lambda *_: {})
        monkeypatch.setattr(
            target_handlers,
            "create_scraping_job",
            lambda **_: SimpleNamespace(id=uuid4()),
        )
        delete_key = MagicMock()
        monkeypatch.setattr(target_handlers, "_delete_idempotency_key", delete_key)

        with pytest.raises(ConflictError):
            await target_handlers.execute_target(
                requested_target_id,
                ExecuteTargetRequest(idempotency_key="reused-key"),
                org_id,
                uuid4(),
                db,
            )

        delete_key.assert_called_once_with(
            org_id, requested_target_id, "reused-key"
        )

    def test_idempotency_key_scope_per_tenant(
        self, client, db, org_id, other_org_id, make_target
    ):
        """Idempotency keys should be scoped per tenant."""
        # DONE(VF-L1-IDEMPOTENCY-DEBT-001): per-tenant idempotency key scoping implemented in
        # layer1_ingestion/api/target_handlers.py:545 (key includes org_id).
        pytest.skip("DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency key scoping implemented; unit test still pending")


class TestIdempotencyKeyExpiration:
    """Test idempotency key expiration behavior."""

    def test_idempotency_key_expiration_after_ttl(
        self, client, db, org_id, make_target
    ):
        """Idempotency keys should expire after TTL (e.g., 24 hours)."""
        # DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency keys stored with 24h TTL via
        # layer1_ingestion/api/target_handlers.py:696 (setex 86400).
        pytest.skip("DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency key TTL implemented; unit test still pending")

    def test_expired_idempotency_key_allows_new_job(
        self, client, db, org_id, make_target
    ):
        """After expiration, same idempotency_key should allow new job creation."""
        # DONE(VF-L1-IDEMPOTENCY-DEBT-001): expired Redis keys allow new job creation;
        # TTL enforced in layer1_ingestion/api/target_handlers.py:696.
        pytest.skip("DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency key TTL implemented; unit test still pending")


class TestReplayAfterJobCompletion:
    """Test replay behavior after job completion."""

    def test_replay_after_job_completion_returns_completed_status(
        self, client, db, org_id, make_target
    ):
        """Replay after job completion should return completed job status."""
        # DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotent replay returns existing job status
        # from layer1_ingestion/api/target_handlers.py:606-619.
        pytest.skip("DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotent replay implemented; unit test still pending")

    def test_replay_after_job_failure_returns_failed_status(
        self, client, db, org_id, make_target
    ):
        """Replay after job failure should return failed job status."""
        # DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotent replay returns existing job status
        # from layer1_ingestion/api/target_handlers.py:606-619.
        pytest.skip("DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotent replay implemented; unit test still pending")


class TestIdempotencyKeyValidation:
    """Test idempotency key validation."""

    def test_invalid_idempotency_key_format_rejected(
        self, client, db, org_id, make_target
    ):
        """Invalid idempotency key format should be rejected."""
        # TODO(VF-L1-IDEMPOTENCY-DEBT-001): implement idempotency key format validation
        # (no regex/pattern validator currently exists in ExecuteTargetRequest).
        pytest.skip("TODO(VF-L1-IDEMPOTENCY-DEBT-001): idempotency key format validation not yet implemented")

    def test_too_long_idempotency_key_rejected(
        self, client, db, org_id, make_target
    ):
        """Too long idempotency key should be rejected."""
        # DONE(VF-L1-IDEMPOTENCY-DEBT-001): max_length=255 enforced by
        # layer1_ingestion/api/schemas/target_schemas.py:328.
        pytest.skip("DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency key length validation implemented; unit test still pending")


class TestIdempotencyKeyMetrics:
    """Test idempotency key metrics."""

    def test_idempotency_key_hit_emits_metric(self, client, db, org_id, make_target):
        """Idempotency key hit should emit metric."""
        # DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency hit/miss metrics implemented in
        # layer1_ingestion/metrics/prometheus_metrics.py:196 and incremented in
        # layer1_ingestion/api/target_handlers.py:571-572,612.
        pytest.skip("DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency key metrics implemented; unit test still pending")

    def test_idempotency_key_miss_emits_metric(self, client, db, org_id, make_target):
        """Idempotency key miss should emit metric."""
        # DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency hit/miss metrics implemented in
        # layer1_ingestion/metrics/prometheus_metrics.py:196 and incremented in
        # layer1_ingestion/api/target_handlers.py:571-572,612.
        pytest.skip("DONE(VF-L1-IDEMPOTENCY-DEBT-001): idempotency key metrics implemented; unit test still pending")
