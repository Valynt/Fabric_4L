from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.agents.provenance_tracking import ProvenanceTrackingAgent
from src.agents.roi_calculation import ROICalculationAgent
from src.agents.value_tree_projection import ValueTreeProjectionAgent
from src.agents.whitespace_analysis import WhitespaceAnalysisAgent
from src.schema.entity_resolution import EntityResolutionRequest, ResolutionStrategy
from src.services.competitive_intel_service import (
    CompetitiveIntelService,
    CompetitorCreate,
)
from src.services.competitive_intel_service import (
    _get_tenant_id as get_competitive_tenant,
)
from src.services.entity_resolution import EntityResolutionService
from src.services.evidence_search import EvidenceSearchService
from src.services.product_service import (
    FeatureCreate,
    ProductCreate,
    ProductService,
)
from src.services.product_service import (
    _get_tenant_id as get_product_tenant,
)
from src.services.roi_calculator_service import ROICalculatorService, ROITemplateCreate
from src.services.signal_persistence import SignalPersistenceService
from src.services.signal_quantification import SignalQuantificationService


class FakeAsyncSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeAsyncDriver:
    def session(self):
        return FakeAsyncSession()


class EmptyAsyncResult:
    def __init__(self, single_record=None):
        self._single_record = single_record

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration

    async def single(self):
        return self._single_record


class AsyncSingleResult:
    def __init__(self, record):
        self._record = record

    async def single(self):
        return self._record


class AsyncDataResult:
    def __init__(self, records):
        self._records = records

    async def data(self):
        return self._records


def assert_explicit_tenant_queries(calls, tenant_id="tenant-secure", tenant_param="tenant_id"):
    assert calls
    for call in calls:
        assert call["tenant_id"] == tenant_id
        assert call["params"][tenant_param] == tenant_id
        assert call["kwargs"]["require_explicit_tenant_id"] is True


