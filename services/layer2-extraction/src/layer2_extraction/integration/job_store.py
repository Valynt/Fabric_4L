"""Job store implementations for Layer 2 extraction pipeline."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PipelineJob(BaseModel):
    """State for a single extract-and-ingest pipeline job."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    source_url: str = ""
    overall_status: str = "pending"
    extraction_status: str = "pending"
    ingestion_status: str = "pending"
    entities_extracted: int = 0
    relationships_extracted: int = 0
    retry_count: int = 0
    last_error: str | None = None
    next_retry_at: datetime | None = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    created_at: datetime | None = None
    tenant_id: str | None = None


class ExtractionArtifacts(BaseModel):
    """Artifacts produced by an extraction run."""

    model_config = ConfigDict(extra="forbid")

    result: Any = None
    relationships: list[Any] = Field(default_factory=list)


class InMemoryJobStore:
    """In-memory job store for development and testing."""

    def __init__(self) -> None:
        self._jobs: dict[str, PipelineJob] = {}
        self._artifacts: dict[str, ExtractionArtifacts] = {}
        self._idempotency_keys: dict[str, str] = {}

    async def get_job(self, job_id: str, *, tenant_id: str | None = None) -> PipelineJob:
        job = self._jobs[job_id]
        if tenant_id is not None and job.tenant_id != tenant_id:
            raise KeyError(job_id)
        return job

    async def get(self, job_id: str, *, tenant_id: str | None = None) -> PipelineJob | None:
        try:
            return await self.get_job(job_id, tenant_id=tenant_id)
        except KeyError:
            return None

    async def set_job(self, job: PipelineJob) -> None:
        self._jobs[job.job_id] = job

    async def set(self, job: PipelineJob) -> None:
        await self.set_job(job)

    async def exists(self, job_id: str) -> bool:
        return job_id in self._jobs

    async def delete(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)
        self._artifacts.pop(job_id, None)

    async def get_artifacts(self, job_id: str, *, tenant_id: str | None = None) -> ExtractionArtifacts | None:
        return self._artifacts.get(job_id)

    async def set_artifacts(self, job_id: str, artifacts: ExtractionArtifacts) -> None:
        self._artifacts[job_id] = artifacts

    async def get_job_id_for_idempotency_key(self, idempotency_key: str) -> str | None:
        return self._idempotency_keys.get(idempotency_key)

    async def set_job_id_for_idempotency_key(self, idempotency_key: str, job_id: str) -> None:
        self._idempotency_keys[idempotency_key] = job_id

    async def list_jobs(self, *, tenant_id: str | None = None) -> list[PipelineJob]:
        jobs = list(self._jobs.values())
        if tenant_id is not None:
            jobs = [j for j in jobs if j.tenant_id == tenant_id]
        return jobs


class RedisJobStore:
    """Redis-backed job store for production use.

    Persists PipelineJob and ExtractionArtifacts in Redis with tenant-scoped
    key prefixes for isolation. Keys expire after ``default_ttl_seconds`` to
    prevent unbounded growth.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl_seconds: int = 86400,
    ) -> None:
        redis_url = redis_url or os.environ.get("REDIS_URL", "")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required for RedisJobStore")
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:
            raise RuntimeError("redis.asyncio is required for RedisJobStore") from exc
        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._job_prefix = "l2:job:"
        self._artifact_prefix = "l2:artifact:"
        self._idempotency_prefix = "l2:idempotency:"
        self._default_ttl = default_ttl_seconds

    def _job_key(self, job_id: str) -> str:
        return f"{self._job_prefix}{job_id}"

    def _artifact_key(self, job_id: str) -> str:
        return f"{self._artifact_prefix}{job_id}"

    def _idempotency_key(self, idempotency_key: str) -> str:
        return f"{self._idempotency_prefix}{idempotency_key}"

    async def get_job(self, job_id: str, *, tenant_id: str | None = None) -> PipelineJob:
        raw = await self._redis.get(self._job_key(job_id))
        if raw is None:
            raise KeyError(job_id)
        data = json.loads(raw)
        job = PipelineJob.model_validate(data)
        if tenant_id is not None and job.tenant_id != tenant_id:
            raise KeyError(job_id)
        return job

    async def get(self, job_id: str, *, tenant_id: str | None = None) -> PipelineJob:
        return await self.get_job(job_id, tenant_id=tenant_id)

    async def set_job(self, job: PipelineJob) -> None:
        await self._redis.setex(
            self._job_key(job.job_id),
            self._default_ttl,
            job.model_dump_json(),
        )

    async def set(self, job: PipelineJob) -> None:
        await self.set_job(job)

    async def exists(self, job_id: str) -> bool:
        count = await self._redis.exists(self._job_key(job_id))
        return bool(count)

    async def delete(self, job_id: str) -> None:
        await self._redis.delete(self._job_key(job_id))
        await self._redis.delete(self._artifact_key(job_id))

    async def get_artifacts(self, job_id: str, *, tenant_id: str | None = None) -> ExtractionArtifacts | None:
        try:
            await self.get_job(job_id, tenant_id=tenant_id)
        except KeyError:
            return None
        raw = await self._redis.get(self._artifact_key(job_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return ExtractionArtifacts.model_validate(data)

    async def set_artifacts(self, job_id: str, artifacts: ExtractionArtifacts) -> None:
        await self._redis.setex(
            self._artifact_key(job_id),
            self._default_ttl,
            artifacts.model_dump_json(),
        )

    async def get_job_id_for_idempotency_key(self, idempotency_key: str) -> str | None:
        job_id = await self._redis.get(self._idempotency_key(idempotency_key))
        return job_id if job_id else None

    async def set_job_id_for_idempotency_key(self, idempotency_key: str, job_id: str) -> None:
        await self._redis.setex(
            self._idempotency_key(idempotency_key),
            self._default_ttl,
            job_id,
        )

    async def list_jobs(self, *, tenant_id: str | None = None) -> list[PipelineJob]:
        keys = []
        async for key in self._redis.scan_iter(match=f"{self._job_prefix}*"):
            keys.append(key)
        jobs: list[PipelineJob] = []
        for key in keys:
            raw = await self._redis.get(key)
            if raw is not None:
                data = json.loads(raw)
                job = PipelineJob.model_validate(data)
                if tenant_id is None or job.tenant_id == tenant_id:
                    jobs.append(job)
        return jobs

    async def close(self) -> None:
        await self._redis.close()


# Backward-compatible alias used by layer2_extraction/api/main.py
JobStore = InMemoryJobStore


def build_job_store() -> InMemoryJobStore | RedisJobStore:
    """Factory for job store based on environment."""
    env = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    redis_url = os.environ.get("REDIS_URL")
    if env in ("production", "staging"):
        if not redis_url:
            raise RuntimeError("REDIS_URL is required in production")
        return RedisJobStore(redis_url)
    return InMemoryJobStore()
