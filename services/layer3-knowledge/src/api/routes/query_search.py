"""Graph query/search route helpers.

Implements GraphRAG query, streaming GraphRAG, and hybrid search execution.
Compatibility aliases for legacy paths are in ``routes/compat_aliases.py``.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError as PydanticValidationError
from value_fabric.shared.identity import RequestContext

from ...api.cache import get_request_deduplicator
from ...api.exception_mapping import map_exception_to_http_error
from ...api.exceptions import SearchError, VectorStoreError
from ...api.models import (
    GraphRAGQuery,
    GraphRAGResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
)

logger = logging.getLogger(__name__)


def _build_error_context(*, tenant_id: str | None, endpoint: str, operation: str, request_id: str | None) -> dict[str, str]:
    context: dict[str, str] = {
        "tenant": str(tenant_id) if tenant_id else "unknown",
        "endpoint": endpoint,
        "operation": operation,
    }
    if request_id:
        context["request_id"] = request_id
        context["correlation_id"] = request_id
    return context


def _request_id_from_context(request: Request | None, ctx: RequestContext | None) -> str | None:
    if request:
        request_id = getattr(request.state, "trace_id", None) or getattr(request.state, "correlation_id", None)
        if request_id:
            return request_id
    if ctx:
        return ctx.request_id
    return None


async def _execute_graph_rag_query(
    graph_rag: Any,
    query_text: str,
    entity_type: str | None,
    max_hops: int,
    max_results: int,
    tenant_id: str,
) -> GraphRAGResponse:
    start_time = time.time()
    result = await graph_rag.query(
        query_text=query_text,
        entity_type=entity_type,
        max_hops=max_hops,
        max_results=max_results,
        tenant_id=tenant_id,
    )
    processing_time = (time.time() - start_time) * 1000
    if isinstance(result, dict):
        query_value = result.get("query", query_text)
        entities = result.get("entities", [])
        relationships = result.get("relationships", [])
        context_graph = result.get("context_graph", {})
        confidence_score = result.get("confidence_score", 0.0)
        sources = result.get("sources", [])
        answer = result.get("answer")
    else:
        query_value = result.query
        entities = result.entities
        relationships = result.relationships
        context_graph = result.context_graph
        confidence_score = result.confidence_score
        sources = result.sources
        answer = getattr(result, "answer", None)
    return GraphRAGResponse.model_validate({
        "query": query_value,
        "entities": entities,
        "relationships": relationships,
        "context_graph": context_graph,
        "confidence_score": confidence_score,
        "sources": sources,
        "processing_time_ms": processing_time,
        "answer": answer,
    })


async def graph_rag_query_impl(
    query: GraphRAGQuery,
    graph_rag: Any,
    *,
    ctx: RequestContext | None = None,
    request: Request | None = None,
) -> GraphRAGResponse:
    try:
        if not (ctx and ctx.tenant_id):
            raise ValueError("tenant context required for graph_rag_query")
        deduplicator = get_request_deduplicator()
        if deduplicator:
            params = {
                "query": query.query,
                "entity_type": query.entity_type,
                "max_hops": query.max_hops,
                "max_results": query.max_results,
            }
            response = await deduplicator.execute(
                operation="graph_rag_query",
                params=params,
                executor=_execute_graph_rag_query,
                ttl=60,
                graph_rag=graph_rag,
                query_text=query.query,
                entity_type=query.entity_type,
                max_hops=query.max_hops,
                max_results=query.max_results,
                tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else "",
            )
            logger.info("GraphRAG query completed", extra={"context": _build_error_context(tenant_id=str(ctx.tenant_id), endpoint="/v1/query", operation="graph_rag_query", request_id=_request_id_from_context(request, ctx))})
            return response
        response = await _execute_graph_rag_query(
            graph_rag, query.query, query.entity_type, query.max_hops, query.max_results, str(ctx.tenant_id) if ctx and ctx.tenant_id else ""
        )
        logger.info("GraphRAG query completed", extra={"context": _build_error_context(tenant_id=str(ctx.tenant_id), endpoint="/v1/query", operation="graph_rag_query", request_id=_request_id_from_context(request, ctx))})
        return response
    except (SearchError, VectorStoreError) as exc:
        context = _build_error_context(
            tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
            endpoint="/v1/query",
            operation="graph_rag_query",
            request_id=_request_id_from_context(request, ctx),
        )
        logger.warning("GraphRAG query mapped exception", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except (PydanticValidationError, ValueError, TypeError) as exc:
        context = _build_error_context(
            tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
            endpoint="/v1/query",
            operation="graph_rag_query",
            request_id=_request_id_from_context(request, ctx),
        )
        context["error_code"] = "VALIDATION_ERROR"
        logger.warning("GraphRAG query validation failed", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except TimeoutError as exc:
        context = _build_error_context(
            tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
            endpoint="/v1/query",
            operation="graph_rag_query",
            request_id=_request_id_from_context(request, ctx),
        )
        context["error_code"] = "UPSTREAM_TIMEOUT"
        logger.error("GraphRAG query timed out", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except Exception as exc:
        context = _build_error_context(
            tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
            endpoint="/v1/query",
            operation="graph_rag_query",
            request_id=_request_id_from_context(request, ctx),
        )
        logger.error("GraphRAG query failed", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)


async def graph_rag_query_stream_impl(
    query: GraphRAGQuery,
    graph_rag: Any,
    *,
    ctx: RequestContext | None = None,
) -> StreamingResponse:
    async def event_generator() -> Any:
        try:
            if not (ctx and ctx.tenant_id):
                raise ValueError("tenant context required for graph_rag_query_stream")
            async for event in graph_rag.query_stream(
                query_text=query.query,
                entity_type=query.entity_type,
                max_hops=query.max_hops,
                max_results=query.max_results,
                tenant_id=str(ctx.tenant_id),
            ):
                event_data = {
                    "event_type": event["event_type"],
                    "data": event["data"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "progress_percent": event.get("progress_percent", 0.0),
                }
                yield f"data: {json.dumps(event_data)}\\n\\n"
        except (TimeoutError, RuntimeError, ValueError, TypeError) as exc:
            logger.error("Streaming GraphRAG query failed", extra={"context": {"tenant": str(ctx.tenant_id) if ctx and ctx.tenant_id else "unknown", "endpoint": "/v1/query/stream", "operation": "graph_rag_query_stream", "error_type": exc.__class__.__name__}}, exc_info=True)
            trace_id = None
            if isinstance(exc, Exception):
                trace_id = getattr(exc, "trace_id", None) or getattr(exc, "correlation_id", None)
            error_event = {
                "event_type": "error",
                "data": {"message": "Streaming query failed"},
                "timestamp": datetime.utcnow().isoformat(),
                "progress_percent": 100.0,
            }
            if trace_id:
                error_event["data"]["trace_id"] = trace_id
            yield f"data: {json.dumps(error_event)}\\n\\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


async def _execute_hybrid_search(
    hybrid_search: Any,
    query: str,
    entity_type: str | None,
    search_type: SearchType | str,
    top_k: int,
    weights: dict | None,
    tenant_id: str,
) -> SearchResponse:
    start_time = time.time()
    search_type_value = search_type.value if isinstance(search_type, SearchType) else search_type
    if search_type_value == "vector":
        results = await hybrid_search.semantic_search(query, entity_type, top_k, tenant_id=tenant_id)
    elif search_type_value == "fulltext":
        results = await hybrid_search.fulltext_search(query, entity_type, top_k, tenant_id=tenant_id)
    else:
        results = await hybrid_search.search(query, [entity_type] if entity_type else None, top_k, weights, tenant_id=tenant_id)
    search_results = [SearchResult(**asdict(result)) for result in results]
    return SearchResponse.model_validate({
        "query": query,
        "results": search_results,
        "total_results": len(search_results),
        "search_type": SearchType(search_type_value),
        "processing_time_ms": (time.time() - start_time) * 1000,
    })


async def hybrid_search_impl(
    request: SearchRequest,
    hybrid_search: Any,
    *,
    ctx: RequestContext | None = None,
    http_request: Request | None = None,
) -> SearchResponse:
    try:
        if not (ctx and ctx.tenant_id):
            raise ValueError("tenant context required for hybrid_search")
        deduplicator = get_request_deduplicator()
        if deduplicator:
            params = {
                "query": request.query,
                "entity_type": request.entity_type,
                "search_type": request.search_type,
                "top_k": request.top_k,
                "weights": request.weights,
            }
            response = await deduplicator.execute(
                operation="hybrid_search",
                params=params,
                executor=_execute_hybrid_search,
                ttl=30,
                hybrid_search=hybrid_search,
                query=request.query,
                entity_type=request.entity_type,
                search_type=request.search_type,
                top_k=request.top_k,
                weights=request.weights,
                tenant_id=str(ctx.tenant_id),
            )
            logger.info("Hybrid search completed", extra={"context": _build_error_context(tenant_id=str(ctx.tenant_id), endpoint="/v1/search", operation="hybrid_search", request_id=_request_id_from_context(http_request, ctx))})
            return response
        response = await _execute_hybrid_search(
            hybrid_search,
            request.query,
            request.entity_type,
            request.search_type,
            request.top_k,
            request.weights,
            str(ctx.tenant_id),
        )
        logger.info("Hybrid search completed", extra={"context": _build_error_context(tenant_id=str(ctx.tenant_id), endpoint="/v1/search", operation="hybrid_search", request_id=_request_id_from_context(http_request, ctx))})
        return response
    except (SearchError, VectorStoreError) as exc:
        context = _build_error_context(
            tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
            endpoint="/v1/search",
            operation="hybrid_search",
            request_id=_request_id_from_context(http_request, ctx),
        )
        logger.warning("Search mapped exception", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except (PydanticValidationError, ValueError, TypeError) as exc:
        context = _build_error_context(
            tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
            endpoint="/v1/search",
            operation="hybrid_search",
            request_id=_request_id_from_context(http_request, ctx),
        )
        context["error_code"] = "VALIDATION_ERROR"
        logger.warning("Search validation failed", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except TimeoutError as exc:
        context = _build_error_context(
            tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
            endpoint="/v1/search",
            operation="hybrid_search",
            request_id=_request_id_from_context(http_request, ctx),
        )
        context["error_code"] = "UPSTREAM_TIMEOUT"
        logger.error("Search timed out", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
    except Exception as exc:
        context = _build_error_context(
            tenant_id=str(ctx.tenant_id) if ctx and ctx.tenant_id else None,
            endpoint="/v1/search",
            operation="hybrid_search",
            request_id=_request_id_from_context(http_request, ctx),
        )
        logger.error("Search failed", extra={"context": context}, exc_info=True)
        raise map_exception_to_http_error(exc, context=context)
