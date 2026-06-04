from __future__ import annotations

import pytest
from pathlib import Path

from src.agents.roi_calculation import ROICalculationAgent
from src.analytics.similarity import SimilarityAnalyzer
from value_fabric.shared.identity.context import set_request_context

# Canonical source root for Layer 3 (via the value_fabric.layer3 shim).
_L3_SRC = Path(__file__).resolve().parents[2] / "services" / "layer3-knowledge" / "src"


@pytest.mark.security
@pytest.mark.unit
def test_similarity_methods_fail_closed_when_tenant_missing() -> None:
    """SimilarityAnalyzer._resolve_tenant_id must raise when tenant_id is absent."""
    analyzer = SimilarityAnalyzer()
    set_request_context(None)
    # Production code raises RuntimeError (missing context — programming error).
    with pytest.raises((RuntimeError, ValueError)):
        analyzer._resolve_tenant_id(None)


@pytest.mark.security
@pytest.mark.unit
async def test_roi_operations_fail_closed_when_tenant_missing() -> None:
    """ROICalculationAgent must raise when tenant_id is absent."""
    agent = ROICalculationAgent(driver=None)
    with pytest.raises((RuntimeError, ValueError)):
        await agent._retrieve_formulas("uc-1", None)
    with pytest.raises((RuntimeError, ValueError)):
        await agent._get_formula("f-1", None)


@pytest.mark.security
@pytest.mark.unit
def test_similarity_queries_are_tenant_scoped_across_traversals() -> None:
    """Cypher queries in SimilarityAnalyzer must carry tenant_id predicates."""
    content = (_L3_SRC / "analytics" / "similarity.py").read_text(encoding="utf-8")
    assert "AND common.tenant_id = $_tenant_id" in content
    assert "all(node IN nodes(path) WHERE node.tenant_id = $_tenant_id)" in content


@pytest.mark.security
@pytest.mark.unit
def test_roi_queries_are_tenant_scoped_across_traversals() -> None:
    """Cypher queries in ROICalculationAgent must carry tenant_id predicates."""
    content = (_L3_SRC / "agents" / "roi_calculation.py").read_text(encoding="utf-8")
    assert (
        "MATCH (uc:UseCase {id: $use_case_id, tenant_id: $_tenant_id})"
        "-[:delivers]->(vd:ValueDriver {tenant_id: $_tenant_id})"
    ) in content
    assert (
        "OPTIONAL MATCH (vd)-[:measuredBy|calculatedBy]->(f:Formula {tenant_id: $_tenant_id})"
    ) in content
