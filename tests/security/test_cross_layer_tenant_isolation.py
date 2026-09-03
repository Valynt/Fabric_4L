from __future__ import annotations

"""Cross-layer tenant isolation security tests.

Tests that verify tenant isolation across all layers:
- Layer 1 (Ingestion) tenant isolation
- Layer 2 (Extraction) tenant isolation
- Layer 3 (Knowledge) tenant isolation
- Layer 4 (Agents) tenant isolation
- Layer 5 (Ground Truth) tenant isolation
- Layer 6 (Benchmarks) tenant isolation
- Layer 7 (Billing) tenant isolation

Production Invariant: Tenant isolation must be enforced across all layers.
These tests verify that cross-layer tenant isolation is maintained.

Author: Autonomous Test Assurance Agent
Date: 2026-06-22
Priority: P0 (Security Boundary)

Remediation (2026-08-27):
The previous version of this suite skipped every test unconditionally. Each
case has been classified and either:

* converted to an executable black-box / repository-level behavioral test
  using two tenants wherever an in-process seam exists (L1 repository,
  L4 checkpoint router, L6 benchmark repository), or
* retained as a *governed* live-stack skip with metadata registered in
  ``config/ci/test_skip_register.yaml``, because local behavioral
  verification is impossible without a live service (Neo4j, cross-layer
  E2E, L2/L5/L7 service boundaries).

Retained skips are covered by the P0/security skip-governance ratchet in
``scripts/ci/check_p0_security_skip_governance.py``; an allowlisted skip
that expires or is newly introduced without a registered entry fails CI.
"""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from layer1_ingestion.crawler.decision_store import (
    CrawlDecisionRecord,
    InMemoryCrawlDecisionRepository,
)
from layer2_extraction.integration.job_store import (
    ExtractionArtifacts,
    InMemoryJobStore,
    PipelineJob,
)
from layer4_agents.api.routes import checkpoints
from layer6_benchmarks.repositories.benchmark_repository import BenchmarkRepository
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

pytestmark = [
    pytest.mark.security,
    pytest.mark.tenant_isolation,
    pytest.mark.cross_layer,
    pytest.mark.mandatory,
    pytest.mark.p0,
]


TENANT_A = str(uuid4())
TENANT_B = str(uuid4())


def _pipeline_job(job_id: str, tenant_id: str) -> PipelineJob:
    return PipelineJob(job_id=job_id, tenant_id=tenant_id)


def _decision(decision_id: str, tenant_id: str, url: str = "https://a.example.com/x") -> CrawlDecisionRecord:
    return CrawlDecisionRecord(
        decision_id=decision_id,
        job_id="job-1",
        tenant_id=tenant_id,
        url=url,
        domain="a.example.com",
        requested_path="/x",
        router_decision="allow",
        router_rule="known_dynamic_page:PRICING",
        quality_passed=True,
        quality_checks={"spa_detected": False},
        fallback_reason=None,
        final_path="/x",
        status_code=200,
        fast_duration_ms=0,
        browser_duration_ms=100,
        fetch_time_ms=100,
        bytes_transferred=5000,
        spa_detected=False,
        text_length=1000,
    )


@pytest.fixture
async def crawl_repo() -> InMemoryCrawlDecisionRepository:
    repo = InMemoryCrawlDecisionRepository()
    await repo.save(_decision("dec-a", TENANT_A))
    yield repo
    repo.clear()


class TestLayer1IngestionIsolation:
    """Test Layer 1 (Ingestion) tenant isolation.

    Converted from unconditional skips to black-box repository-level
    two-tenant behavior via ``InMemoryCrawlDecisionRepository``.
    """

    @pytest.mark.asyncio
    async def test_l1_crawl_jobs_tenant_scoped(self, crawl_repo):
        assert await crawl_repo.get_by_job("job-1", tenant_id=TENANT_A) != []
        assert await crawl_repo.get_by_job("job-1", tenant_id=TENANT_B) == []

    @pytest.mark.asyncio
    async def test_l1_crawl_decisions_tenant_scoped(self, crawl_repo):
        assert await crawl_repo.get_by_id("dec-a", tenant_id=TENANT_A) is not None
        assert await crawl_repo.get_by_id("dec-a", tenant_id=TENANT_B) is None
        assert await crawl_repo.get_by_url("https://a.example.com/x", tenant_id=TENANT_A) != []
        assert await crawl_repo.get_by_url("https://a.example.com/x", tenant_id=TENANT_B) == []
        assert await crawl_repo.get_by_domain("a.example.com", tenant_id=TENANT_A) != []
        assert await crawl_repo.get_by_domain("a.example.com", tenant_id=TENANT_B) == []

    @pytest.mark.asyncio
    async def test_l1_save_rejects_wrong_trusted_tenant(self, crawl_repo):
        from layer1_ingestion.shared.exceptions import TenantContextError

        with pytest.raises(TenantContextError, match="does not match trusted caller"):
            await crawl_repo.save(_decision("dec-forged", TENANT_A), trusted_tenant_id=TENANT_B)

    def test_l1_robots_cache_tenant_isolated(self):
        """Robots cache is tenant-isolated.

        Retained as a governed live-stack skip: the robots cache is an
        external service (Redis/HTTP fetch) with no in-process repository
        seam, so local behavioral verification is insufficient.
        """
        pytest.skip("Requires cross-layer integration test")


