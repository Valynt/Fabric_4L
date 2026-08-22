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

import asyncio
import logging
import os
import time
from collections.abc import Awaitable, Callable

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.metrics import (
    DELEGATION_CACHE_TOTAL,
    DELEGATION_CIRCUIT_OPEN_TOTAL,
    DELEGATION_LATENCY_SECONDS,
    DELEGATION_REQUESTS_TOTAL,
    DELEGATION_RETRY_TOTAL,
)
from app.core.security import TokenPayload, require_authenticated
from value_fabric.shared.resilience import (
    CircuitBreakerOpen,
    CircuitBreakerRegistry,
    RetryableError,
    TRANSIENT_STATUS_CODES,
    retry_transient_async,
)

logger = logging.getLogger("fabric.delegation")

router = APIRouter(tags=["layer-delegation"])

# Process-local async breaker registry, one per owning layer segment. These
# open on sustained upstream outages so subsequent delegations fail fast with
# 503 instead of queuing behind timeouts. Per-replica state is acceptable here:
# the gateway is horizontally scalable and a warm breaker on one replica
# simply routes traffic through the others until Kubernetes probes evict it.
_breakers = CircuitBreakerRegistry()

# Cap on in-flight delegations per replica. Without this, a slow upstream
# (e.g. L4 LangGraph workflow) can exhaust the async event loop's connection
# pool and starve other handlers. Acquired around each upstream attempt;
# when exhausted, new delegations fail fast with 503 rather than queuing.
# Tuned via DELEGATION_MAX_CONCURRENCY (default 64 — well above the typical
# per-replica worker count but low enough to protect the connection pool).
#
# Lazily created per event loop: a module-level asyncio.Semaphore created at
# import time binds to whatever loop is active then, which breaks under
# pytest-asyncio's per-test loops. _get_semaphore() resolves the loop-bound
# instance on first use so it always matches the running loop.
import asyncio
import weakref

