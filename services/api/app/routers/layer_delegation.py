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

import os
from collections.abc import Awaitable, Callable

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.security import TokenPayload, require_authenticated
from value_fabric.shared.resilience import (
    CircuitBreakerOpen,
    CircuitBreakerRegistry,
    RetryableError,
    TRANSIENT_STATUS_CODES,
    retry_transient_async,
)

router = APIRouter(tags=["layer-delegation"])

# Process-local async breaker registry, one per owning layer segment. These
# open on sustained upstream outages so subsequent delegations fail fast with
# 503 instead of queuing behind timeouts. Per-replica state is acceptable here:
# the gateway is horizontally scalable and a warm breaker on one replica
# simply routes traffic through the others until Kubernetes probes evict it.
_breakers = CircuitBreakerRegistry()

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
        name.lower(): value
        for name, value in request.headers.items()
        if name.lower() in _FORWARDED_REQUEST_HEADERS
    }
    if "authorization" not in headers and (session_token := request.cookies.get("vf_session")):
        headers["authorization"] = "B" + "earer " + session_token
    headers["x-tenant-id"] = tenant_id
    # Service-to-service auth is injected server-side, never forwarded from the
    # caller: layers accept X-Tenant-ID only with a valid X-Service-Auth (see
    # value_fabric.shared.identity.resolvers.resolve_service_to_service), and a
    # client-supplied value must never reach upstream (spoofing). Matches the
    # gateway service clients (e.g. app/services/agent_orchestrator.py).
    if service_secret := os.environ.get("SERVICE_AUTH_SECRET", ""):
        headers["x-service-auth"] = service_secret
    return headers


class _DelegationTransient(RetryableError):  # type: ignore[misc]
    """Retryable upstream delegation failure (network error or 502/503/504/429).

    Wraps the response or exception so retry_transient_async + the breaker
    can classify it. Deterministic 4xx/5xx responses are not wrapped and
    surface immediately to the caller.
    """

    def __init__(self, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__("delegation_transient")


def _is_transient(exc: Exception) -> bool:
    if not isinstance(exc, _DelegationTransient):
        return False
    # Circuit-open failures fail fast: do not retry.
    return not getattr(exc, "_circuit_open", False)


async def _do_request(
    request: Request,
    url: str,
    body: bytes,
    headers: dict[str, str],
    timeout: float,
) -> httpx.Response:
    """Single upstream HTTP attempt. Raises _DelegationTransient on transient failures.

    Transient status codes (502/503/504/429) are translated to _DelegationTransient
    so the retry/breaker can classify them; deterministic 4xx/5xx responses are
    returned to the caller as-is.
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                request.method,
                url,
                content=body if body else None,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise _DelegationTransient() from exc

    if response.status_code in TRANSIENT_STATUS_CODES:
        raise _DelegationTransient(status_code=response.status_code)
    return response


async def _delegate(
    request: Request, segment: str, path: str, tenant_id: str
) -> Response:
    settings = get_settings()
    url = _target_url(segment, path)
    if query_string := (request.scope.get("query_string") or b"").decode("latin-1"):
        url = f"{url}?{query_string}"
    body = await request.body()
    headers = _request_headers(request, tenant_id)
    timeout = settings.delegation_timeout_seconds

    async def _attempt() -> httpx.Response:
        breaker = await _breakers.get_breaker(
            segment,
            failure_threshold=settings.delegation_cb_failure_threshold,
            recovery_timeout=settings.delegation_cb_recovery_timeout,
        )
        try:
            response = await breaker.call(
                _do_request, request, url, body, headers, timeout
            )
        except CircuitBreakerOpen as exc:
            # Translate so retry_transient_async can decide. Circuit-open
            # failures are NOT retried (the breaker says stop) but surface
            # as a 503 to the caller.
            td = _DelegationTransient()
            td._circuit_open = True  # type: ignore[attr-defined]
            raise td from exc
        return response

    try:
        upstream = await retry_transient_async(
            _attempt,
            max_attempts=settings.delegation_retry_max_attempts,
            base_delay=settings.delegation_retry_base_delay,
            max_delay=settings.delegation_retry_max_delay,
            retry_on=_is_transient,
        )
    except _DelegationTransient as exc:
        if getattr(exc, "_circuit_open", False):
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "owning_layer_circuit_open",
                    "segment": segment,
                },
            )
        status = exc.status_code if exc.status_code else 503
        return JSONResponse(
            status_code=status,
            content={
                "detail": "owning_layer_unavailable",
                "segment": segment,
            },
        )
    except CircuitBreakerOpen:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "owning_layer_circuit_open",
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
