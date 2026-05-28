from __future__ import annotations

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Compatibility alias endpoints delegating to canonical route implementations.
"""


from fastapi import APIRouter, Depends, HTTPException, Request
from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError
from value_fabric.shared.identity import RequestContext, require_authenticated

from ...api.dependencies import get_graph_rag, get_hybrid_search
from ...api.models import GraphRAGQuery, GraphRAGResponse, SearchRequest, SearchResponse
from ...services.compat_metrics import (
    record_deprecated_legacy_field_usage,
    record_deprecated_route_hit,
)
from . import query_search

router = APIRouter(prefix="/v1", tags=["compatibility"], dependencies=[Depends(require_authenticated)])


def _app_client(request: Request) -> str:
    return request.headers.get("x-app-client", "unknown")


def _assert_legacy_alias_enabled(request: Request, alias_name: str) -> None:
    phase = getattr(request.app.state, "layer3_compat_deprecation_phase", "warning_only")
    if phase == "disable_non_prod":
        env = getattr(request.app.state, "environment", "dev")
        if env.lower() != "prod":
            raise ServiceUnavailableError(message=f"Legacy alias '{alias_name}' disabled in non-production")
    elif phase == "removed":
        raise ServiceUnavailableError(message=f"Legacy alias '{alias_name}' has been removed")


def _record_route_hit(request: Request, route: str, tenant_id: str) -> None:
    record_deprecated_route_hit(route, tenant_id=tenant_id, app_client=_app_client(request))


@router.post("/graphrag", response_model=GraphRAGResponse, deprecated=True)
async def graph_rag_legacy_alias(
    query: GraphRAGQuery,
    request: Request,
    graph_rag=Depends(get_graph_rag),
    ctx: RequestContext = Depends(require_authenticated),
):
    _assert_legacy_alias_enabled(request, "/v1/graphrag")
    _record_route_hit(request, "/v1/graphrag", tenant_id=str(ctx.tenant_id))
    return await query_search.graph_rag_query_impl(query, graph_rag, ctx=ctx, request=request)


@router.post("/query/graph", response_model=GraphRAGResponse, deprecated=True)
async def graph_rag_query_aliases(
    query: GraphRAGQuery,
    request: Request,
    graph_rag=Depends(get_graph_rag),
    ctx: RequestContext = Depends(require_authenticated),
):
    route = request.url.path
    _assert_legacy_alias_enabled(request, route)
    _record_route_hit(request, route, tenant_id=str(ctx.tenant_id))
    return await query_search.graph_rag_query_impl(query, graph_rag, ctx=ctx, request=request)


@router.post("/query/graph/stream", deprecated=True)
async def graph_rag_query_stream_alias(
    query: GraphRAGQuery,
    request: Request,
    graph_rag=Depends(get_graph_rag),
    ctx: RequestContext = Depends(require_authenticated),
):
    _assert_legacy_alias_enabled(request, "/v1/query/graph/stream")
    _record_route_hit(request, "/v1/query/graph/stream", tenant_id=str(ctx.tenant_id))
    return await query_search.graph_rag_query_stream_impl(query, graph_rag, ctx=ctx)


@router.post("/search/hybrid", response_model=SearchResponse, deprecated=True)
@router.post("/search", response_model=SearchResponse, deprecated=True)
@router.post("/query/search", response_model=SearchResponse, deprecated=True)
async def hybrid_search_aliases(
    request: SearchRequest,
    http_request: Request,
    hybrid_search=Depends(get_hybrid_search),
    ctx: RequestContext = Depends(require_authenticated),
):
    app_client = _app_client(http_request)
    route = http_request.url.path
    _assert_legacy_alias_enabled(http_request, route)
    record_deprecated_route_hit(route, tenant_id=str(ctx.tenant_id), app_client=app_client)
    if request.search_type.value == "fulltext":
        record_deprecated_legacy_field_usage(
            "search_type=fulltext", tenant_id=str(ctx.tenant_id), app_client=app_client
        )
    return await query_search.hybrid_search_impl(request, hybrid_search, ctx=ctx, http_request=http_request)
