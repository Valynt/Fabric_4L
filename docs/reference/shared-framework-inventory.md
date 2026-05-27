# Shared Framework Inventory for Maintained Service Entrypoints

## Purpose

This inventory captures the current baseline implementation traits for all maintained service entrypoints so future refactors can be measured against explicit, testable expectations.

## Scope

- `services/layer1-ingestion/src/api/main.py`
- `services/layer2-extraction/src/layer2_extraction/api/main.py`
- `services/layer3-knowledge/src/api/main.py`
- `services/layer4-agents/src/api/main.py`
- `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py`
- `services/layer6-benchmarks/src/api/main.py`
- `services/api/app/main.py`

## Baseline Inventory (per service)

| Service | Middleware stack | Health endpoints | Logging setup | Exception handlers | Tenant extraction / enforcement | Rate limiting behavior | Idempotency handling |
|---|---|---|---|---|---|---|---|
| Layer 1 Ingestion | `GovernanceMiddleware`, security middleware (`add_security_middleware`), CORS (`CORSMiddleware`), metrics (`MetricsMiddleware`) | `/health`, `/ready`, `/metrics` | `structlog.configure(...)` + bound logger | Shared envelope via `register_exception_handlers(app)` | Governance context (`request.state.governance_context`) and shared identity middleware | `RedisRateLimiter` integration in app middleware + shared throttling headers | Shared idempotency policy managed by governance middleware hooks |
| Layer 2 Extraction | Shared app factory (`create_fabric_app`) middleware bundle + router lifecycle middleware | `register_health_endpoint` registers `/health` (+ readiness through shared bootstrap) | Python `logging` logger + shared startup logging pathways | Shared envelope via `register_exception_handlers(app)` | `RequestContext` dependency + fabric auth envelope registration (`register_fabric_auth_from_env`) | Shared middleware bundle from `create_fabric_app` + policy-controlled throttling | Shared framework idempotency controls through common FastAPI bootstrap |
| Layer 3 Knowledge | Shared framework middlewares (`add_request_id_middleware`, `add_governance_middleware`, security validation, CORS) | System router health/readiness + metrics endpoint | `setup_logging(...)` + structured logger | Explicit exception handler registration for `ValueFabricException` family and validation errors | Shared identity/governance request context in dependencies and middleware | `add_rate_limiting(app, settings)` canonical rate-limit middleware | Shared governance/idempotency compatibility in framework bootstrap |
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
