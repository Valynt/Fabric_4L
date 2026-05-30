from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from src.db.query_execution import (
    TenantExecutionContext,
    TenantQueryExecutor,
    TenantQueryValidationError,
)
from src.retrieval.hybrid_search import HybridSearch
from src.schema.constraints import CONSTRAINTS, INDEXES


def test_missing_tenant_context_fails_closed_for_graph_reads() -> None:
    with pytest.raises(TenantQueryValidationError, match="Tenant context is required"):
        TenantQueryExecutor._validate(
            query="MATCH (e:Entity {id: $entity_id, tenant_id: $tenant_id}) RETURN e",
            params={"entity_id": "entity-1"},
            context=TenantExecutionContext(tenant_id=None),
        )


@pytest.mark.asyncio
async def test_hybrid_search_forwards_authenticated_tenant_to_vector_store() -> None:
    class _VectorStore:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def search(self, **kwargs):
            self.calls.append(kwargs)
            return []

    vector_store = _VectorStore()
    search = HybridSearch(
        driver=None,
        vector_store=vector_store,
        graph_engine=None,
        settings=SimpleNamespace(),
    )

    await search.semantic_search(
        query="revenue leakage",
        entity_type="Capability",
        top_k=5,
        tenant_id="tenant-a",
    )

    assert vector_store.calls == [
        {
            "query_text": "revenue leakage",
            "entity_type": "Capability",
            "top_k": 5,
            "tenant_id": "tenant-a",
        }
    ]


def test_graph_service_entrypoints_require_explicit_tenant_id() -> None:
    from src.services.competitive_intel_service import CompetitiveIntelService
    from src.services.evidence_search import EvidenceSearchService
    from src.services.product_service import ProductService
    from src.services.signal_persistence import SignalPersistenceService
    from src.services.signal_quantification import SignalQuantificationService

    service_methods = [
        ProductService.create_product,
        ProductService.get_product,
        ProductService.update_product,
        ProductService.delete_product,
        CompetitiveIntelService.add_competitor,
        CompetitiveIntelService.get_competitor,
        CompetitiveIntelService.update_competitor,
        CompetitiveIntelService.delete_competitor,
        CompetitiveIntelService.add_battlecard,
        CompetitiveIntelService.record_win_loss,
        CompetitiveIntelService.analyze_competitive_landscape,
        CompetitiveIntelService.get_win_loss_summary,
        EvidenceSearchService.find_matching_evidence,
        EvidenceSearchService.search_by_keywords,
        EvidenceSearchService.get_evidence_details,
        EvidenceSearchService.index_evidence,
        SignalPersistenceService.persist_signal,
        SignalPersistenceService.link_evidence,
        SignalPersistenceService.map_to_value_driver,
        SignalPersistenceService.get_signals_for_account,
        SignalPersistenceService.get_signal_by_id,
        SignalPersistenceService.update_signal_impact,
        SignalQuantificationService.quantify_signal,
    ]

    for method in service_methods:
        tenant_param = inspect.signature(method).parameters.get("tenant_id")
        assert tenant_param is not None, f"{method.__qualname__} must declare tenant_id"
        assert tenant_param.default is inspect._empty, f"{method.__qualname__} must require tenant_id"


def test_tenant_partition_constraints_and_indexes_exist_for_graph_hot_labels() -> None:
    constraint_map = {(c.entity_type, tuple(c.property_name) if isinstance(c.property_name, list) else (c.property_name,)) for c in CONSTRAINTS}
    index_map = {(i.entity_type, tuple(i.properties)) for i in INDEXES}

    expected_constraints = {
        ("Entity", ("id", "tenant_id")),
        ("Product", ("id", "tenant_id")),
        ("Competitor", ("id", "tenant_id")),
        ("Battlecard", ("id", "tenant_id")),
        ("PainSignal", ("id", "tenant_id")),
        ("Evidence", ("id", "tenant_id")),
        ("ValueDriver", ("id", "tenant_id")),
        ("Formula", ("id", "tenant_id")),
        ("Account", ("id", "tenant_id")),
    }
    expected_indexes = {
        ("Entity", ("tenant_id",)),
        ("Entity", ("tenant_id", "id")),
        ("Product", ("tenant_id",)),
        ("Product", ("tenant_id", "id")),
        ("Competitor", ("tenant_id",)),
        ("Competitor", ("tenant_id", "id")),
        ("Evidence", ("tenant_id",)),
        ("Evidence", ("tenant_id", "id")),
        ("PainSignal", ("tenant_id",)),
        ("PainSignal", ("tenant_id", "id")),
        ("Formula", ("tenant_id",)),
        ("Formula", ("tenant_id", "id")),
        ("ValueDriver", ("tenant_id", "id")),
        ("Account", ("tenant_id",)),
        ("Account", ("tenant_id", "id")),
    }

    assert expected_constraints.issubset(constraint_map)
    assert expected_indexes.issubset(index_map)
