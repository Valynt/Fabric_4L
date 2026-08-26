"""Guard: L2 extraction jobs are tenant-bound; forged queue payloads are
rejected explicitly, not implicitly (#1258 / T-4).

Previously a Celery payload carrying job_id + config.tenant_id was validated
only for presence of tenant_id; the job record was created tenantless, so a
forged payload naming another tenant's job could be processed under the wrong
context. Now the job is bound to the authenticated tenant at creation, and an
existing job under a DIFFERENT tenant raises AuthorizationError
(tenant_context_mismatch) — fail closed, non-retryable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.p0, pytest.mark.tenant_boundary, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
L2_PIPELINE_RUNNER = (
    REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/pipeline_runner.py"
)
L2_JOB_STORE = (
    REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/integration/job_store.py"
)


class TestTenantBoundJobWiring:
    def test_job_created_with_tenant_binding(self) -> None:
        text = L2_PIPELINE_RUNNER.read_text(encoding="utf-8")
        assert "tenant_id=tenant_id," in text, "PipelineJob must be bound to the authenticated tenant at creation"

    def test_forged_payload_raises_tenant_mismatch(self) -> None:
        text = L2_PIPELINE_RUNNER.read_text(encoding="utf-8")
        assert '"code": "tenant_context_mismatch"' in text
        assert "AuthorizationError" in text
        # The mismatch check must run when the job already exists
        assert "await job_store.get(job_id, tenant_id=tenant_id)" in text

    def test_job_store_enforces_tenant_scoped_lookup(self) -> None:
        text = L2_JOB_STORE.read_text(encoding="utf-8")
        assert "job.tenant_id != tenant_id" in text
        assert "tenant_id: str | None = None" in text


class TestBehavioralProof:
    def test_inmemory_store_rejects_cross_tenant_lookup(self) -> None:
        # Load job_store.py directly by path: importing via the package triggers
        # integration/__init__.py, which pulls the full service stack (layer3
        # client, sqlalchemy, ...). job_store.py itself only needs pydantic.
        import asyncio
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("l2_job_store_under_test", L2_JOB_STORE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        # Register in sys.modules BEFORE exec so pydantic can resolve the
        # `from __future__ import annotations` string annotations (datetime).
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        InMemoryJobStore = module.InMemoryJobStore
        PipelineJob = module.PipelineJob

        async def run() -> None:
            store = InMemoryJobStore()
            await store.set(PipelineJob(job_id="job-a", tenant_id="tenant-a"))
            # Same tenant: visible
            assert await store.get("job-a", tenant_id="tenant-a") is not None
            # Cross tenant: invisible (the mismatch path in run_extraction
            # converts this into an explicit AuthorizationError)
            assert await store.get("job-a", tenant_id="tenant-b") is None

        asyncio.run(run())
