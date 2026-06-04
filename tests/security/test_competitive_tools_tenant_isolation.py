"""Security regression tests for competitive intelligence tool tenant isolation."""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_query_graph_for_competitor_enforces_tenant_scope() -> None:
    """Same competitor name across tenants must never leak related attributes."""
    fake_neo4j_module = types.SimpleNamespace(AsyncGraphDatabase=MagicMock())
    sys.modules.setdefault("neo4j", fake_neo4j_module)
    from layer4_agents.tools.competitive_tools import AnalyzeCompetitionTool

    tool = AnalyzeCompetitionTool()

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(
        return_value=[
            {
                "capabilities": ["tenant-a capability"],
                "risks": ["tenant-a risk"],
                "cost_items": ["tenant-a cost"],
            }
        ]
    )
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    mock_driver.session.return_value.__aexit__.return_value = False
    mock_driver.close = AsyncMock()

    with patch("neo4j.AsyncGraphDatabase.driver", return_value=mock_driver):
        await tool._query_graph_for_competitor(
            competitor_name="Acme",
            tenant_id="tenant-a",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            database="valuefabric",
        )

    mock_session.run.assert_called_once()
    query_text = mock_session.run.call_args.args[0]
    params = mock_session.run.call_args.args[1]

    assert "MATCH (c:Competitor {name: $name, tenant_id: $tenant_id})" in query_text
    assert "WHERE cap.tenant_id = $tenant_id" in query_text
    assert "WHERE r.tenant_id = $tenant_id" in query_text
    assert "WHERE cs.tenant_id = $tenant_id" in query_text
    assert params["name"] == "Acme"
    assert params["tenant_id"] == "tenant-a"
