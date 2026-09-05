"""Hostile tenant-isolation tests for queue payloads and async workers (V1-TENANCY-010).

Covers the negative cases for L1 ingestion jobs and L2 extraction batch ingest:

(a) Tenant A submits a job referencing Tenant B data -> server-side binding wins.
(b) Worker receives a job WITHOUT tenant context -> fail closed, non-retryable.
(c) Forged queue payload carrying a different tenant ID -> rejected, not retried.
(d) Retried job after an org switch (same job_id, new tenant) -> rejected.
(e) Cache entries for the same object ID under another tenant -> invisible/tamper-proof.

The suite is self-contained: heavy optional dependencies (celery, redis,
structlog, fastapi) are replaced with minimal fakes so the modules under test
are loaded directly by path, exercising the REAL tenant-handling code.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

pytestmark = [pytest.mark.security, pytest.mark.p0, pytest.mark.tenancy, pytest.mark.tenant_boundary]

REPO_ROOT = Path(__file__).resolve().parents[2]
L2_TASKS = REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/shared/tasks.py"
L2_JOB_STORE = REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/integration/job_store.py"
L2_CACHE = REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/extraction/cache.py"
L2_PIPELINE_RUNNER = REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/pipeline_runner.py"
L1_TASKS_INIT = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/shared/tasks/__init__.py"
L1_EXTRACTION_TASK = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/shared/tasks/extraction.py"
HOSTILE_FIXTURES = REPO_ROOT / "tests/tenancy/hostile_fixtures.py"

TENANT_A = "tenant-alpha-001"
TENANT_B = "tenant-beta-002"


# ---------------------------------------------------------------------------
# Fakes for unavailable third-party dependencies
# ---------------------------------------------------------------------------


class AuthorizationError(Exception):
    """Mirror of value_fabric.shared.error_handling.exceptions.AuthorizationError."""

    def __init__(self, message: str = "Request failed", error_code=None, status_code: int = 403, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class RetryRequested(Exception):
    """Sentinel raised by the fake task self.retry()."""


class _FakeTaskSelf:
    """Stand-in for a bound Celery task instance."""

    def __init__(self) -> None:
        self.request = SimpleNamespace(retries=0)
        self.retry_calls: list[dict] = []

    def retry(self, exc=None, countdown=None):
        self.retry_calls.append({"exc": exc, "countdown": countdown})
        raise RetryRequested(f"retry(exc={exc!r}, countdown={countdown})")


def _install_fake_celery() -> None:
    celery_mod = ModuleType("celery")

    class _FakeCeleryApp:
        def __init__(self, *args, **kwargs):
            self.conf = SimpleNamespace(update=lambda **_: None)

        def task(self, *dargs, **dkwargs):
            def decorator(fn):
                return fn

            if dargs and callable(dargs[0]):
                return dargs[0]
            return decorator

    celery_mod.Celery = _FakeCeleryApp  # type: ignore[attr-defined]
    sys.modules["celery"] = celery_mod


def _install_fake_value_fabric() -> None:
    """Provide the minimal value_fabric surface used by layer2 shared/tasks.py."""
    vf = ModuleType("value_fabric")
    vf.__path__ = []  # type: ignore[attr-defined]
    vf_shared = ModuleType("value_fabric.shared")
    vf_shared.__path__ = []  # type: ignore[attr-defined]
    redis_ha = ModuleType("value_fabric.shared.redis_ha")
    redis_ha.get_celery_redis_broker_config = lambda url: (url, {})  # type: ignore[attr-defined]
    eh = ModuleType("value_fabric.shared.error_handling")
    eh.__path__ = []  # type: ignore[attr-defined]
    eh_exc = ModuleType("value_fabric.shared.error_handling.exceptions")
    eh_exc.AuthorizationError = AuthorizationError  # type: ignore[attr-defined]
    vf.shared = vf_shared  # type: ignore[attr-defined]
    sys.modules.update(
        {
            "value_fabric": vf,
            "value_fabric.shared": vf_shared,
            "value_fabric.shared.redis_ha": redis_ha,
            "value_fabric.shared.error_handling": eh,
            "value_fabric.shared.error_handling.exceptions": eh_exc,
        }
    )


def _load_module(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # register BEFORE exec for __future__ annotations
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _restore_sys_modules():
    """Fake dependency modules must never leak into other tests in the process."""
    snapshot = dict(sys.modules)
    yield
    sys.modules.clear()
    sys.modules.update(snapshot)


@pytest.fixture()
def l2_tasks() -> ModuleType:
    """Load the real L2 celery tasks module with fake broker plumbing."""
    _install_fake_celery()
    _install_fake_value_fabric()
    return _load_module("l2_shared_tasks_under_test", L2_TASKS)


@pytest.fixture()
def job_store_module() -> ModuleType:
    return _load_module("l2_job_store_under_test", L2_JOB_STORE)


@pytest.fixture()
def cache_module() -> ModuleType:
    metrics_mod = ModuleType("layer2_extraction.metrics")
    metrics_mod.get_metrics = lambda: None  # type: ignore[attr-defined]
    pkg = ModuleType("layer2_extraction")
    pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["layer2_extraction"] = pkg
    sys.modules["layer2_extraction.metrics"] = metrics_mod
    return _load_module("l2_cache_under_test", L2_CACHE)


def _fake_l2_main_with_run_extraction(run_extraction_impl) -> None:
    pkg = ModuleType("layer2_extraction")
    pkg.__path__ = []  # type: ignore[attr-defined]
    api_pkg = ModuleType("layer2_extraction.api")
    api_pkg.__path__ = []  # type: ignore[attr-defined]
    main_mod = ModuleType("layer2_extraction.api.main")
    main_mod.run_extraction = run_extraction_impl  # type: ignore[attr-defined]
    sys.modules["layer2_extraction"] = pkg
    sys.modules["layer2_extraction.api"] = api_pkg
    sys.modules["layer2_extraction.api.main"] = main_mod


# ---------------------------------------------------------------------------
# (b) Worker receives a job without tenant context -> fail closed
# ---------------------------------------------------------------------------


class TestMissingTenantContextFailsClosed:
    def test_run_extraction_task_missing_tenant_rejected_without_retry(self, l2_tasks) -> None:
        fake_self = _FakeTaskSelf()
        with pytest.raises(ValueError, match="tenant_id"):
            asyncio.run(
                l2_tasks.run_extraction_task(fake_self, "job-1", "https://a.example", "content", {})
            )
        assert fake_self.retry_calls == [], "missing tenant context must fail closed, never retry"

    def test_run_extraction_task_blank_tenant_rejected_without_retry(self, l2_tasks) -> None:
        fake_self = _FakeTaskSelf()
        with pytest.raises(ValueError, match="tenant_id"):
            asyncio.run(
                l2_tasks.run_extraction_task(
                    fake_self, "job-1", "https://a.example", "content", {"tenant_id": "   "}
                )
            )
        assert fake_self.retry_calls == []

    def test_extract_entities_task_missing_tenant_rejected_without_retry(self, l2_tasks) -> None:
        """A forged/absent-context entity task must not process content tenantlessly."""
        fake_self = _FakeTaskSelf()
        with pytest.raises(ValueError, match="tenant_id"):
            asyncio.run(l2_tasks.extract_entities_task(fake_self, "job-1", "secret content", {}))
        assert fake_self.retry_calls == [], "tenantless entity extraction must fail closed"

    def test_extract_relationships_task_missing_tenant_rejected_without_retry(self, l2_tasks) -> None:
        fake_self = _FakeTaskSelf()
        with pytest.raises(ValueError, match="tenant_id"):
            asyncio.run(l2_tasks.extract_relationships_task(fake_self, "job-1", [{"id": "e1"}], {}))
        assert fake_self.retry_calls == [], "tenantless relationship extraction must fail closed"

    def test_run_extraction_missing_tenant_raises_authorization_error(self) -> None:
        """pipeline_runner must fail closed via _require_authenticated_tenant_id."""
        text = L2_PIPELINE_RUNNER.read_text(encoding="utf-8")
        assert "_require_authenticated_tenant_id(" in text
        assert '"code": "tenant_context_required"' in (
            REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/_shared.py"
        ).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# (c) Forged queue payload with a different tenant ID
# ---------------------------------------------------------------------------


class TestForgedQueuePayload:
    def test_tenant_mismatch_is_not_retried(self, l2_tasks) -> None:
        """AuthorizationError from the pipeline (tenant_context_mismatch) is
        terminal: the worker must fail closed instead of retrying a forged
        payload up to max_retries (which would amplify broker-level attacks)."""

        async def _forge_rejected(**kwargs):
            raise AuthorizationError(
                message="Request failed",
                details={"code": "tenant_context_mismatch"},
            )

        _fake_l2_main_with_run_extraction(_forge_rejected)
        fake_self = _FakeTaskSelf()
        with pytest.raises(AuthorizationError):
            asyncio.run(
                l2_tasks.run_extraction_task(
                    fake_self,
                    "job-owned-by-tenant-a",
                    "https://a.example",
                    "content",
                    {"tenant_id": TENANT_B},
                )
            )
        assert fake_self.retry_calls == [], "tenant mismatch must be non-retryable (fail closed)"

    def test_tasks_module_uses_canonical_authorization_error(self) -> None:
        text = L2_TASKS.read_text(encoding="utf-8")
        assert "from value_fabric.shared.error_handling.exceptions import AuthorizationError" in text

    def test_cross_tenant_job_overwrite_denied(self, job_store_module) -> None:
        """A forged payload naming Tenant A's job_id must not mutate the record."""
        InMemoryJobStore = job_store_module.InMemoryJobStore
        PipelineJob = job_store_module.PipelineJob

        async def run() -> None:
            store = InMemoryJobStore()
            await store.set(PipelineJob(job_id="job-a", tenant_id=TENANT_A))
            with pytest.raises(PermissionError):
                await store.set(PipelineJob(job_id="job-a", tenant_id=TENANT_B))
            # Original record is untouched
            job = await store.get("job-a", tenant_id=TENANT_A)
            assert job is not None and job.tenant_id == TENANT_A

        asyncio.run(run())

    def test_pipeline_runner_binds_and_verifies_tenant(self) -> None:
        text = L2_PIPELINE_RUNNER.read_text(encoding="utf-8")
        assert "tenant_id=tenant_id," in text, "job must be bound to the verified tenant at creation"
        assert '"code": "tenant_context_mismatch"' in text
        assert "await job_store.get(job_id, tenant_id=tenant_id)" in text


