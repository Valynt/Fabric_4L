# ADR-029: Middleware and Auth Flow Contract Ratification

## Status: ACCEPTED

Date: 2026-07-10  
Author: Platform Engineering Staff  
Approver: Architecture Review Board  
Supersedes: ADR-014 (Inline Middleware Registration), ADR-017 (Per-Route Auth Re-validation)

---

## Context

### The Problem

Fabric 4L's request processing pipeline has evolved organically across three years of rapid growth. The result is a middleware stack that is functionally correct in isolation but architecturally incoherent — a patchwork of inline registrations, scattered auth checks, duplicate validation logic, and response-handling middleware that breaks the abstraction boundary by writing directly to the response stream.

**Pattern A: Inline Scatter-Gather Registration** (used in `services/api/`, `services/web/`)
Middleware is registered via `app.use(middleware)` calls distributed across route files, plugin modules, and initialization hooks. The execution order depends on module load order, which depends on file system traversal and import DAG — neither of which is deterministic or explicit. During a recent incident (INC-2026-0330), a new `app.use(cors())` call added at the top of a route file inadvertently ran after the auth middleware because of ES module hoisting, causing preflight requests to fail with 401 responses.

**Pattern B: Per-Route Auth Re-validation** (used in `services/orchestrator/`, `tools/custom-agents/`)
Route handlers and business logic functions re-verify authentication by re-parsing JWT tokens, re-checking expiry, or re-querying the permissions database — work already performed by upstream middleware. This duplication creates security drift: when the auth middleware upgraded to Ed25519 signatures in March 2026, three downstream services continued validating with the old RSA path because they had their own auth logic. The inconsistency was discovered only during a security audit.

**Pattern C: Custom Validation Schemas** (used in `services/analytics/`, `services/billing/`)
Each route defines its own request validation using hand-written Joi or Zod schemas that duplicate fields already specified in the OpenAPI specification. When the OpenAPI spec changes, the hand-written schemas do not automatically update, creating mismatches between documented and actual behavior. A recent API version change added a required `region` field to a request body; the OpenAPI spec was updated, but the Zod schema in the route file was not, causing 500 errors for two weeks before detection.

**Pattern D: Middleware Response Direct Write** (used in legacy error handlers)
Middleware functions call `res.status(500).json({ error: ... })` directly rather than throwing errors that flow to the error boundary. This makes it impossible for the error boundary to apply consistent formatting, logging, and metrics. Error responses vary in shape depending on which middleware failed, breaking client parsing logic.

### Operational Impact

| Incident ID | Root Cause | Date |
|-------------|-----------|------|
| INC-2026-0330 | `app.use()` load order caused CORS to run post-auth, breaking preflight | 2026-03-30 |
| INC-2026-0418 | Per-route auth re-validation used stale RSA key after platform Ed25519 migration | 2026-04-18 |
| INC-2026-0522 | Zod schema diverged from OpenAPI spec; missing `region` validation caused 500 | 2026-05-22 |
| INC-2026-0601 | Error middleware wrote raw stack trace to response; PII exposure | 2026-06-01 |

### Decision Forces

1. **Deterministic ordering:** Middleware execution order must be explicit, version-controlled, and independent of module load order.
2. **Single auth validation:** Authentication is verified exactly once per request, at a single phase in the pipeline.
3. **Spec-driven validation:** Request validation is generated from the OpenAPI specification, not hand-maintained in parallel.
4. **Error boundary sovereignty:** Only the error boundary writes HTTP responses. All other phases throw or set context.
5. **Composability:** The pipeline must support route-specific phase declarations without inline registration.
6. **Observability:** Every phase execution is visible in traces with timing, success/failure, and context modifications.

---

## Decision

We will adopt a **single canonical pattern: Layered Middleware Stack with eight ordered phases**, plus a global error boundary. Each phase is a pure function that receives a context object and returns a modified context or throws an error. No phase writes HTTP responses directly.

### Phase Specification

