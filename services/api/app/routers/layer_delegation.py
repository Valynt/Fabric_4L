"""Thin gateway delegation to owning layer services.

Decision D1 (docs/architecture/source-of-truth-ratification.md): the browser
talks only to the gateway. The frontend's per-layer route segments
(``/v1/agents/*``, ``/v1/ingest/*``, ``/v1/extract/*``, ``/v1/graph/*``,
``/v1/truths/*``) are an internal client convention; this router makes that
convention true by delegating to the owning layer with the caller's verified
identity. The gateway adds no business logic here: authentication, tenant
resolution, and authorization are re-verified by the owning layer's own
governance middleware (defense in depth, fail-closed).

Registered LAST in main.py so product-domain routers (accounts, hypotheses,
agents/workflows, benchmarks, …) keep precedence; delegation only serves
paths no product router owns. ``/v1/benchmarks/*`` is intentionally absent:
it is owned by ``routers/benchmarks.py`` with a typed Layer 6 client.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import parse_qs

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.security import TokenPayload, require_authenticated

router = APIRouter(tags=["layer-delegation"])

# segment -> (settings attribute for base URL, owning-layer path prefix).
#
# The prefix must match the frontend path convention for the segment,
# inherited from the previous dev-proxy topology:
# - l3/l4 hooks embed the owning layer's version prefix themselves
#   (e.g. apiGet('l3', '/v1/calculators/...'), apiPatch('l4', '/v1/evidence/...'))
#   so the subpath IS the layer-relative path: no added prefix.
# - l1/l5 hooks pass bare resource paths ('/jobs', '/academy/pillars'),
#   so the delegation adds the owning layer's canonical mount prefix.
# This table is the single place where that convention lives.
DELEGATION_TARGETS: dict[str, tuple[str, str]] = {
    "agents": ("layer4_api_base_url", ""),
    "ingest": ("layer1_api_base_url", "/api/v1/ingestion"),
    "extract": ("layer2_api_base_url", "/v1"),
    "graph": ("layer3_api_base_url", ""),
    "truths": ("layer5_api_base_url", "/api/v1"),
}

_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)

# Headers the caller may supply that carry verified identity — forwarded
# verbatim so the owning layer re-verifies the same principal.
_FORWARDED_REQUEST_HEADERS = frozenset(
    {
        "authorization",
        "x-organization-id",
        "x-org-id",
        "x-user-id",
        "x-role",
        "x-request-id",
        "x-correlation-id",
        "x-trace-id",
        "x-validation-run-id",
        "x-service-auth",
        "content-type",
        "accept",
        "idempotency-key",
    }
)

_DELEGATION_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def _target_url(segment: str, path: str) -> str:
    settings = get_settings()
    attr, prefix = DELEGATION_TARGETS[segment]
    base = getattr(settings, attr).rstrip("/")
    suffix = f"/{path}" if path else ""
    return f"{base}{prefix}{suffix}"


def _request_headers(request: Request, tenant_id: str) -> dict[str, str]:
    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() in _FORWARDED_REQUEST_HEADERS
    }
    headers["X-Tenant-ID"] = tenant_id
    return headers


async def _delegate(
    request: Request, segment: str, path: str, tenant_id: str
) -> Response:
    settings = get_settings()
    url = _target_url(segment, path)
    body = await request.body()
    try:
        _qp = request.scope.get("query_string", b"")
        query = {k: v[-1] for k, v in parse_qs(_qp.decode()).items()} if _qp else {}
        async with httpx.AsyncClient(
            timeout=settings.delegation_timeout_seconds,
            follow_redirects=False,
        ) as client:
            upstream = await client.request(
                request.method,
                url,
                params=query,
                content=body if body else None,
                headers=_request_headers(request, tenant_id),
            )
    except httpx.HTTPError:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "owning_layer_unavailable",
                "segment": segment,
            },
        )

    response_headers = {
        name: value
        for name, value in upstream.headers.items()
        if name.lower() not in _HOP_BY_HOP
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


def _make_handler(segment: str) -> Callable[..., Awaitable[Response]]:
    async def handler(
        request: Request,
        path: str = "",
        auth: TokenPayload = Depends(require_authenticated),
    ) -> Response:
        return await _delegate(request, segment, path, auth.tenant_id)

    return handler


for _segment in DELEGATION_TARGETS:
    router.add_api_route(
        f"/{_segment}/{{path:path}}",
        _make_handler(_segment),
        methods=_DELEGATION_METHODS,
        name=f"delegate_{_segment}",
        include_in_schema=False,
    )
    router.add_api_route(
        f"/{_segment}",
        _make_handler(_segment),
        methods=_DELEGATION_METHODS,
        name=f"delegate_{_segment}_root",
        include_in_schema=False,
    )


__all__ = ["router", "DELEGATION_TARGETS"]
