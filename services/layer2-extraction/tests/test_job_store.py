"""Unit tests for layer2_extraction.integration.job_store."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from layer2_extraction.integration.job_store import (
    ExtractionArtifacts,
    InMemoryJobStore,
    PipelineJob,
    build_job_store,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job(job_id: str = "j1", tenant_id: str | None = "t1") -> PipelineJob:
    return PipelineJob(job_id=job_id, tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# PipelineJob model
# ---------------------------------------------------------------------------

class TestPipelineJobModel:
    def test_source_url_defaults_to_empty_string(self):
        job = PipelineJob(job_id="j1")
        assert job.source_url == ""

    def test_created_at_is_optional(self):
        job = PipelineJob(job_id="j1", created_at=None)
        assert job.created_at is None

    def test_created_at_accepts_datetime(self):
        now = datetime.now()
        job = PipelineJob(job_id="j1", created_at=now)
        assert job.created_at == now

    def test_default_statuses_are_pending(self):
        job = PipelineJob(job_id="j1")
        assert job.overall_status == "pending"
        assert job.extraction_status == "pending"
        assert job.ingestion_status == "pending"


# ---------------------------------------------------------------------------
# InMemoryJobStore
# ---------------------------------------------------------------------------

class TestInMemoryJobStoreSetGet:
    @pytest.mark.asyncio
    async def test_set_job_and_get_job_round_trip(self):
        store = InMemoryJobStore()
        job = _job("j1", "t1")
        await store.set_job(job)
        retrieved = await store.get_job("j1")
        assert retrieved.job_id == "j1"

    @pytest.mark.asyncio
    async def test_get_job_raises_key_error_for_unknown(self):
        store = InMemoryJobStore()
        with pytest.raises(KeyError):
            await store.get_job("nonexistent")

    @pytest.mark.asyncio
    async def test_get_job_raises_key_error_for_cross_tenant(self):
        store = InMemoryJobStore()
        job = _job("j1", "tenant-a")
        await store.set_job(job)
        with pytest.raises(KeyError):
            await store.get_job("j1", tenant_id="tenant-b")

    @pytest.mark.asyncio
    async def test_get_job_with_correct_tenant_succeeds(self):
        store = InMemoryJobStore()
        job = _job("j1", "tenant-a")
        await store.set_job(job)
        retrieved = await store.get_job("j1", tenant_id="tenant-a")
        assert retrieved.job_id == "j1"

    @pytest.mark.asyncio
    async def test_set_job_overwrites_existing(self):
        store = InMemoryJobStore()
        job = _job("j1")
        await store.set_job(job)
        updated = PipelineJob(job_id="j1", tenant_id="t1", extraction_status="completed")
        await store.set_job(updated)
        retrieved = await store.get_job("j1")
        assert retrieved.extraction_status == "completed"


class TestInMemoryJobStoreListJobs:
    @pytest.mark.asyncio
    async def test_list_jobs_returns_all_without_filter(self):
        store = InMemoryJobStore()
        await store.set_job(_job("j1", "t1"))
        await store.set_job(_job("j2", "t2"))
        jobs = await store.list_jobs()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_list_jobs_filters_by_tenant_id(self):
        store = InMemoryJobStore()
        await store.set_job(_job("j1", "t1"))
        await store.set_job(_job("j2", "t2"))
        await store.set_job(_job("j3", "t1"))
        jobs = await store.list_jobs(tenant_id="t1")
        assert len(jobs) == 2
        assert all(j.tenant_id == "t1" for j in jobs)

    @pytest.mark.asyncio
    async def test_list_jobs_empty_store_returns_empty_list(self):
        store = InMemoryJobStore()
        jobs = await store.list_jobs()
        assert jobs == []


class TestInMemoryJobStoreArtifacts:
    @pytest.mark.asyncio
    async def test_set_and_get_artifacts_round_trip(self):
        store = InMemoryJobStore()
        artifacts = ExtractionArtifacts(result={"key": "value"}, relationships=[])
        await store.set_artifacts("j1", artifacts)
        retrieved = await store.get_artifacts("j1")
        assert retrieved is not None
        assert retrieved.result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_artifacts_returns_none_for_unknown(self):
        store = InMemoryJobStore()
        result = await store.get_artifacts("nonexistent")
        assert result is None


class TestInMemoryJobStoreAliases:
    @pytest.mark.asyncio
    async def test_set_alias_stores_job(self):
        store = InMemoryJobStore()
        job = _job("j1")
        await store.set(job)
        retrieved = await store.get_job("j1")
        assert retrieved.job_id == "j1"

    @pytest.mark.asyncio
    async def test_get_alias_returns_job(self):
        store = InMemoryJobStore()
        job = _job("j1")
        await store.set_job(job)
        retrieved = await store.get("j1")
        assert retrieved is not None
        assert retrieved.job_id == "j1"

    @pytest.mark.asyncio
    async def test_get_alias_returns_none_for_unknown(self):
        store = InMemoryJobStore()
        result = await store.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_job(self):
        store = InMemoryJobStore()
        job = _job("j1")
        await store.set_job(job)
        await store.delete("j1")
        result = await store.get("j1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_does_not_raise(self):
        store = InMemoryJobStore()
        await store.delete("nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# build_job_store
# ---------------------------------------------------------------------------

class TestBuildJobStore:
    def test_returns_in_memory_store_in_development(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("REDIS_URL", raising=False)
        store = build_job_store()
        assert isinstance(store, InMemoryJobStore)

    def test_returns_in_memory_store_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        store = build_job_store()
        assert isinstance(store, InMemoryJobStore)

    def test_raises_in_production_without_redis_url(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("REDIS_URL", raising=False)
        with pytest.raises(RuntimeError, match="REDIS_URL"):
            build_job_store()

    def test_raises_in_staging_without_redis_url(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.delenv("REDIS_URL", raising=False)
        with pytest.raises(RuntimeError, match="REDIS_URL"):
            build_job_store()


# ---------------------------------------------------------------------------
# RedisJobStore (mocked)
# ---------------------------------------------------------------------------

class TestRedisJobStoreMocked:
    @pytest.mark.asyncio
    async def test_set_job_calls_redis_setex(self):
        from layer2_extraction.integration.job_store import RedisJobStore

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisJobStore(redis_url="redis://localhost:6379")
            job = _job("j1", "t1")
            await store.set_job(job)
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert "l2:job:j1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_job_raises_key_error_when_not_found(self):
        from layer2_extraction.integration.job_store import RedisJobStore

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisJobStore(redis_url="redis://localhost:6379")
            with pytest.raises(KeyError):
                await store.get_job("nonexistent")

    @pytest.mark.asyncio
    async def test_get_job_returns_job_when_found(self):
        from layer2_extraction.integration.job_store import RedisJobStore

        job = _job("j1", "t1")
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=job.model_dump_json())

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisJobStore(redis_url="redis://localhost:6379")
            retrieved = await store.get_job("j1")
            assert retrieved.job_id == "j1"

    @pytest.mark.asyncio
    async def test_delete_calls_redis_delete(self):
        from layer2_extraction.integration.job_store import RedisJobStore

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisJobStore(redis_url="redis://localhost:6379")
            await store.delete("j1")
            assert mock_redis.delete.call_count == 2  # job key + artifact key
