from __future__ import annotations

import pytest
from fastapi import HTTPException
from types import SimpleNamespace

from src.api.models import GraphRAGQuery, SearchRequest, SearchType
from src.api.routes import query_search, system


class _TimeoutGraphRag:
    async def query(self, **kwargs):
        raise TimeoutError("upstream timeout")


class _BadPayloadGraphRag:
    async def query(self, **kwargs):
        return {"query": "x", "search_type": object()}


class _TimeoutHybridSearch:
    async def search(self, *args, **kwargs):
        raise TimeoutError("search timeout")


@pytest.mark.asyncio
async def test_graph_rag_timeout_maps_to_internal_error_shape() -> None:
    query = GraphRAGQuery(query="q")
    with pytest.raises(HTTPException) as exc:
        await query_search.graph_rag_query_impl(query, _TimeoutGraphRag())

    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "INTERNAL_ERROR"
    assert exc.value.detail["context"]["operation"] == "graph_rag_query"


@pytest.mark.asyncio
async def test_hybrid_search_timeout_maps_to_internal_error_shape() -> None:
    request = SearchRequest(query="q", search_type=SearchType.HYBRID)
    with pytest.raises(HTTPException) as exc:
        await query_search.hybrid_search_impl(request, _TimeoutHybridSearch())

    assert exc.value.status_code == 500
    assert exc.value.detail["code"] == "INTERNAL_ERROR"
    assert exc.value.detail["context"]["operation"] == "hybrid_search"


@pytest.mark.asyncio
async def test_metrics_route_returns_stable_error_shape() -> None:
    class _BrokenMetrics:
        def get_metrics(self) -> str:
            raise RuntimeError("boom")

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(metrics=_BrokenMetrics())))
    response = await system.get_metrics(request)

    assert response.status_code == 500
    assert response.media_type == "application/json"
    assert "METRICS_EXPORT_ERROR" in response.body.decode("utf-8")