@pytest.mark.asyncio
async def test_evidence_link_routes_forward_authenticated_tenant_context(monkeypatch):
    from src.api.routes import evidence

    observed = []

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class FakeDriver:
        def session(self):
            return FakeSession()

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append(
            {"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs}
        )
        if "RETURN count(r)" in query:
            return AsyncSingleResult({"deleted": 1})
        return AsyncDataResult(
            [
                {
                    "evidence_id": "evidence-1",
                    "evidence_title": "Evidence",
                    "evidence_type": "case_study",
                }
            ]
        )

    monkeypatch.setattr(evidence, "run_validated_query", fake_run_validated_query)

    assert await evidence.unlink_evidence_from_driver(
        evidence_id="evidence-1",
        driver_id="driver-1",
        tenant_id="tenant-secure",
        driver=FakeDriver(),
    ) == {"evidence_id": "evidence-1", "driver_id": "driver-1", "deleted": 1}
    links = await evidence.list_evidence_links(
        driver_id="driver-1",
        tenant_id="tenant-secure",
        driver=FakeDriver(),
    )

    assert links["links"][0]["evidence_id"] == "evidence-1"
    for call in observed:
        assert call["tenant_id"] == "tenant-secure"
        assert call["params"]["tenant_id"] == "tenant-secure"
        assert call["kwargs"]["require_explicit_tenant_id"] is True
    assert {call["kwargs"]["query_name"] for call in observed} == {
        "evidence.unlink_evidence_from_driver",
        "evidence.list_driver_evidence_links",
    }


@pytest.mark.asyncio
async def test_sync_manager_metadata_reads_forward_authenticated_tenant_context(monkeypatch):
    from src.ingestion import sync_manager

    observed = []
    tenant_id = "11111111-1111-1111-1111-111111111111"

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class FakeDriver:
        def session(self, database=None):
            return FakeSession()

    class FakeLoader:
        async def _get_driver(self):
            return FakeDriver()

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append(
            {"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs}
        )
        return AsyncSingleResult(
            {
                "s": {
                    "source_id": "source-1",
                    "extraction_job_id": "job-1",
                    "content_hash": "hash-1",
                    "synced_at": "2026-06-05T00:00:00+00:00",
                    "status": "completed",
                    "error": None,
                    "tenant_id": tenant_id,
                }
            }
        )

    monkeypatch.setattr(sync_manager, "run_validated_query", fake_run_validated_query)

    manager = sync_manager.SyncManager(
        loader=FakeLoader(),
        settings=SimpleNamespace(neo4j_database="neo4j"),
    )
    status = await manager.get_sync_status("source-1", tenant_id)

    assert status["source_id"] == "source-1"
    assert observed[0]["tenant_id"] == tenant_id
    assert observed[0]["params"]["tenant_id"] == tenant_id
    assert observed[0]["kwargs"]["require_explicit_tenant_id"] is True
    assert observed[0]["kwargs"]["query_name"] == "sync_manager.get_sync_status"


def test_product_service_requires_context_tenant(monkeypatch):
    monkeypatch.setattr(
        'src.services.product_service.require_context',
        lambda: (_ for _ in ()).throw(RuntimeError('no context')),
    )
    with pytest.raises(RuntimeError, match='tenant_id is required'):
        get_product_tenant()


def test_competitive_service_requires_context_tenant(monkeypatch):
    monkeypatch.setattr(
        'src.services.competitive_intel_service.require_context',
        lambda: (_ for _ in ()).throw(RuntimeError('no context')),
    )
    with pytest.raises(RuntimeError, match='tenant_id is required'):
        get_competitive_tenant()


@pytest.mark.asyncio
async def test_product_run_cypher_requires_tenant_id():
    service = ProductService(MagicMock())
    with pytest.raises(RuntimeError, match='tenant_id is required'):
        await service._run_cypher(MagicMock(), 'MATCH (p:Product) RETURN p', {})


@pytest.mark.asyncio
async def test_product_run_cypher_forwards_authenticated_tenant_id(monkeypatch):
    observed = {}

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.update({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        return ["ok"]

    monkeypatch.setattr("src.services.product_service.run_validated_query", fake_run_validated_query)

    service = ProductService(MagicMock())
    result = await service._run_cypher(
        MagicMock(),
        "MATCH (p:Product {tenant_id: $tenant_id}) RETURN p",
        {"tenant_id": "tenant-a"},
    )

    assert result == ["ok"]
    assert observed["tenant_id"] == "tenant-a"
    assert observed["params"] == {"tenant_id": "tenant-a"}
    assert observed["kwargs"]["require_explicit_tenant_id"] is True


@pytest.mark.asyncio
async def test_product_mutations_use_audited_graph_mutation(monkeypatch):
    observed = []

    class FakeMutation:
        def __init__(self, *, tenant_id, session, operation_source):
            observed.append({"tenant_id": tenant_id, "operation_source": operation_source})

        async def write_node(self, label, node_id, properties):
            observed.append({"action": "write_node", "label": label, "tenant_id": properties["tenant_id"]})

        async def write_relationship(self, src_id, rel_type, tgt_id, properties=None, versioned=True):
            observed.append({"action": "write_relationship", "rel_type": rel_type, "versioned": versioned})

        async def delete_node(self, label, node_id):
            observed.append({"action": "delete_node", "label": label, "node_id": node_id})

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"action": "query", "tenant_id": tenant_id, "params": params, "kwargs": kwargs})
        return AsyncSingleResult({"found": 1, "feature_ids": []})

    monkeypatch.setattr("src.services.product_service.AuditedGraphMutation", FakeMutation)
    monkeypatch.setattr("src.services.product_service.run_validated_query", fake_run_validated_query)

    service = ProductService(FakeAsyncDriver())

    await service.create_product(
        "tenant-secure",
        ProductCreate(name="Product", description="Desc"),
    )
    await service.add_feature(
        "tenant-secure",
        "product-1",
        FeatureCreate(name="Feature", description="Desc"),
    )
    assert await service.delete_product("tenant-secure", "product-1") is True

    assert {"action": "write_node", "label": "Product", "tenant_id": "tenant-secure"} in observed
    assert {"action": "write_node", "label": "Feature", "tenant_id": "tenant-secure"} in observed
    assert {"action": "write_relationship", "rel_type": "HAS_FEATURE", "versioned": False} in observed
    assert {"action": "delete_node", "label": "Product", "node_id": "product-1"} in observed
    assert_explicit_tenant_queries([call for call in observed if call.get("action") == "query"])


@pytest.mark.asyncio
async def test_competitive_run_cypher_requires_tenant_id():
    service = CompetitiveIntelService(MagicMock())
    with pytest.raises(RuntimeError, match='tenant_id is required'):
        await service._run_cypher(MagicMock(), 'MATCH (c:Competitor) RETURN c', {})


@pytest.mark.asyncio
async def test_competitive_run_cypher_forwards_authenticated_tenant_id(monkeypatch):
    observed = {}

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.update({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        return ["ok"]

    monkeypatch.setattr("src.services.competitive_intel_service.run_validated_query", fake_run_validated_query)

    service = CompetitiveIntelService(MagicMock())
    result = await service._run_cypher(
        MagicMock(),
        "MATCH (c:Competitor {tenant_id: $tenant_id}) RETURN c",
        {"tenant_id": "tenant-a"},
    )

    assert result == ["ok"]
    assert observed["tenant_id"] == "tenant-a"
    assert observed["params"] == {"tenant_id": "tenant-a"}
    assert observed["kwargs"]["require_explicit_tenant_id"] is True


@pytest.mark.asyncio
async def test_competitive_mutations_use_audited_graph_mutation(monkeypatch):
    observed = []

    class FakeMutation:
        def __init__(self, *, tenant_id, session, operation_source):
            observed.append({"tenant_id": tenant_id, "operation_source": operation_source})

        async def write_node(self, label, node_id, properties):
            observed.append({"action": "write_node", "label": label, "tenant_id": properties["tenant_id"]})

        async def delete_node(self, label, node_id):
            observed.append({"action": "delete_node", "label": label, "node_id": node_id})

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"action": "query", "tenant_id": tenant_id, "params": params, "kwargs": kwargs})
        return AsyncSingleResult({"found": 1, "battlecard_ids": []})

    monkeypatch.setattr("src.services.competitive_intel_service.AuditedGraphMutation", FakeMutation)
    monkeypatch.setattr("src.services.competitive_intel_service.run_validated_query", fake_run_validated_query)

    service = CompetitiveIntelService(FakeAsyncDriver())

    await service.add_competitor(
        "tenant-secure",
        CompetitorCreate(name="Competitor", description="Desc"),
    )
    assert await service.delete_competitor("tenant-secure", "competitor-1") is True

    assert {"action": "write_node", "label": "Competitor", "tenant_id": "tenant-secure"} in observed
    assert {"action": "delete_node", "label": "Competitor", "node_id": "competitor-1"} in observed
    assert_explicit_tenant_queries([call for call in observed if call.get("action") == "query"])


@pytest.mark.asyncio
async def test_entity_resolution_candidate_queries_require_explicit_tenant_context(monkeypatch):
    observed = []

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        result = MagicMock()
        result.data = AsyncMock(return_value=[])
        return result

    monkeypatch.setattr("src.services.entity_resolution.run_validated_query", fake_run_validated_query)

    service = EntityResolutionService(MagicMock())
    session = MagicMock()
    request = EntityResolutionRequest(
        entity_type="Organization",
        tenant_id="tenant-secure",
        query_attributes={"name": "Acme", "embedding": [0.11, 0.22]},
        strategy=ResolutionStrategy.HYBRID,
    )

    await service._find_exact_candidates(session, request)
    await service._find_fuzzy_candidates(session, request)
    await service._find_vector_candidates(session, request)

    assert len(observed) == 3
    assert_explicit_tenant_queries(observed)


@pytest.mark.asyncio
async def test_whitespace_analysis_queries_require_explicit_tenant_context(monkeypatch):
    observed = []

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        return EmptyAsyncResult()

    monkeypatch.setattr("src.agents.whitespace_analysis.run_validated_query", fake_run_validated_query)

    agent = WhitespaceAnalysisAgent(FakeAsyncDriver())

    gaps = await agent._identify_gaps(
        "Acme",
        ["pain-1"],
        ["capability-1"],
        tenant_id="tenant-secure",
    )
    maturity = await agent._assess_maturity(
        "Acme",
        ["capability-1"],
        tenant_id="tenant-secure",
    )
    pathways = await agent._generate_expansion_pathways(
        "Acme",
        "capability-1",
        tenant_id="tenant-secure",
    )

    assert gaps["error"] == ""
    assert maturity["error"] == ""
    assert pathways["error"] == ""
    assert len(observed) == 3
    assert_explicit_tenant_queries(observed)


@pytest.mark.asyncio
async def test_provenance_tracking_queries_require_explicit_tenant_context(monkeypatch):
    observed = []

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        return EmptyAsyncResult({"id": "created"})

    monkeypatch.setattr("src.agents.provenance_tracking.run_validated_query", fake_run_validated_query)

    agent = ProvenanceTrackingAgent(FakeAsyncDriver())

    entity = await agent._record_entity(
        "DOCUMENT",
        "document-1",
        "Document",
        {},
        tenant_id="tenant-secure",
    )
    activity = await agent._record_activity(
        "EXTRACTION",
        "activity-1",
        "Extraction",
        {},
        tenant_id="tenant-secure",
    )
    derivation = await agent._record_derivation(
        "derived-1",
        "source-1",
        tenant_id="tenant-secure",
    )
    trace = await agent._create_decision_trace(
        "workflow-1",
        "instance-1",
        "value_model",
        "output-1",
        [{"description": "step"}],
        tenant_id="tenant-secure",
    )
    lineage = await agent._query_lineage("document-1", tenant_id="tenant-secure")

    assert entity["error"] == ""
    assert activity["error"] == ""
    assert derivation["error"] == ""
    assert trace["trace_id"]
    assert lineage["error"] == ""
    assert len(observed) == 6
    assert_explicit_tenant_queries(observed)


@pytest.mark.asyncio
async def test_roi_calculation_queries_require_explicit_tenant_context(monkeypatch):
    observed = []

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        return EmptyAsyncResult()

    monkeypatch.setattr("src.agents.roi_calculation.run_validated_query", fake_run_validated_query)

    agent = ROICalculationAgent(FakeAsyncDriver())

    formulas = await agent._retrieve_formulas("use-case-1", tenant_id="tenant-secure")
    formula = await agent._get_formula("formula-1", tenant_id="tenant-secure")

    assert formulas["error"] == ""
    assert formula is None
    assert len(observed) == 2
    assert_explicit_tenant_queries(observed, tenant_param="_tenant_id")


@pytest.mark.asyncio
async def test_signal_quantification_formula_lookup_requires_explicit_tenant_context(monkeypatch):
    observed = []

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        return AsyncSingleResult(None)

    monkeypatch.setattr("src.services.signal_quantification.run_validated_query", fake_run_validated_query)

    service = SignalQuantificationService(FakeAsyncDriver())
    formula = await service._select_formula(
        "tenant-secure",
        "Downtime",
        "System downtime",
        "manufacturing",
    )

    assert formula["id"] == "default-operational"
    assert observed == [
        {
            "query": observed[0]["query"],
            "params": {
                "formula_ids": ["ai-f-001"],
                "tenant_id": "tenant-secure",
            },
            "tenant_id": "tenant-secure",
            "kwargs": observed[0]["kwargs"],
        }
    ]
    assert observed[0]["kwargs"]["require_explicit_tenant_id"] is True


@pytest.mark.asyncio
async def test_roi_calculator_service_uses_explicit_tenant_for_reads_and_audited_writes(monkeypatch):
    observed_queries = []
    observed_mutations = []

    class FakeMutation:
        def __init__(self, *, tenant_id, session, operation_source):
            observed_mutations.append({"tenant_id": tenant_id, "operation_source": operation_source})

        async def write_node(self, label, node_id, properties):
            observed_mutations.append(
                {"label": label, "node_id": node_id, "tenant_id": properties["tenant_id"]}
            )
            return {"status": "ok", "id": node_id}

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed_queries.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        return EmptyAsyncResult({"total": 0, "calculation": None, "case_count": 0})

    monkeypatch.setattr("src.services.roi_calculator_service.run_validated_query", fake_run_validated_query)
    monkeypatch.setattr("src.services.roi_calculator_service.AuditedGraphMutation", FakeMutation)
    monkeypatch.setattr("src.services.roi_calculator_service._get_tenant_id", lambda: "tenant-secure")

    service = ROICalculatorService(FakeAsyncDriver())

    await service.create_template_for_tenant(
        "tenant-secure",
        ROITemplateCreate(name="Template", description="Desc"),
    )
    await service.get_templates("tenant-secure")
    await service.save_calculation(
        "tenant-secure",
        inputs={"num_employees": 100},
        outputs={"roi_pct_year1": 150.0},
    )
    assert await service.get_calculation("tenant-secure", "calc-1") is None
    await service.list_calculations()
    await service.get_industry_benchmarks("tenant-secure", "technology")

    assert observed_mutations[0]["tenant_id"] == "tenant-secure"
    assert observed_mutations[1]["label"] == "ROITemplate"
    assert observed_mutations[1]["tenant_id"] == "tenant-secure"
    assert observed_mutations[2]["tenant_id"] == "tenant-secure"
    assert observed_mutations[3]["label"] == "ROICalculation"
    assert observed_mutations[3]["tenant_id"] == "tenant-secure"

    assert_explicit_tenant_queries(observed_queries)


@pytest.mark.asyncio
async def test_signal_persistence_reads_require_explicit_tenant_context(monkeypatch):
    observed = []

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        result = MagicMock()
        result.data = AsyncMock(return_value=[])
        result.single = AsyncMock(return_value=None)
        return result

    monkeypatch.setattr("src.services.signal_persistence.run_validated_query", fake_run_validated_query)

    service = SignalPersistenceService(FakeAsyncDriver())

    assert await service.get_signals_for_account("tenant-secure", "account-1") == []
    assert await service.get_signal_by_id("tenant-secure", "signal-1") is None

    assert len(observed) == 2
    assert_explicit_tenant_queries(observed)


@pytest.mark.asyncio
async def test_evidence_search_queries_require_explicit_tenant_context(monkeypatch):
    observed = []

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        result = MagicMock()
        result.data = AsyncMock(return_value=[])
        result.single = AsyncMock(
            return_value={"evidence_id": "evidence-1"} if "embedding" in params else None
        )
        return result

    monkeypatch.setattr("src.services.evidence_search.run_validated_query", fake_run_validated_query)

    service = EvidenceSearchService(FakeAsyncDriver())
    monkeypatch.setattr(service, "_generate_embedding", AsyncMock(return_value=[0.1, 0.2, 0.3]))

    assert await service.find_matching_evidence("tenant-secure", "late invoices") == []
    assert await service.search_by_keywords("tenant-secure", ["invoice"]) == []
    assert await service.get_evidence_details("tenant-secure", "evidence-1") is None
    assert (
        await service.index_evidence(
            "tenant-secure",
            {"id": "evidence-1", "title": "Evidence"},
            [0.1, 0.2, 0.3],
        )
        == "evidence-1"
    )

    assert len(observed) == 4
    assert_explicit_tenant_queries(observed)


@pytest.mark.asyncio
async def test_value_tree_projection_traversals_require_explicit_tenant_context(monkeypatch):
    observed = []

    async def fake_run_validated_query(session, query, params, *, tenant_id=None, **kwargs):
        observed.append({"query": query, "params": params, "tenant_id": tenant_id, "kwargs": kwargs})
        return EmptyAsyncResult()

    monkeypatch.setattr("src.agents.value_tree_projection.run_validated_query", fake_run_validated_query)

    agent = ValueTreeProjectionAgent(FakeAsyncDriver())

    upward = await agent._upward_traversal("capability-1", tenant_id="tenant-secure")
    downward = await agent._downward_traversal("outcome-1", tenant_id="tenant-secure")

    assert upward["paths"] == []
    assert downward["paths"] == []
    assert len(observed) == 2
    assert_explicit_tenant_queries(observed)