| Phase | Order | Responsibility | Context Modifications | Can Terminate |
|-------|-------|---------------|----------------------|---------------|
| `request_id` | 1 | Assign or propagate `x-request-id` | Sets `ctx.requestId` | No |
| `correlation` | 2 | Extract/inject distributed trace IDs | Sets `ctx.traceId`, `ctx.span` | No |
| `auth` | 3 | Validate credentials, establish tenant context | Sets `ctx.identity`, `ctx.tenantContext` | Yes (401/403) |
| `tenant_scope` | 4 | Validate tenant access tier and permissions | May narrow `ctx.tenantContext.scope` | Yes (403) |
| `rate_limit` | 5 | Apply rate limiting keyed by tenant + endpoint + identity | No modifications | Yes (429) |
| `validation` | 6 | Validate request body and parameters against OpenAPI | Sets `ctx.validatedBody`, `ctx.validatedParams` | Yes (400) |
| `handler` | 7 | Execute business logic | Sets `ctx.result` | Yes |
| `response` | 8 | Serialize `ctx.result` to response format | Sets response body and headers | No |
| `error_boundary` | Global | Catch all errors, normalize to canonical error shape | Sets response body and status | Yes |

### Contract Rules

1. **Explicit ordering:** The complete phase list is declared in a single `pipeline.config.ts` file per service. No `app.use()` calls exist outside this file. Phase order is immutable at runtime.

2. **Auth produces, downstream consumes:** The `auth` phase is the sole producer of `AuthContext`. All downstream phases receive `ctx.identity` and `ctx.tenantContext` as read-only. Re-validation is prohibited. If downstream code needs additional identity claims, it reads from `ctx.identity.claims` — it does not re-parse the JWT.

3. **Route manifests declare phases:** Every route declares its required phases in the route manifest (see ADR-032). The pipeline executor skips phases not declared for a route (e.g., a health-check route may declare only `request_id`, `handler`, `response`).

4. **OpenAPI-driven validation:** The `validation` phase uses validators auto-generated from the OpenAPI specification by `openapi-typescript` and `openapi-validator`. No hand-written Zod, Joi, or Yup schemas exist in route files.

5. **Error boundary exclusivity:** Only the `error_boundary` phase writes to the HTTP response. All other phases communicate failure by throwing an error with a canonical error code. The error boundary catches, logs, formats, and responds.

6. **Context immutability between phases:** Each phase receives a shallow-frozen context snapshot. Modifications are made via `ctx.with({ key: value })` which returns a new context object. This prevents accidental mutation of context by one phase affecting another.

7. **Phase timing and observability:** Each phase execution creates an OpenTelemetry span. Phase latency, success/failure, and context modifications (keys added/removed) are recorded as span attributes. Spans are nested under the request trace.

8. **Rate limiting contract:** Rate limiting is keyed by `tenant_id::endpoint_pattern::identity_hash` with per-tier limits. The `rate_limit` phase does not modify context; it either continues (within limit) or terminates (exceeded). Rate limit state is stored in Redis with 1-second granularity.

### Why Ordered Phases over alternatives

| Alternative | Reason for rejection |
|-------------|---------------------|
| Express/Connect `app.use()` chain | Non-deterministic ordering, mutable at runtime, scattered registration |
| Koa-style onion middleware | Composable but ordering still implicit; no phase boundaries |
| FastAPI dependency injection | Excellent for Python but not portable to Node.js services; ordering implicit |
| Envoy/Istio external auth | Adds network hop, latency, and infrastructure complexity; doesn't solve application-layer ordering |
| Event-driven pipeline | Too complex for synchronous request processing; debugging overhead |

The ordered phase model makes the pipeline inspectable: at startup, the system logs the exact phase order for every route. It makes the pipeline testable: each phase is a pure function with known inputs and outputs. It makes the pipeline enforceable: the manifest validator fails CI if a route declares a phase without declaring all its prerequisites.

---

## Consequences

### Positive

- **Deterministic execution:** Middleware order is explicit in `pipeline.config.ts` and identical across all environments. No more load-order incidents.
- **Single auth validation:** Authentication happens exactly once. Security upgrades (new signature algorithms, claim validation) require changes only in the `auth` phase implementation.
- **Spec-driven validation:** Request validators are generated from OpenAPI. When the spec changes, validators regenerate automatically. No divergence.
- **Consistent error handling:** The error boundary owns all responses. Every error follows the canonical envelope shape (see ADR-031). No more raw stack traces in responses.
- **Route-level observability:** The pipeline executor logs per-phase latency, enabling precise bottleneck identification.
- **Testability:** Individual phases are pure functions testable without HTTP servers. The pipeline executor is testable with mock phases.
- **Security posture:** Auth is centralized and auditable. Downstream code cannot accidentally skip or weaken validation.
- **Onboarding clarity:** New engineers learn one pipeline model that applies to every service. No service-specific middleware conventions.

### Negative

