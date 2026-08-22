# Gateway Orchestration Reference

> Canonical reference for the API gateway's request orchestration, delegation,
> resilience, observability, and caching behavior. Read this before modifying
> `services/api/app/routers/layer_delegation.py`,
> `services/api/app/services/agent_orchestrator.py`, or the gateway's k8s
> scaling manifests.

## 1. Overview

The API gateway (`services/api/`) is the browser's sole entry point. It
authenticates the caller, resolves tenant context, and delegates to the owning
layer service. It adds no business logic for delegated paths — authentication,
tenant resolution, and authorization are re-verified by the owning layer's own
governance middleware (defense in depth, fail-closed).

Two delegation paths exist:

| Path | Router | Purpose |
|---|---|---|
| **L4 workflow orchestration** | `app/services/agent_orchestrator.py` | Run LangGraph workflows on Layer 4, poll run status, return structured results. Uses a sync `httpx.Client` with retry + circuit breaker. |
| **Generic layer delegation** | `app/routers/layer_delegation.py` | Thin reverse proxy for L1–L5 path segments (`/v1/agents/*`, `/v1/ingest/*`, `/v1/extract/*`, `/v1/graph/*`, `/v1/truths/*`). Async, with retry, circuit breaker, backpressure, and GET caching. |

## 2. Routing contract

### 2.1 Delegation targets

`DELEGATION_TARGETS` in `layer_delegation.py` maps a frontend route segment to
a `(settings_attr, path_prefix)` pair:

| Segment | Settings attr | Prefix added | Frontend convention |
|---|---|---|---|
| `agents` | `layer4_api_base_url` | _(none)_ | hooks embed `/v1/...` themselves |
| `ingest` | `layer1_api_base_url` | `/api/v1/ingestion` | hooks pass bare resource paths |
| `extract` | `layer2_api_base_url` | `/v1` | hooks pass bare resource paths |
| `graph` | `layer3_api_base_url` | _(none)_ | hooks embed `/v1/...` themselves |
| `truths` | `layer5_api_base_url` | `/api/v1` | hooks pass bare resource paths |

`/v1/benchmarks/*` is **not** delegated — it is owned by
`routers/benchmarks.py` with a typed Layer 6 client.

### 2.2 Router ordering

The delegation router is registered **last** in `main.py` so product-domain
routers (accounts, hypotheses, agents/workflows, benchmarks, …) keep precedence.
Delegation only serves paths no product router owns.

### 2.3 Production ingress

Production ingress **must** route all API traffic through the gateway service
(`api-gateway`). The legacy `layer-apis` Ingress in
`k8s/routing/nginx/ingress.yaml` that routed `/layer1`–`/layer6` directly to
each layer service has been removed — it bypassed the gateway's auth, tenant
context, rate limiting, audit logging, and SLA enforcement.

The `scripts/ci/k8s_routing_check.py` CI gate validates routing manifests and
rejects any overlay that re-introduces direct layer bypass.

## 3. Resilience

### 3.1 Retry

Both delegation paths retry transient failures (network errors and HTTP
502/503/504/429) with exponential backoff and jitter.

| Setting | Env var | Default |
|---|---|---|
| `delegation_retry_max_attempts` | `DELEGATION_RETRY_MAX_ATTEMPTS` | 3 |
| `delegation_retry_base_delay` | `DELEGATION_RETRY_BASE_DELAY` | 0.2 s |
| `delegation_retry_max_delay` | `DELEGATION_RETRY_MAX_DELAY` | 5.0 s |

Deterministic 4xx/5xx responses are **not** retried — they surface to the
caller immediately.

### 3.2 Circuit breaker

Each owning-layer segment has its own circuit breaker in a process-local
`CircuitBreakerRegistry`. A breaker opens after `delegation_cb_failure_threshold`
consecutive failures and stays open for `delegation_cb_recovery_timeout`
seconds before allowing a half-open probe.