# ---------------------------------------------------------------------------
# (a) Tenant A submits a job referencing Tenant B data (L1 dispatch side)
# ---------------------------------------------------------------------------


class TestL1DispatchTenantProvenance:
    """The tenant ID on the wire must originate from the server-verified job
    record, never from client-controlled prev_results or request payloads."""

    def test_l1_stage_tasks_require_tenant_scoped_sessions(self) -> None:
        text = L1_TASKS_INIT.read_text(encoding="utf-8")
        assert text.count("require_tenant=True") >= 3, "stage tasks must use tenant-scoped sessions"
        assert "def process_scraping_job(self, job_id: str, tenant_id: str)" in text

    def test_l1_l2_dispatch_payload_tenant_comes_from_job_record(self) -> None:
        text = L1_EXTRACTION_TASK.read_text(encoding="utf-8")
        assert "def ai_extraction_stage(self, prev_result: dict, tenant_id: str)" in text
        # The tenant forwarded to L2 must be read from the DB-verified job row,
        # not from prev_result / config / any queue-supplied field.
        assert '"tenant_id": str(job.tenant_id)' in text
        assert "get_db_session(tenant_id=tenant_uuid, require_tenant=True)" in text

    def test_queue_envelope_cannot_override_authenticated_tenant(self) -> None:
        harness_mod = _load_module("hostile_fixtures_under_test", HOSTILE_FIXTURES)
        harness = harness_mod.HostileTenancyHarness()
        # Tenant A authenticated; envelope claims Tenant B -> rejected.
        with pytest.raises(PermissionError):
            harness.dispatch_queue_message(TENANT_A, {"tenant_id": TENANT_B, "job_id": "job-b"})
        # Missing tenant context -> rejected.
        with pytest.raises(ValueError):
            harness.dispatch_queue_message(TENANT_A, {"job_id": "job-a"})
        # Matching context dispatches and records the authenticated tenant.
        msg = harness.dispatch_queue_message(TENANT_A, {"tenant_id": TENANT_A, "job_id": "job-a"})
        assert msg["tenant_id"] == TENANT_A