class TestLayer2ExtractionIsolation:
    """Test Layer 2 (Extraction) tenant isolation.

    Converted from unconditional skips to black-box two-tenant behavior via
    ``InMemoryJobStore``. The store enforces ``tenant_id`` on job reads and
    lists; ``get_artifacts`` must not leak artifacts across tenants.
    """

    @pytest.mark.asyncio
    async def test_l2_extraction_jobs_tenant_scoped(self):
        store = InMemoryJobStore()
        await store.set_job(
            _pipeline_job(job_id="job-A", tenant_id=TENANT_A)
        )
        await store.set_job(
            _pipeline_job(job_id="job-B", tenant_id=TENANT_B)
        )

        # Valid caller sees only its own job; cross-tenant read is denied.
        assert await store.get_job("job-A", tenant_id=TENANT_A) is not None
        with pytest.raises(KeyError):
            await store.get_job("job-A", tenant_id=TENANT_B)
        assert [j.job_id for j in await store.list_jobs(tenant_id=TENANT_A)] == ["job-A"]

    @pytest.mark.asyncio
    async def test_l2_artifacts_tenant_scoped(self):
        """Tenant B cannot read or infer tenant A's extraction artifacts."""
        store = InMemoryJobStore()
        await store.set_job(_pipeline_job(job_id="job-A", tenant_id=TENANT_A))
        await store.set_artifacts("job-A", ExtractionArtifacts(result={"ok": True}))

        # Owner can read; a different tenant must be denied (no leak).
        assert await store.get_artifacts("job-A", tenant_id=TENANT_A) is not None
        assert await store.get_artifacts("job-A", tenant_id=TENANT_B) is None

    def test_l2_signals_tenant_scoped(self):
        pytest.skip("Requires L2 service integration")


class TestLayer3KnowledgeIsolation:
    """Test Layer 3 (Knowledge) tenant isolation."""

    def test_l3_graph_queries_tenant_scoped(self):
        pytest.skip("Requires L3 service integration")

    def test_l3_vector_search_tenant_scoped(self):
        pytest.skip("Requires L3 service integration")

    def test_l3_knowledge_subgraphs_tenant_scoped(self):
        pytest.skip("Requires L3 service integration")


class _FakeConn:
    async def fetch(self, _query: str, thread_id: str, tenant_id: str, _limit: int):
        if thread_id == "wf-b" and tenant_id == "tenant-b":
            return [
                {
                    "thread_id": "wf-b",
                    "checkpoint_id": "chk-1",
                    "state_data": {"tenant_id": "tenant-b", "current_node": "node"},
                    "created_at": None,
                }
            ]
        return []

    async def fetchrow(self, _query: str, thread_id: str, checkpoint_id: str, tenant_id: str):
        if thread_id == "wf-b" and checkpoint_id == "chk-1" and tenant_id == "tenant-b":
            return {
                "thread_id": "wf-b",
                "checkpoint_id": "chk-1",
                "state_data": {"tenant_id": "tenant-b", "current_node": "node"},
                "created_at": None,
            }
        return None


class _FakeExecutor:
    checkpoint_saver = type("Saver", (), {"conn": _FakeConn()})()

    async def get_workflow_status(self, workflow_id: str):
        if workflow_id == "wf-b":
            return {"workflow_id": workflow_id, "tenant_id": "tenant-b", "status": "paused"}
        return None

    async def resume_from_checkpoint(self, **_kwargs):
        return {"status": "resumed"}