| Setting | Env var | Default |
|---|---|---|
| `delegation_cb_failure_threshold` | `DELEGATION_CB_FAILURE_THRESHOLD` | 5 |
| `delegation_cb_recovery_timeout` | `DELEGATION_CB_RECOVERY_TIMEOUT` | 60.0 s |

Open → caller receives `503 {"detail": "owning_layer_circuit_open"}`. Per-replica
state is acceptable: the gateway is horizontally scalable and a warm breaker on
one replica routes traffic through the others until k8s probes evict it.

### 3.3 Backpressure

A per-replica `asyncio.Semaphore` caps concurrent in-flight delegations so a
slow upstream (e.g. L4 LangGraph workflow) cannot exhaust the event loop's
connection pool. When the semaphore is saturated, new delegations fail fast with
`503 {"detail": "gateway_concurrency_exhausted"}` (not retried).

| Setting | Env var | Default |
|---|---|---|
| `_DELEGATION_MAX_CONCURRENCY` | `DELEGATION_MAX_CONCURRENCY` | 64 |

The semaphore is lazily created per event loop (via `weakref.WeakKeyDictionary`)
to avoid binding to a stale loop under pytest-asyncio's per-test loops.

### 3.4 Health probes

`app/main.py` exposes health probes for the gateway itself and for each
delegation target:

- `/healthz` — gateway liveness
- `/readyz` — gateway readiness (DB + Redis + all layer probes)
- Per-layer probes (`_api_layer_probe`) issue a lightweight GET to each layer's
  health endpoint and report DEGRADED on non-2xx.

## 4. Observability

### 4.1 Metrics

Four Prometheus metrics (in `app/core/metrics.py`) instrument every delegation:

| Metric | Labels | Meaning |
|---|---|---|
| `fabric_api_delegation_requests_total` | segment, method, status_code, outcome | Total delegated requests by outcome (success / unavailable / circuit_open / concurrency_exhausted) |
| `fabric_api_delegation_latency_seconds` | segment, method | End-to-end latency including retries |
| `fabric_api_delegation_circuit_open_total` | segment | Requests rejected because the breaker was open |
| `fabric_api_delegation_retry_total` | segment | Retry attempts issued (excludes the first try) |
| `fabric_api_delegation_cache_total` | segment, outcome | GET cache lookups (hit / miss / store / skip) |

### 4.2 Structured audit log

Every delegation emits a structured `logger.info("delegation", extra={...})`
line with segment, method, path, status_code, outcome, duration_ms, retries,
request_id, and tenant_id. These lines are the audit trail for delegated
traffic and are indexed by the platform's log pipeline.

### 4.3 Trace propagation

`merge_trace_headers()` (from
`value_fabric.shared.observability.http_trace_propagation`) injects the active
OpenTelemetry trace context into the outgoing headers dict so downstream layers
see the same trace and their spans are correlated with the gateway's. No-op
when OTel is not installed or no span is active.

## 5. GET response cache

Safe GET delegations are cached in Redis for a short TTL to reduce load on
owning layers during read-heavy access patterns (e.g. graph entity lookups).

| Setting | Env var | Default |
|---|---|---|
| `_DELEGATION_CACHE_TTL` | `DELEGATION_CACHE_TTL_SECONDS` | 30 s |

### 5.1 Eligibility

- **Method**: `GET` only. POST/PUT/PATCH/DELETE bypass the cache entirely.
- **Body**: GETs with a request body are skipped (rare; avoids cache key
  ambiguity).
- **Status**: only `2xx` upstream responses are stored. 4xx/5xx are returned
  to the caller uncached.

### 5.2 Cache key

Keys are scoped per `(tenant_id, user_id, segment, path, query_string)` using
SHA-256, so one tenant/user cannot read another's cached response. The Redis
key prefix is `delegation:get:`.

### 5.3 Fail-open behavior