_DELEGATION_MAX_CONCURRENCY = int(os.environ.get("DELEGATION_MAX_CONCURRENCY", "64"))
_semaphore_cache: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _get_semaphore() -> asyncio.Semaphore:
    """Return a loop-bound semaphore for the currently running event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    sem = _semaphore_cache.get(loop)
    if sem is None:
        sem = asyncio.Semaphore(_DELEGATION_MAX_CONCURRENCY)
        _semaphore_cache[loop] = sem
    return sem


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
    if "authorization" not in headers and (
        session_token := request.cookies.get("vf_session")
    ):
        headers["authorization"] = "B" + "earer " + session_token
    headers["x-tenant-id"] = tenant_id
    # Service-to-service auth is injected server-side, never forwarded from the
    # caller: layers accept X-Tenant-ID only with a valid X-Service-Auth (see
    # value_fabric.shared.identity.resolvers.resolve_service_to_service), and a
    # client-supplied value must never reach upstream (spoofing). Matches the
    # gateway service clients (e.g. app/services/agent_orchestrator.py).
    if service_secret := os.environ.get("SERVICE_AUTH_SECRET", ""):
        headers["x-service-auth"] = service_secret
    # Propagate the active OTel trace context so downstream layers see the same
    # trace and their spans are correlated with the gateway's. No-op when OTel
    # is not installed or no span is active.
    from value_fabric.shared.observability.http_trace_propagation import (
        merge_trace_headers,
    )

    merge_trace_headers(headers)
    return headers


class _DelegationTransient(RetryableError):
    """Retryable upstream delegation failure (network error or 502/503/504/429).

    Wraps the response or exception so retry_transient_async + the breaker
    can classify it. Deterministic 4xx/5xx responses are not wrapped and
    surface immediately to the caller.
    """

    concurrency_exhausted: bool = False
    circuit_open: bool = False

    def __init__(
        self,
        status_code: int | None = None,
        headers: httpx.Headers | dict[str, str] | None = None,
        content: bytes | None = None,
        concurrency_exhausted: bool = False,
        circuit_open: bool = False,
    ) -> None:
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.concurrency_exhausted = concurrency_exhausted
        self.circuit_open = circuit_open
        super().__init__("delegation_transient")


def _is_transient(exc: Exception) -> bool:
    if not isinstance(exc, _DelegationTransient):
        return False
    # Circuit-open and concurrency-exhausted failures fail fast: do not retry.
    if exc.circuit_open or exc.concurrency_exhausted:
        return False
    return True


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
        raise _DelegationTransient(
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
        )
    return response


# --- GET response cache -----------------------------------------------------
# Short-TTL Redis cache for safe GET delegations. Caches per (tenant, user,
# segment, path, query) so one tenant/user cannot read another's cached
# response. Fail-open: any Redis error is skipped (the request still goes
# upstream). Mutations (POST/PUT/PATCH/DELETE) bypass the cache entirely.
_DELEGATION_CACHE_TTL = int(os.environ.get("DELEGATION_CACHE_TTL_SECONDS", "30"))


def _cache_key(
    segment: str, path: str, tenant_id: str, user_id: str | None, query_string: str
) -> str:
    """Build a tenant+user scoped Redis key for a GET delegation."""
    import hashlib

    digest = hashlib.sha256(
        f"{user_id or ''}|{path}|{query_string}".encode()
    ).hexdigest()
    return f"delegation:get:{tenant_id}:{segment}:{digest}"


def _sync_cache_lookup(key: str) -> tuple[int, bytes, str] | None:
    """Return (status, body, content_type) from cache, or None on miss/unavailable."""
    from app.core.redis_client import get_redis_client

    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception as exc:  # noqa: BLE001 — fail open
        logger.debug("delegation cache lookup failed: %s", exc)
        return None
    if not raw:
        return None
    parts = raw.split("\r", 2)
    if len(parts) != 3:
        return None
    status = int(parts[0])
    content_type = parts[1]
    body = parts[2].encode("latin-1")
    return status, body, content_type


async def _cache_lookup(key: str) -> tuple[int, bytes, str] | None:
    """Non-blocking cache lookup offloaded to worker thread."""
    return await asyncio.to_thread(_sync_cache_lookup, key)


def _sync_cache_store(key: str, status: int, body: bytes, content_type: str) -> bool:
    """Store a GET response in cache with the configured TTL.

    Returns True if stored, False if Redis was unavailable or the write failed.
    """
    from app.core.redis_client import get_redis_client

    client = get_redis_client()
    if client is None:
        return False
    payload = f"{status}\r{content_type}\r{body.decode('latin-1')}"
    try:
        client.set(key, payload, ex=_DELEGATION_CACHE_TTL)
    except Exception as exc:  # noqa: BLE001 — fail open
        logger.debug("delegation cache store failed: %s", exc)
        return False
    return True


async def _cache_store(key: str, status: int, body: bytes, content_type: str) -> bool:
    """Non-blocking cache store offloaded to worker thread."""
    return await asyncio.to_thread(_sync_cache_store, key, status, body, content_type)


def _sync_cache_invalidate(tenant_id: str, segment: str) -> None:
    """Invalidate cached GET delegations for a tenant and segment after mutation."""
    from app.core.redis_client import get_redis_client

    client = get_redis_client()
    if client is None:
        return
    try:
        match_pattern = f"delegation:get:{tenant_id}:{segment}:*"
        keys = list(client.scan_iter(match=match_pattern, count=100))
        if keys:
            client.delete(*keys)
    except Exception as exc:  # noqa: BLE001 — fail open
        logger.debug("delegation cache invalidate failed: %s", exc)


async def _cache_invalidate(tenant_id: str, segment: str) -> None:
    """Non-blocking cache invalidation offloaded to worker thread."""
    await asyncio.to_thread(_sync_cache_invalidate, tenant_id, segment)


async def _delegate(
    request: Request,
    segment: str,
    path: str,
    tenant_id: str,
    user_id: str | None = None,
) -> Response:
    settings = get_settings()
    url = _target_url(segment, path)
    query_string = (request.scope.get("query_string") or b"").decode("latin-1")
    if query_string:
        url = f"{url}?{query_string}"
    body = await request.body()
    headers = _request_headers(request, tenant_id)
    if user_id:
        headers["x-user-id"] = user_id
    timeout = settings.delegation_timeout_seconds
    method = request.method.upper()
    request_id = headers.get("x-request-id") or headers.get("x-trace-id")
    effective_user_id = user_id or headers.get("x-user-id")

    _start = time.perf_counter()
    _retries = 0

    def _record(outcome: str, status_code: int | str) -> None:
        duration = time.perf_counter() - _start
        DELEGATION_REQUESTS_TOTAL.labels(
            segment=segment,
            method=method,
            status_code=str(status_code),
            outcome=outcome,
        ).inc()
        DELEGATION_LATENCY_SECONDS.labels(segment=segment, method=method).observe(
            duration
        )
        if _retries:
            DELEGATION_RETRY_TOTAL.labels(segment=segment).inc(_retries)
        logger.info(
            "delegation",
            extra={
                "segment": segment,
                "method": method,
                "path": path,
                "status_code": status_code,
                "outcome": outcome,
                "duration_ms": round(duration * 1000, 2),
                "retries": _retries,
                "request_id": request_id,
                "tenant_id": tenant_id,
                "user_id": effective_user_id,
            },
        )

    # GET cache: serve from Redis on a hit. Only safe GETs with no body are
    # eligible; mutations and non-GET methods bypass the cache.
    cache_key: str | None = None
    if method == "GET" and not body:
        cache_key = _cache_key(
            segment, path, tenant_id, effective_user_id, query_string
        )
        cached = await _cache_lookup(cache_key)
        if cached is not None:
            DELEGATION_CACHE_TOTAL.labels(segment=segment, outcome="hit").inc()
            status, cached_body, content_type = cached
            _record("cache_hit", status)
            return Response(
                content=cached_body,
                status_code=status,
                headers={"x-delegation-cache": "hit"},
                media_type=content_type or None,
            )
        DELEGATION_CACHE_TOTAL.labels(segment=segment, outcome="miss").inc()
    elif method == "GET":
        DELEGATION_CACHE_TOTAL.labels(segment=segment, outcome="skip").inc()

    class _RetryCounter:
        """Captures retry attempts for metrics without coupling to the retry helper internals."""

        def __init__(self) -> None:
            self.count = 0

        async def before_attempt(self) -> None:
            if self.count > 0:
                nonlocal _retries
                _retries = self.count
            self.count += 1

    counter = _RetryCounter()

    async def _attempt() -> httpx.Response:
        await counter.before_attempt()
        breaker = await _breakers.get_breaker(
            segment,
            failure_threshold=settings.delegation_cb_failure_threshold,
            recovery_timeout=settings.delegation_cb_recovery_timeout,
        )
        # Backpressure: cap concurrent upstream calls per replica so a slow
        # upstream cannot exhaust the connection pool. Fails fast with a
        # transient error (retried once, then 503) if the semaphore is
        # exhausted — better to reject early than to queue indefinitely.
        semaphore = _get_semaphore()
        if semaphore.locked():
            raise _DelegationTransient(status_code=503, concurrency_exhausted=True)
        await semaphore.acquire()
        try:
            response = await breaker.call(
                _do_request, request, url, body, headers, timeout
            )
        except CircuitBreakerOpen as exc:
            # Translate so retry_transient_async can decide. Circuit-open
            # failures are NOT retried (the breaker says stop) but surface
            # as a 503 to the caller.
            raise _DelegationTransient(circuit_open=True) from exc
        finally:
            semaphore.release()
        return response

    # Restrict automatic retries to idempotent requests (or explicit idempotency key)
    # to avoid duplicate writes on non-idempotent mutations (e.g. POST, PATCH).
    is_idempotent = method in {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"} or bool(
        request.headers.get("idempotency-key")
        or request.headers.get("x-idempotency-key")
    )
    max_attempts = settings.delegation_retry_max_attempts if is_idempotent else 1

    try:
        upstream = await retry_transient_async(
            _attempt,
            max_attempts=max_attempts,
            base_delay=settings.delegation_retry_base_delay,
            max_delay=settings.delegation_retry_max_delay,
            retry_on=_is_transient,
        )
    except _DelegationTransient as exc:
        if getattr(exc, "_circuit_open", False):
            DELEGATION_CIRCUIT_OPEN_TOTAL.labels(segment=segment).inc()
            _record("circuit_open", 503)
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "owning_layer_circuit_open",
                    "segment": segment,
                },
            )
        if getattr(exc, "_concurrency_exhausted", False):
            _record("concurrency_exhausted", 503)
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "gateway_concurrency_exhausted",
                    "segment": segment,
                },
            )
        status = exc.status_code if exc.status_code else 503
        _record("unavailable", status)
        if status == 429 and exc.headers:
            preserved_headers: dict[str, str] = {}
            for k, v in exc.headers.items():
                k_lower = k.lower()
                if k_lower in {"retry-after"} or k_lower.startswith("x-ratelimit-"):
                    preserved_headers[k] = v
            if exc.content:
                return Response(
                    content=exc.content,
                    status_code=429,
                    headers=preserved_headers,
                    media_type=exc.headers.get("content-type", "application/json"),
                )
            return JSONResponse(
                status_code=429,
                headers=preserved_headers,
                content={
                    "detail": "owning_layer_rate_limited",
                    "segment": segment,
                },
            )
        return JSONResponse(
            status_code=status,
            content={
                "detail": "owning_layer_unavailable",
                "segment": segment,
            },
        )
    except CircuitBreakerOpen:
        DELEGATION_CIRCUIT_OPEN_TOTAL.labels(segment=segment).inc()
        _record("circuit_open", 503)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "owning_layer_circuit_open",
                "segment": segment,
            },
        )

    _record("success", upstream.status_code)
    response_headers = {
        name: value
        for name, value in upstream.headers.items()
        if name.lower() not in _HOP_BY_HOP
    }
    # Store safe GET 2xx responses in the short-TTL cache for reuse.
    if cache_key is not None and 200 <= upstream.status_code < 300:
        if await _cache_store(
            cache_key,
            upstream.status_code,
            upstream.content,
            upstream.headers.get("content-type", "application/json"),
        ):
            response_headers["x-delegation-cache"] = "store"
    elif (
        method in {"POST", "PUT", "PATCH", "DELETE"}
        and 200 <= upstream.status_code < 300
    ):
        # Invalidate cached GET delegations for the tenant segment on mutation
        await _cache_invalidate(tenant_id, segment)

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
        return await _delegate(request, segment, path, auth.tenant_id, user_id=auth.sub)

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