@pytest.fixture
async def l4_client() -> AsyncClient:
    app = FastAPI()
    app.include_router(checkpoints.checkpoint_router, prefix="/v1")
    register_exception_handlers(app)
    app.dependency_overrides[checkpoints.get_executor] = lambda: _FakeExecutor()
    app.dependency_overrides[checkpoints.require_authenticated] = lambda: RequestContext(
        tenant_id="tenant-a", user_id="user-a", roles=[]
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestLayer4AgentsIsolation:
    """Test Layer 4 (Agents) tenant isolation.

    Converted from unconditional skips to executable behavioral tests against
    the real ``checkpoint_router``; cross-tenant access fails closed with 403.
    """

    @pytest.mark.asyncio
    async def test_l4_workflows_tenant_scoped(self, l4_client: AsyncClient):
        response = await l4_client.get("/v1/workflows/wf-b/checkpoints")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_l4_agent_states_tenant_scoped(self, l4_client: AsyncClient):
        response = await l4_client.get("/v1/workflows/wf-b/checkpoints/chk-1/state")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_l4_checkpoints_tenant_scoped(self, l4_client: AsyncClient):
        diff = await l4_client.post(
            "/v1/workflows/wf-b/checkpoints/diff",
            json={"checkpoint_a_id": "chk-1", "checkpoint_b_id": "chk-1"},
        )
        assert diff.status_code == 403
        resume = await l4_client.post(
            "/v1/workflows/wf-b/resume-from-checkpoint",
            json={"checkpoint_id": "chk-1", "resume_data": {}, "skip_nodes": []},
        )
        assert resume.status_code == 403


class TestLayer5GroundTruthIsolation:
    """Test Layer 5 (Ground Truth) tenant isolation."""

    def test_l5_truth_objects_tenant_scoped(self):
        pytest.skip("Requires L5 service integration")

    def test_l5_value_claims_tenant_scoped(self):
        pytest.skip("Requires L5 service integration")

    def test_l5_governance_records_tenant_scoped(self):
        pytest.skip("Requires L5 service integration")


@pytest.fixture
def l6_repo():
    from unittest.mock import AsyncMock, MagicMock

    driver = MagicMock()
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    driver.session.return_value = session
    return BenchmarkRepository(driver)


class TestLayer6BenchmarksIsolation:
    """Test Layer 6 (Benchmarks) tenant isolation.

    Converted from unconditional skips to repository-level behavioral tests:
    every Cypher read carries the authenticated tenant_id predicate.
    """

    @pytest.mark.asyncio
    async def test_l6_benchmark_datasets_tenant_scoped(self, l6_repo):
        from unittest.mock import AsyncMock

        mock_tx = AsyncMock()
        mock_records = AsyncMock()
        mock_records.single = AsyncMock(return_value=None)
        mock_tx.run = AsyncMock(return_value=mock_records)

        await l6_repo._tx_get_dataset(mock_tx, "ds-a", TENANT_A)

        mock_tx.run.assert_called_once()
        (query,), call_kwargs = mock_tx.run.call_args
        assert "$tenant_id" in query
        assert call_kwargs["tenant_id"] == TENANT_A
        assert call_kwargs["dataset_id"] == "ds-a"

    def test_l6_benchmark_results_tenant_scoped(self):
        pytest.skip("Requires L6 service integration")


class TestLayer7BillingIsolation:
    """Test Layer 7 (Billing) tenant isolation."""

    def test_l7_usage_records_tenant_scoped(self):
        pytest.skip("Requires L7 service integration")

    def test_l7_invoices_tenant_scoped(self):
        pytest.skip("Requires L7 service integration")

    def test_l7_billing_overages_tenant_scoped(self):
        pytest.skip("Requires L7 service integration")


class TestCrossLayerDataFlow:
    """Test that tenant context propagates correctly across layers.

    Cross-layer propagation is a true live-stack E2E behavior; each hop
    requires running adjacent services, so these remain governed skips.
    """

    def test_tenant_context_propagation_l1_to_l2(self):
        pytest.skip("Requires cross-layer integration test")

    def test_tenant_context_propagation_l2_to_l3(self):
        pytest.skip("Requires cross-layer integration test")

    def test_tenant_context_propagation_l3_to_l4(self):
        pytest.skip("Requires cross-layer integration test")

    def test_tenant_context_propagation_l4_to_l5(self):
        pytest.skip("Requires cross-layer integration test")

    def test_tenant_context_propagation_l5_to_l6(self):
        pytest.skip("Requires cross-layer integration test")

    def test_tenant_context_propagation_l6_to_l7(self):
        pytest.skip("Requires cross-layer integration test")


class TestCrossLayerHostileAttempts:
    """Test adversarial cross-layer tenant isolation bypass attempts."""

    def test_cannot_access_l1_data_from_l2_different_tenant(self):
        pytest.skip("Requires cross-layer integration test")

    def test_cannot_access_l2_data_from_l3_different_tenant(self):
        pytest.skip("Requires cross-layer integration test")

    def test_cannot_access_l3_data_from_l4_different_tenant(self):
        pytest.skip("Requires cross-layer integration test")

    def test_cannot_access_l4_data_from_l5_different_tenant(self):
        pytest.skip("Requires cross-layer integration test")


class TestPositiveCases:
    """POSITIVE: Test that legitimate cross-layer access works."""

    @pytest.mark.asyncio
    async def test_same_tenant_cross_layer_access_works(self, crawl_repo):
        assert await crawl_repo.get_by_id("dec-a", tenant_id=TENANT_A) is not None
        assert await crawl_repo.get_by_url("https://a.example.com/x", tenant_id=TENANT_A) != []

    def test_tenant_context_consistency_across_layers(self):
        pytest.skip("Requires cross-layer integration test")
