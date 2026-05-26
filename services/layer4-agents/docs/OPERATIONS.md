# Layer 4 Production Operations Guide

This document covers operating the Layer 4 Agentic Workflow Engine in production environments.

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `LAYER4_DATABASE_URL` | Primary PostgreSQL connection (asyncpg) | `postgresql+asyncpg://user:pass@postgres:5432/layer4_agents` |
| `JWT_SECRET` | HS256 secret for JWT validation | `min-32-byte-secret-here` |
| `API_KEY_HMAC_SECRET` | HMAC key for API key hashing | `min-32-byte-secret-here` |

### Service Mesh & Upstream Dependencies

| Variable | Description | Production Requirement |
|----------|-------------|------------------------|
| `LAYER1_API_URL` | Layer 1 Ingestion endpoint | HTTPS to in-cluster FQDN |
| `LAYER2_API_URL` | Layer 2 Extraction endpoint | HTTPS to in-cluster FQDN |
| `LAYER3_API_URL` | Layer 3 Knowledge endpoint | HTTPS to in-cluster FQDN |
| `LAYER5_API_URL` | Layer 5 Ground Truth endpoint | HTTPS to in-cluster FQDN |
| `SERVICE_MESH_MTLS_ENABLED` | Set `true` when mesh mTLS terminates HTTPS | Required for service-mesh HTTP exceptions |

> **Security:** Never use HTTP defaults in production. Local development requires `ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT=true`.

### Optional / Fallback

| Variable | Default | Description |
|----------|---------|-------------|
| `CHECKPOINT_DATABASE_URL` | `LAYER4_DATABASE_URL` | Dedicated checkpoint database (recommended at scale) |
| `REDIS_URL` | `redis://localhost:6379` | Redis for state manager and scheduler queues |
| `LAYER4_OIDC_STATE_STORE_BACKEND` | `redis` | OIDC state backend (`redis` or `memory` for dev only) |
| `LAYER4_OIDC_STATE_TTL_SECONDS` | `300` | OIDC state record TTL |
| `LAYER4_AGENT_GATE_TIMEOUT_SECONDS` | `600` | Human review gate timeout used by the gate expiration scheduler. If unset, Layer 4 defaults to 600 seconds for backward compatibility. |
| `LLM_MODEL` | `gpt-4o` | Fallback LLM model when tenant resolution fails |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `100` | Per-tenant rate limit |
| `RATE_LIMIT_BURST_SIZE` | `20` | Per-tenant burst allowance |

## Startup Sequence

Layer 4 uses a FastAPI lifespan for deterministic startup:

1. `validate_production_safety()` — ensures secrets and HTTPS in production.
2. `configure_settings()` — lazy initialization of Infisical secrets and dependency verification.
3. Database connectivity check.
4. Vault / secret store check.
5. Redis connectivity check.
6. Checkpoint saver initialization (`AsyncPostgresSaver`).
7. Executor / scheduler / message bus startup.

### Startup Failure Behavior

| Dependency | Missing in Production | Missing in Development |
|------------|----------------------|------------------------|
| Database | **Hard failure** — pod will not start | Hard failure |
| Redis | **Hard failure** — pod will not start | Falls back to in-memory LRU (10K entries) |
| Vault | Hard failure | Warning logged, continues |
| Infisical | Warning logged, continues | Warning logged, continues |

> **Note:** As of the production readiness pass, `settings.py` no longer performs side effects at import time. All verification happens inside `configure_settings()`, called during lifespan. This means tooling, tests, and one-off scripts can import Layer 4 modules safely.

## Scaling Considerations

### PostgreSQL Checkpoints

- The checkpoint database stores LangGraph workflow state for pause/resume and human-in-the-loop flows.
- At high throughput, use a dedicated `CHECKPOINT_DATABASE_URL` separate from the primary application database.
- Monitor connection pool saturation on the checkpoint DB; `AsyncPostgresSaver` manages its own connection lifecycle.

### Redis

- Used for: workflow state caching, scheduler task queues, rate limit counters, OIDC state.
- If Redis is unavailable, the state manager falls back to an in-memory `OrderedDict` LRU with a 10,000-entry cap.
- **Risk:** In-memory fallback is per-pod; state will be lost on pod restart. Ensure Redis is highly available for production.