# ---------------------------------------------------------------------------
# (d) Retried job after an org switch
# ---------------------------------------------------------------------------


class TestRetriedJobAfterOrgSwitch:
    def test_retry_with_new_tenant_context_cannot_see_old_job(self, job_store_module) -> None:
        """Job created under Tenant A; after an org switch the retried delivery
        arrives with Tenant B context -> the job must be invisible (the worker
        converts this into tenant_context_mismatch, see pipeline_runner)."""
        InMemoryJobStore = job_store_module.InMemoryJobStore
        PipelineJob = job_store_module.PipelineJob

        async def run() -> None:
            store = InMemoryJobStore()
            await store.set(PipelineJob(job_id="job-retry", tenant_id=TENANT_A))
            assert await store.exists("job-retry")  # job_id exists globally...
            assert await store.get("job-retry", tenant_id=TENANT_B) is None  # ...but not for B
            assert await store.get("job-retry", tenant_id=TENANT_A) is not None
            # Cross-tenant listing never leaks the job either
            assert [j.job_id for j in await store.list_jobs(tenant_id=TENANT_B)] == []

        asyncio.run(run())

    def test_artifacts_invisible_across_tenants(self, job_store_module) -> None:
        InMemoryJobStore = job_store_module.InMemoryJobStore
        PipelineJob = job_store_module.PipelineJob
        ExtractionArtifacts = job_store_module.ExtractionArtifacts

        async def run() -> None:
            store = InMemoryJobStore()
            await store.set(PipelineJob(job_id="job-art", tenant_id=TENANT_A))
            await store.set_artifacts("job-art", ExtractionArtifacts(result={"secret": "alpha"}))
            assert await store.get_artifacts("job-art", tenant_id=TENANT_B) is None
            visible = await store.get_artifacts("job-art", tenant_id=TENANT_A)
            assert visible is not None and visible.result == {"secret": "alpha"}

        asyncio.run(run())