- **Learning curve:** Engineers familiar with Express `app.use()` must learn the phase model. Documentation and reference implementation mitigate this.
- **Verbosity:** Declaring all phases explicitly is more verbose than `app.use(router)`. The route manifest abstraction reduces boilerplate for common patterns.
- **Migration cost:** ~45 services have scattered `app.use()` registrations. Each must be migrated to the pipeline config. A codemod extracts existing middleware into phase functions.
- **Debugging complexity:** The context object is abstract; attaching a debugger requires understanding the phase model. We add a `debug` phase that dumps context state when `FABRIC_DEBUG_PIPELINE=1`.
- **Performance overhead:** Context snapshotting between phases adds ~0.3ms per request. This is negligible compared to the I/O in typical handlers (database, external APIs).

---

## Compliance

### Automated Enforcement (Three Layers)

**IDE / Local Development:**
- ESLint rule `no-inline-middleware`: Error on `app.use()` calls outside `pipeline.config.ts`.
- ESLint rule `no-req-auth-revalidation`: Error on `jwt.verify()`, `jwt.decode()`, or manual token parsing outside the `auth` phase.
- ESLint rule `no-handwritten-validation-schema`: Error on Zod/Joi/Yup schema definitions in route files when an OpenAPI spec exists.
- ESLint rule `no-middleware-res-write`: Error on `res.status().json()` or `res.send()` calls outside the `response` and `error_boundary` phases.

**Pre-commit:**
- `lint-staged` runs ESLint on changed files.
- `pipeline-manifest-check` warns if a route's phase declaration is missing required prerequisites (e.g., declaring `tenant_scope` without `auth`).

**CI Gate:**
- `check_middleware` job runs on every PR:
  - ESLint rules are errors (exit 1 on violation)
  - Pipeline manifest validator: every route's declared phases form a valid prefix of the canonical phase list (no skipping prerequisites)
  - OpenAPI spec diff: PRs modifying routes must include corresponding OpenAPI spec changes
  - Phase timing test: integration test verifies that `auth` phase executes before `validation` phase for all routes

### Runtime Enforcement
- Pipeline manifest validator runs at application startup and `process.exit(1)` if any route has invalid phase declarations.
- Attempting to modify `ctx` in-place (not via `ctx.with()`) throws a runtime error in development builds (detected via Proxy).
- Error boundary catches all unhandled errors and returns canonical error shape. Errors escaping the boundary are logged as critical bugs.

### Manual Verification
- Quarterly architecture review spot-checks 5 random services for middleware compliance.
- Security audit verifies auth phase is the sole JWT validation point per service.

---

## Migration

### Timeline

| Phase | Version | Date | Behavior |
|-------|---------|------|----------|
| Soft deprecation | v1.2.0 | 2026-07-10 | ESLint warnings, dashboard tracking, codemod available, new services use pipeline |
| Hard enforcement | v1.3.0 | 2026-10-10 | ESLint errors, CI fails on violations, all new routes must use pipeline config |
| Removal | v1.4.0 | 2027-01-10 | Legacy inline middleware adapters removed, all services must use pipeline |

### Codemod: `migrate-middleware-pipeline`

```bash
npx @fabric/codemod migrate-middleware-pipeline --target ./services/api --write
```

The codemod performs these transforms:

**Before:**
```typescript
// services/api/src/routes/workflows.ts (scattered inline registration)
import { authMiddleware } from "../middleware/auth";
import { validateWorkflowBody } from "../validation/workflows";
import { rateLimiter } from "../middleware/rate-limit";

const router = Router();

// Inline middleware scattered through route files
router.use(rateLimiter);

router.post(
  "/workflows",
  authMiddleware,
  validateWorkflowBody,  // hand-written Zod schema
  async (req, res) => {
    // Re-validates JWT inside handler — anti-pattern
    const token = req.headers.authorization?.split(" ")[1];
    const payload = jwt.verify(token, JWT_SECRET);  // DUPLICATED AUTH
    const tenantId = payload.tenant_id;

    const workflow = await createWorkflow(req.body, tenantId);
    res.status(201).json(workflow);
  },
);

// Error handler in a different file, writes response directly
router.use((err, req, res, next) => {
  res.status(500).json({ error: err.message, stack: err.stack });  // LEAKS STACK
});
```