### Executor Concurrency

- The `OrchestrationController` uses an `asyncio.Semaphore` to bound concurrent workflows.
- Default concurrent limit is derived from `settings.max_concurrent_workflows`.
- Excess workflows are queued in the `TaskScheduler` with priority ordering (`CRITICAL` > `NORMAL` > `BACKGROUND`).

## Health Checks

The Docker image includes a Python-based health check (`src/health_check.py`) that probes the `/health` endpoint using `urllib` — no `curl` binary is required in the slim image.

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -m src.health_check || exit 1
```

### Health Endpoint Behavior

- Returns `200 OK` when the API server is responsive.
- Does **not** verify downstream dependencies (DB, Redis) to avoid cascading health check failures.
- For deep dependency health, use the readiness probe at `/ready` if configured separately.

## Monitoring & Alerting

### Prometheus Metrics

The `GovernanceMiddleware` emits rate-limit metrics on hit:

```python
# Pseudocode for metric shape
rate_limit_hits_total{tenant_id="...", path="..."}
```

Key metrics to alert on:

| Metric / Pattern | Severity | Meaning |
|------------------|----------|---------|
| `rate_limit_hits_total` spike | Warning | Tenant may be abusing API or has legitimate burst need |
| `WorkflowTimeoutError` in logs | Critical | Workflow exceeded global timeout; may need checkpoint recovery |
| `No agent available for capability` | Warning | Capability demand exceeds registered agent supply |
| `Failed to resolve LLM model` | Warning | Tenant model lookup failed; falling back to default |

### Log Patterns

Structured logs use the `Layer4LifecycleLogger` with `Layer4EventContext`:

```json
{
  "stage": "completion",
  "context": {
    "request_id": "...",
    "trace_id": "...",
    "tenant_id": "...",
    "workflow_id": "...",
    "run_id": "...",
    "provider_name": "langgraph"
  }
}
```

Alert on:
- `stage: "failure"` with `error_code: "WORKFLOW_TIMEOUT"`
- `stage: "failure"` with `error_code: "WORKFLOW_EXECUTION_ERROR"`
- Any log containing `cross-tenant` or `tenant isolation violation`

## Graceful Shutdown

When receiving `SIGTERM`:

1. Executor sets `_shutting_down = True`; new `execute_workflow` calls are rejected.
2. Active workflows are marked `INTERRUPTED` and persisted to state manager.
3. Active `asyncio.Task` objects are cancelled.
4. Scheduler stops accepting new tasks and drains its queue.
5. Message bus closes.
6. Checkpoint saver connections are closed safely (handles already-closed connections).

> **Recovery:** On next startup, interrupted workflows can be resumed via the checkpoint API (`POST /v1/workflows/{id}/resume`).

## Rate Limiting

Rate limiting is enforced by `GovernanceMiddleware` using `TenantRateLimiter`:

- Scope: per `tenant_id`
- Algorithm: token bucket (`RATE_LIMIT_REQUESTS_PER_MINUTE` / `RATE_LIMIT_BURST_SIZE`)
- Exempt: `/health` and `/metrics` endpoints
- Behavior on hit: `429 Too Many Requests` with `Retry-After` header; metric emitted

## Backup & Recovery

### Checkpoint Data

Checkpoint data is stored in PostgreSQL. Include the checkpoint database in your standard PostgreSQL backup strategy (WAL archiving, point-in-time recovery).

### Workflow State

- Redis state is ephemeral (TTL-based).
- Persistent state lives in PostgreSQL via the state manager's fallback path and checkpoint saver.
- For disaster recovery, restore checkpoint DB first, then restart Layer 4 pods.

## Security Checklist

- [ ] `JWT_SECRET` is ≥ 32 bytes and rotated on schedule
- [ ] `API_KEY_HMAC_SECRET` is ≥ 32 bytes and rotated on schedule
- [ ] `LAYER{1,2,3,5}_API_URL` values use HTTPS
- [ ] `SERVICE_MESH_MTLS_ENABLED=true` when using mesh HTTP exceptions
- [ ] Row-Level Security (RLS) policies are active on all tenant-scoped tables
- [ ] `LAYER4_OIDC_STATE_STORE_BACKEND` is `redis` in production
- [ ] Health check does not expose internal state or secrets