# ---------------------------------------------------------------------------
# (e) Cache entries for the same object ID under another tenant
# ---------------------------------------------------------------------------


class _FakeRedis:
    """Minimal async Redis stand-in storing raw bytes."""

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: bytes) -> None:
        self.store[key] = value

    async def close(self) -> None:
        return None


class TestExtractionCacheTenantScope:
    def test_same_object_different_tenant_no_cache_hit(self, cache_module) -> None:
        ExtractionCache = cache_module.ExtractionCache

        async def run() -> None:
            cache = ExtractionCache(redis_url=None)
            await cache.set(TENANT_A, "hash-obj-1", "v1", "pack", "entities", value={"a": 1})
            assert await cache.get(TENANT_B, "hash-obj-1", "v1", "pack", "entities") is None
            assert await cache.get(TENANT_A, "hash-obj-1", "v1", "pack", "entities") == {"a": 1}

        asyncio.run(run())

    def test_cache_operations_require_tenant(self, cache_module) -> None:
        ExtractionCache = cache_module.ExtractionCache

        async def run() -> None:
            cache = ExtractionCache(redis_url=None)
            with pytest.raises(ValueError, match="tenant_id"):
                await cache.get("", "hash", "v1", "pack", "entities")
            with pytest.raises(ValueError, match="tenant_id"):
                await cache.set("", "hash", "v1", "pack", "entities", value={})

        asyncio.run(run())

    def test_tampered_envelope_tenant_is_rejected(self, cache_module) -> None:
        """If a Redis entry is forged so Tenant A's key holds an envelope
        claiming Tenant B, the read must be discarded (defense in depth)."""
        ExtractionCache = cache_module.ExtractionCache
        Envelope = cache_module.ExtractionCacheEnvelope

        async def run() -> None:
            cache = ExtractionCache(redis_url=None)
            fake_redis = _FakeRedis()
            cache._redis = fake_redis
            key = cache._make_key(TENANT_A, "hash-obj-9", "v1", "pack", "entities")
            forged = Envelope(version=1, tenant_id=TENANT_B, endpoint="entities", data={"stolen": True})
            fake_redis.store[key] = forged.model_dump_json().encode("utf-8")
            assert await cache.get(TENANT_A, "hash-obj-9", "v1", "pack", "entities") is None

        asyncio.run(run())

    def test_cache_key_is_tenant_namespaced(self, cache_module) -> None:
        cache = cache_module.ExtractionCache(redis_url=None)
        key_a = cache._make_key(TENANT_A, "same-hash", "v1", "pack", "entities")
        key_b = cache._make_key(TENANT_B, "same-hash", "v1", "pack", "entities")
        assert key_a != key_b, "identical objects in different tenants must not share a cache key"
