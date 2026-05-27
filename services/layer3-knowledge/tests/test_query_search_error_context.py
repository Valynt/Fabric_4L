from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from value_fabric.layer3.api.exceptions import SearchError
from value_fabric.layer3.api.models import GraphRAGQuery, SearchRequest
from value_fabric.layer3.api.routes import query_search
from value_fabric.shared.identity import RequestContext


class _FailingGraphRag:
    async def query(self, **kwargs):
        raise SearchError("backend unavailable")


class _FailingHybridSearch:
    async def search(self, *args, **kwargs):
        raise SearchError("backend unavailable")


class _RuntimeFailingGraphRag:
    async def query(self, **kwargs):
        raise RuntimeError("unexpected crash")


@pytest.mark.asyncio
async def test_graph_rag_maps_error_with_tenant_and_correlation_context(caplog):
    ctx = RequestContext(tenant_id="tenant-abc", request_id="ctx-rid")
    request = SimpleNamespace(state=SimpleNamespace(trace_id="trace-123", correlation_id="corr-999"))
    query = GraphRAGQuery(query="foo")

    with pytest.raises(HTTPException) as exc_info:
        await query_search.graph_rag_query_impl(query, _FailingGraphRag(), ctx=ctx, request=request)

    detail = exc_info.value.detail
    assert detail["context"]["tenant"] == "tenant-abc"
    assert detail["context"]["request_id"] == "trace-123"
    assert detail["context"]["correlation_id"] == "trace-123"
    assert "backend unavailable" not in str(detail)

    assert any(
        getattr(record, "context", {}).get("tenant") == "tenant-abc"
        and getattr(record, "context", {}).get("request_id") == "trace-123"
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_hybrid_search_uses_context_request_id_fallback_when_http_trace_missing(caplog):
    ctx = RequestContext(tenant_id="tenant-fallback", request_id="ctx-request-22")
    request = SimpleNamespace(state=SimpleNamespace())
    payload = SearchRequest(query="bar")

    with pytest.raises(HTTPException) as exc_info:
        await query_search.hybrid_search_impl(payload, _FailingHybridSearch(), ctx=ctx, http_request=request)

    detail = exc_info.value.detail
    assert detail["context"]["tenant"] == "tenant-fallback"
    assert detail["context"]["request_id"] == "ctx-request-22"
    assert detail["context"]["correlation_id"] == "ctx-request-22"

    assert any(
        getattr(record, "context", {}).get("correlation_id") == "ctx-request-22"
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_graph_rag_runtime_error_returns_safe_500_and_logs_context(caplog):
    ctx = RequestContext(tenant_id="tenant-z", request_id="req-z")
    request = SimpleNamespace(state=SimpleNamespace(trace_id="trace-z"))
    query = GraphRAGQuery(query="boom")

    with pytest.raises(HTTPException) as exc_info:
        await query_search.graph_rag_query_impl(query, _RuntimeFailingGraphRag(), ctx=ctx, request=request)

    detail = exc_info.value.detail
    assert exc_info.value.status_code == 500
    assert detail["code"] == "INTERNAL_ERROR"
    assert "unexpected crash" not in str(detail)
    assert any(
        getattr(record, "context", {}).get("tenant") == "tenant-z"
        and getattr(record, "context", {}).get("request_id") == "trace-z"
        for record in caplog.records
    )