Redis is optional for the cache. If `REDIS_URL` is not configured or Redis is
unreachable, lookups and stores silently fail open — the request still goes
upstream and returns the fresh response. The `x-delegation-cache` response
header is omitted when Redis is unavailable so callers can detect cache
participation:

- `x-delegation-cache: hit` — served from cache, upstream not called
- `x-delegation-cache: store` — fresh response stored to cache

## 6. Scalability

### 6.1 Horizontal Pod Autoscaler

`k8s/base/hpa/api-gateway-hpa.yml` scales the gateway between 3 and 12
replicas based on:

- CPU ≥ 70% → scale up
- Memory ≥ 80% → scale up
- Scale-up: max 100% per 60s (aggressive)
- Scale-down: max 50% per 60s (conservative)

### 6.2 Pod Disruption Budget

`k8s/base/pdb/api-gateway-pdb.yml` sets `minAvailable: 2` so voluntary
disruptions (node drains, cluster upgrades) cannot take the gateway below 2
replicas.

### 6.3 Baseline replicas

The `api-gateway` Deployment runs 3 replicas (matching the HPA minimum) to
guarantee the PDB is satisfiable at rest.

## 7. L4 workflow orchestration

`AgentOrchestrator` (`app/services/agent_orchestrator.py`) is the gateway-side
projection of L4 workflow runs. It uses `Layer4OrchestrationClient` (a sync
`httpx.Client` with retry + sync circuit breaker) to:

1. Start a LangGraph workflow run on Layer 4.
2. Poll the run status until terminal.
3. Return the structured workflow result to the caller.

Env-tunable settings (prefix `LAYER4_`):

| Env var | Default | Meaning |
|---|---|---|
| `LAYER4_RETRY_MAX_ATTEMPTS` | 3 | Max attempts for transient L4 failures |
| `LAYER4_RETRY_BASE_DELAY` | 0.2 s | Base delay for exponential backoff |
| `LAYER4_RETRY_MAX_DELAY` | 5.0 s | Cap on backoff delay |
| `LAYER4_CB_FAILURE_THRESHOLD` | 5 | Consecutive failures before the L4 breaker opens |
| `LAYER4_CB_RECOVERY_TIMEOUT` | 60.0 s | Time the L4 breaker stays open |

`_truncate_utf8(text, max_chars)` truncates upstream response bodies for error
reporting at code-point boundaries (safe for multi-byte UTF-8, no ellipsis
suffix).

## 8. MCP Gateway integration

The MCP Gateway (`packages/shared/src/value_fabric/shared/mcp_gateway/`)
secures tool invocation with OAuth 2.1 + PKCE, RFC 8693 token exchange, and JWS
manifest verification. `_execute_tool` dispatches to the registered tool
endpoint (`manifest.endpoint`) with:

- The delegated token in the `Authorization` header
- `X-Tenant-ID`, `X-User-ID`, `X-Request-ID` forwarded as headers
- The tool parameters as the JSON body
- A configurable `tool_timeout_seconds` (default 30 s)

The gateway authenticates, authorizes, and delegates a scoped token; the tool
is responsible for its own tenant isolation.

## 9. Change checklist

Before modifying the gateway orchestration:

- [ ] Identify whether the change affects L4 orchestration or generic delegation.
- [ ] Preserve router ordering (delegation registered last in `main.py`).
- [ ] Preserve tenant context propagation (`_request_headers`).
- [ ] Do not forward caller-supplied `X-Tenant-ID`; the gateway injects it
      server-side alongside `X-Service-Auth`.
- [ ] Preserve retry + circuit breaker + backpressure semantics.
- [ ] Update metrics if a new outcome class is introduced.
- [ ] Add or update regression tests in `test_layer_delegation.py` /
      `test_agent_orchestrator.py`.
- [ ] Run targeted: `pytest services/api/app/tests/test_layer_delegation.py
      services/api/app/tests/test_agent_orchestrator.py -q`.
- [ ] Report residual risks.
