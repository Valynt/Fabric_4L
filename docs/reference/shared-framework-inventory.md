# Shared Framework Inventory for Maintained Service Entrypoints

## Purpose

This inventory captures the current baseline implementation traits for all maintained service entrypoints so future refactors can be measured against explicit, testable expectations.

## Scope

- `services/layer1-ingestion/src/api/main.py`
- `services/layer1-ingestion/src/api/app_monolith.py`
- `services/layer2-extraction/src/layer2_extraction/api/main.py`
- `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/api/main.py`
- `services/layer3-knowledge/src/api/main.py`
- `services/layer4-agents/src/layer4_agents/api/main.py`
- `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py`
- `services/layer6-benchmarks/src/api/main.py`
- `services/api/app/main.py`
- `services/layer7-billing/src/layer7_billing/api/main.py`

## Service Entrypoint Migration Status

All known maintained service entrypoints are now on `create_fabric_app`.

| Service | Entrypoint | Factory | Validation | Notes |
|---|---|---|---|---|
| Layer 1 Ingestion | `services/layer1-ingestion/src/api/main.py` | `create_fabric_app` | py_compile pass; full import smoke blocked by pre-existing SQLAlchemy `orm.event` issue | Preserved middleware order, custom exception handlers, GovernanceMiddleware + `RedisRateLimiter` |
| Layer 1 Ingestion (monolith) | `services/layer1-ingestion/src/api/app_monolith.py` | `create_fabric_app` | py_compile pass | Custom exception handlers, `SecurityValidationMiddleware` |
| Layer 2 Extraction | `services/layer2-extraction/src/layer2_extraction/api/main.py` | `create_fabric_app` | Pre-existing | |
| Layer 2.5 Signal Refinery | `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/api/main.py` | `create_fabric_app` | py_compile pass | `CallableProbe` readiness via `health_probes`; CORS + Governance in `post_core_middleware_hook` |
| Layer 3 Knowledge | `services/layer3-knowledge/src/api/main.py` | `create_fabric_app` | py_compile pass; shared framework imports verified; **full import/test smoke blocked by pre-existing `db.query_execution` relative import issue** | See Layer 3 Preservation Notes below |
| Layer 4 Agents | `services/layer4-agents/src/layer4_agents/api/main.py` | `create_fabric_app` | Pre-existing | |
| Layer 5 Ground Truth | `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py` | `create_fabric_app` | Pre-existing | |
| Layer 6 Benchmarks | `services/layer6-benchmarks/src/api/main.py` | `create_fabric_app` | Pre-existing | |
| API Gateway | `services/api/app/main.py` | `create_fabric_app` | Pre-existing | |
| Layer 7 Billing | `services/layer7-billing/src/layer7_billing/api/main.py` | `create_fabric_app` | py_compile pass; no tests exist yet | Async PostgreSQL + RLS; `PostgresHealthProbe` wired to `/ready` |

> **Layer 3 validation caveat:** Layer 3 is not marked as fully validated until the pre-existing import issue (`services/layer3-knowledge/src/db/query_execution.py` relative import beyond top-level package) is fixed or bypassed with an agreed test shim. This blocker is tracked as compatibility debt.

## Baseline Inventory (per service)

| Service | Middleware stack | Health endpoints | Logging setup | Exception handlers | Tenant extraction / enforcement | Rate limiting behavior | Idempotency handling |
|---|---|---|---|---|---|---|---|
| Layer 1 Ingestion | `GovernanceMiddleware`, security middleware (`add_security_middleware`), CORS (`CORSMiddleware`), metrics (`MetricsMiddleware`) | `/health`, `/ready`, `/metrics` | `structlog.configure(...)` + bound logger | Shared envelope via `register_exception_handlers(app)` | Governance context (`request.state.governance_context`) and shared identity middleware | `RedisRateLimiter` integration in app middleware + shared throttling headers | Shared idempotency policy managed by governance middleware hooks |
| Layer 2 Extraction | Shared app factory (`create_fabric_app`) middleware bundle + router lifecycle middleware | `register_health_endpoint` registers `/health` (+ readiness through shared bootstrap) | Python `logging` logger + shared startup logging pathways | Shared envelope via `register_exception_handlers(app)` | `RequestContext` dependency + fabric auth envelope registration (`register_fabric_auth_from_env`) | Shared middleware bundle from `create_fabric_app` + policy-controlled throttling | Shared framework idempotency controls through common FastAPI bootstrap |
| Layer 3 Knowledge | `create_fabric_app` with `post_core_middleware_hook` for SecurityValidation, Governance, custom rate limiting; VersionMiddleware via `app.middleware("http")` | System router `/health` + `/metrics`; framework `/ready` via `health_probes` | `setup_logging(...)` + structured logger | Explicit exception handler registration for `ValueFabricException` family and validation errors (shared import with local fallback) | Shared identity/governance request context in dependencies and middleware | `add_rate_limiting(app, settings)` preserved as-is (pre-existing behavior) | Shared governance/idempotency compatibility in framework bootstrap |
| Layer 4 Agents | Shared bootstrap + security middleware + metrics middleware + CORS | `/health`, `/ready`, `/metrics` | Structured logging initialization + startup metadata | Shared envelope via `register_exception_handlers(app)` plus workflow-specific guards | Tenant context via shared identity middleware and agent request context objects | Shared rate limit policy wiring via bootstrap middleware | Shared idempotency envelope for workflow-triggering endpoints |
| Layer 5 Ground Truth | Shared app factory, security middleware (`add_security_middleware`), metrics middleware | `/health`, `/ready`, `/metrics` (including schema-aware readiness) | `configure_structured_logging()` and request-scoped log context helpers | Canonical JSON error envelopes and explicit handler pathways in API module | Tenant context from governance middleware and request context extraction | Shared rate-limit behavior from common bootstrap and identity policies | Shared idempotency enforcement surface in middleware policy chain |
| Layer 6 Benchmarks | Shared app factory, security middleware, metrics middleware, CORS | `/health`, `/ready`, `/metrics` | standard `logging` + startup metadata emission | Shared envelope via `register_exception_handlers(app)` | `RequestContext` dependency from `value_fabric.shared.identity.context` | Shared rate-limit policy through framework bootstrap | Shared idempotency/gateway policy behavior from bootstrap |
| API Gateway (`services/api`) | Shared app factory middleware stack + `AuditMiddleware` + metrics middleware | `register_health_endpoint` + `/metrics` | App-core logging + audit trail middleware | Shared framework exception envelope policies from API bootstrap | Tenant enforcement rollout config in `create_fabric_app(...)` | Rate-limiting rollout in `EnforcementRolloutConfig` (currently audit mode) | Idempotency rollout in `EnforcementRolloutConfig` (currently audit mode) |