**After:**
```typescript
// services/api/src/pipeline.config.ts
export const pipelineConfig: PipelineConfig = {
  phases: [
    "request_id",
    "correlation",
    "auth",
    "tenant_scope",
    "rate_limit",
    "validation",
    "handler",
    "response",
  ],
  errorBoundary: "error_boundary",
};

// services/api/src/routes/workflows.ts
import { defineRoute } from "@fabric/platform/pipeline";

export const workflowRoutes = defineRoute({
  path: "/workflows",
  method: "POST",
  phases: ["request_id", "correlation", "auth", "tenant_scope", "rate_limit", "validation", "handler", "response"],
  openApiSpec: "#/paths/workflows/post",
  handler: async (ctx: PipelineContext): Promise<Workflow> => {
    // Auth already validated; tenant context available
    const { tenantContext, validatedBody } = ctx;
    const workflow = await createWorkflow(validatedBody, tenantContext.tenant_id);
    return ctx.with({ result: workflow });
  },
});
```

**Before (legacy auth re-validation in business logic):**
```typescript
// services/orchestrator/src/agents/runner.ts
async function executeAgentRun(
  runId: string,
  tenantId: string,
  agentConfig: AgentConfig,
): Promise<RunResult> {
  // Re-validates tenant access by querying DB — already done in middleware
  const hasAccess = await checkTenantAccess(tenantId, agentConfig.required_scope);
  if (!hasAccess) throw new AuthError("Access denied");

  // ...
}
```

**After (trust auth context, no re-validation):**
```typescript
// services/orchestrator/src/agents/runner.ts
import { getTenantContextOrThrow } from "@fabric/platform/context";

async function executeAgentRun(
  runId: string,
  agentConfig: AgentConfig,
): Promise<RunResult> {
  const ctx = getTenantContextOrThrow();
  // Tenant access already validated by tenant_scope phase
  // ctx.scope contains granted permissions
  if (!ctx.scope.includes(agentConfig.required_scope)) {
    throw new AuthorizationError(`Missing scope: ${agentConfig.required_scope}`);
  }
  // ...
}
```

### Service-by-Service Rollout

| Service | Pattern Before | Migration Effort | Owner | Target Completion |
|---------|---------------|-----------------|-------|-------------------|
| `services/api/` | Inline scatter-gather | High (12 route files) | @team-platform | 2026-09-01 |
| `services/web/` | Inline scatter-gather | Medium (6 route files) | @team-web | 2026-08-15 |
| `services/orchestrator/` | Per-route auth re-validation | High (8 agent runners) | @team-agents | 2026-09-15 |
| `services/analytics/` | Custom Zod schemas | Medium (15 schemas) | @team-data | 2026-08-30 |

### Checklist Per Service

- [ ] Extract all `app.use()` calls into `pipeline.config.ts`
- [ ] Convert middleware functions to phase functions `(ctx) => ctx.with({...})`
- [ ] Remove all JWT re-validation from route handlers and business logic
- [ ] Replace hand-written validation schemas with OpenAPI-generated validators
- [ ] Remove all `res.send()`, `res.json()`, `res.status()` calls from middleware
- [ ] Add route manifests for all routes with correct phase declarations
- [ ] Verify pipeline manifest validator passes at startup
- [ ] Run integration tests: all routes return correct status codes
- [ ] Update service README with "Middleware Pipeline" section linking to this ADR
- [ ] Tag PR with `contract-adr-029`

---

## Appendix: Phase Interface

```typescript
// platform/pipeline/types.ts
interface PipelineContext {
  readonly requestId: string;
  readonly traceId: string;
  readonly span: Span;
  readonly identity: AuthIdentity | null;
  readonly tenantContext: TenantContext | null;
  readonly validatedBody: unknown;
  readonly validatedParams: Record<string, string>;
  readonly result: unknown;

  with(partial: Partial<PipelineContext>): PipelineContext;
}

type PhaseFunction = (ctx: PipelineContext) => Promise<PipelineContext>;

interface PipelineConfig {
  phases: readonly string[];
  errorBoundary: string;
  phaseImplementations: Record<string, PhaseFunction>;
}
```

---

## References

- CONTRACT.md Section 2.3: Middleware and Auth Flow
- ADR-028: Tenant Context Propagation Contract Ratification
- ADR-032: UI Route/State Progression Contract Ratification
- `examples/canonical/middleware/pipeline.ts`: Reference implementation
- `test/middleware-phase-order.spec.ts`: Compliance test
- INC-2026-0330, INC-2026-0418, INC-2026-0522, INC-2026-0601: Incident reports