## Shared App Factory DB/Session Guardrail

`create_fabric_app()` is intentionally limited to HTTP/framework assembly concerns and **must not** open or close DB sessions automatically. Session lifecycle ownership stays in each service's startup/shutdown hooks and dependency injection wiring. Any future shared DB/session helper must be explicit, opt-in, and validated service-by-service before use.

## Allowed Differences vs Must-Converge

### Allowed Differences (intentional and acceptable)

1. **Logging backend**: services may use `structlog`, stdlib `logging`, or shared logging wrappers.
2. **Health implementation details**: some services register health endpoints through helper utilities while others mount explicit handlers.
3. **Strictness mode**: enforcement mode (`audit` vs `enforce`) can vary by service and environment.
4. **Readiness depth**: readiness checks can include service-specific probes (DB schema, Neo4j, cache).

### Must-Converge Items (non-negotiable)

1. **Shared error envelope** must be registered and reachable from entrypoint code.
2. **Tenant context propagation** must originate from authenticated context / governance middleware, not request payload.
3. **Rate limiting integration** must exist and emit contract-compliant metadata where throttling is active.
4. **Health endpoint surface** must expose baseline health endpoint(s) and readiness semantics.
5. **Security/governance middleware** must remain present in all maintained service entrypoints.
6. **Idempotency policy hook point** must remain wired through shared bootstrap/governance path.

## Test Coverage Mapping

Central compatibility tests for this inventory live in:

- `tests/architecture/test_service_entrypoint_baseline_compat.py`

These tests fail fast for drift in middleware wiring, exception envelope registration, tenant context references, response metadata-related hooks, and health endpoint declarations.

## Layer 3 Migration Preservation Notes

The Layer 3 migration to `create_fabric_app` preserved the following service-specific behaviors:

- **Service-owned lifespan**: All startup/shutdown logic (telemetry, cache, metrics, versioning, Vault gate, app state) remains in the service `lifespan` hook.
- **Custom OTel tracer initialization**: `init_telemetry()` continues to set up a custom `TracerProvider` with `BatchSpanProcessor` and `OTLPSpanExporter`; `FastAPIInstrumentor.instrument_app(app)` is still called after factory creation.
- **Neo4j driver lifecycle**: Driver connection, schema initialization, and vector store setup remain service-owned in `init_app_state`.
- **Cache / metrics / versioning initialization**: Unchanged; metrics middleware is still installed inside lifespan via `install_metrics_middleware(...)`.
- **Vault production gate**: The `ENVIRONMENT=production` Vault connectivity check remains in lifespan.
- **App state ownership**: `app.state.app_state`, `app.state.cache_manager`, `app.state.metrics`, and `app.state.version_compatibility` are still managed by the service.
- **Local/shared exception handler fallback pattern**: The try/except block around `register_exception_handlers(app)` with local fallback handlers is preserved.
- **VersionMiddleware placement**: Added after factory call via `app.middleware("http")(VersionMiddleware(...))`, preserving the original effective request order.
- **Existing custom rate limiting behavior**: `add_rate_limiting(...)` is called exactly as before, preserving the pre-existing (possibly no-op) middleware registration pattern.

## Layer 3 Readiness Probe

Layer 3 now exposes `/ready` through `create_fabric_app`:

- **Path**: `/ready` (configured via `readiness_path`)
- **Probe**: `CallableProbe(name="neo4j", fn=_neo4j_probe)`
- **Implementation**: The probe checks `app.state.app_state.neo4j_driver` after lifespan initialization. If the driver is `None`, readiness returns `healthy=False` with detail `neo4j driver not connected`.
- **Backward compatibility**: Existing `/health` and `/health/detailed` endpoints in the system router remain unchanged. Consumers depending on the legacy health surface are unaffected.

## PR Summary Language

> Layer 3 was migrated to `create_fabric_app` while preserving service-owned lifespan, middleware behavior, readiness semantics, app state, and exception handling. `py_compile` and shared framework imports pass. Full Layer 3 import/test smoke remains blocked by a pre-existing `db.query_execution` relative import issue unrelated to this migration and is tracked as compatibility debt.
