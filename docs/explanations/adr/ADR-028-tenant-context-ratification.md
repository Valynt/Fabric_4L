# ADR-028: Tenant Context Propagation Contract Ratification

## Status: ACCEPTED

Date: 2026-07-10  
Author: Platform Engineering Staff  
Approver: Architecture Review Board  
Supersedes: ADR-019 (Tenant ID as Parameter), ADR-022 (Tenant Context on Request Object)

---

## Context

### The Problem

As of Q2 2026, Fabric 4L has three competing patterns for propagating tenant identity across asynchronous call boundaries — each partially correct, each actively used in production, and each creating compounding drag on engineering velocity and operational safety.

**Pattern A: Explicit Parameter Passing** (used in `services/api/`, `services/orchestrator/`)
Every function signature in the call chain carries a `tenantId: string` parameter. This creates parameter pollution: a function at layer N that does not itself need tenant awareness must still accept and forward `tenantId` solely because something at layer N+1 requires it. The result is signatures like `processWorkflow(workflowId, tenantId, options, context)` where `tenantId` is visually indistinguishable from business parameters. Refactoring becomes high-touch because changing a leaf function's tenant needs forces signature changes up the entire stack.

**Pattern B: Request-Object Mutation** (used in `services/web/`, `middleware/legacy/`)
The authentication middleware decodes the JWT and stores a mutable `tenant` object directly on the Express/Fastify request object (`req.tenant = decoded`). Downstream code reads from `req.tenant.id`. This pattern fails as soon as work leaves the HTTP request lifecycle: background jobs, WebSocket handlers, and inter-service gRPC calls have no `req` object. It also permits accidental mutation — multiple middleware layers have been observed overwriting `req.tenant` with partial or inconsistent shapes, causing subtle cross-tenant context corruption that is nearly impossible to reproduce in development.

**Pattern C: Direct Header Access** (used in `services/analytics/`, `tools/ad-hoc-scripts/`)
Code reads `req.headers["x-tenant-id"]` or parses the JWT claims inline at the point of use. This duplicates JWT validation logic across dozens of files, creates security gaps (not all code paths validate signatures), and makes tenant context extraction dependent on transport-layer specifics that should be abstracted by the time business logic executes.

### Operational Impact

| Incident ID | Root Cause | Date |
|-------------|-----------|------|
| INC-2026-0412 | Background job used `req.tenant` (undefined in job context), defaulted to `null`, and ran RLS-unrestricted query across all tenants | 2026-04-12 |
| INC-2026-0528 | Parameter-passing refactoring omitted `tenantId` in one call site; query ran without `SET LOCAL app.tenant_id`, returning 14,000 rows from wrong tenant | 2026-05-28 |
| INC-2026-0614 | Analytics script parsed JWT claims without signature verification; forged `x-tenant-id` header exposed billing data | 2026-06-14 |

These are not coding errors in isolation. They are systemic consequences of pattern competition. When three patterns coexist, no single pattern receives the testing, documentation, and enforcement investment required to make it safe at scale.

### Decision Forces

1. **Safety:** Tenant context must be immutable, validated, and fail-safe (return `null` or throw outside scope — never default to a shared context).
2. **Transport independence:** Business logic must not know whether it is running inside an HTTP request, a background job, or a CLI script.
3. **Ergonomics:** The right way must require less code than the wrong way.
4. **Observability:** Every operation must be traceable to a tenant without manual annotation.
5. **Migration cost:** We have ~340 call sites to migrate across 8 services. The new pattern must support incremental adoption.

---

## Decision

We will adopt a **single canonical pattern: Request-Scoped Async Context with Middleware Injection**, using `AsyncLocalStorage` (Node.js) or language-equivalent thread-local / context-local storage.

### Specification

1. **Storage:** `AsyncLocalStorage<TenantContext>` is instantiated once in `platform/context/tenant-storage.ts` and exported as `tenantContextStore`.

2. **Injection:** A single `TenantContextMiddleware` runs immediately after the `auth` phase (phase 3 of the middleware stack; see ADR-029). It validates the JWT signature, extracts `tenant_id`, constructs a `TenantContext` object, and calls `tenantContextStore.run(ctx, () => next())`. No other middleware or handler constructs or modifies tenant context.

3. **Access:** All downstream code calls `getTenantContext(): TenantContext | null` imported from `platform/context/tenant-context.ts`. This function reads from `tenantContextStore.getStore()`. It returns `null` when called outside an active async scope.

4. **Immutability:** The context object is constructed with `Object.freeze()` at the top level and on all nested objects. To create a derived context (e.g., for a sub-operation with narrowed scope), use `withTenantContext(baseCtx, overrides): TenantContext` which constructs a new frozen object.

5. **Cross-service propagation:** When service A calls service B via HTTP, the outbound request includes header `x-fabric-tenant-id: <tenant_id>` signed with the inter-service signing key (`x-fabric-tenant-sig: <hmac>`). Service B's auth middleware verifies the HMAC before constructing tenant context. When propagating via message queue, the tenant_id is included as an explicit field in the message payload and verified against the publisher's signing key.

6. **Required fields:**
   - `tenant_id`: UUIDv4, validated at injection time
   - `tenant_tier`: `"shared" | "dedicated" | "enterprise"`
   - `region`: string, the deployment region hosting tenant data
   - `issued_at`: ISO 8601 timestamp of context creation
   - `scope`: array of permission strings granted by the auth phase

7. **Lifetime:** The context lives for the duration of the `AsyncLocalStorage.run()` call. For HTTP requests, this is the request handler. For background jobs, the job processor wraps its execution in `tenantContextStore.run()`. For tests, `withTenantContext()` provides a scoped helper.

8. **Fail-safe guarantees:**
   - `getTenantContext()` returns `null` outside scope (never undefined, never a default context).
   - Database access helpers require a non-null context (via `getTenantContextOrThrow()`).
   - RLS policies use `current_setting('app.tenant_id', true)` which returns empty string if unset, matching no rows rather than all rows.

### Why AsyncLocalStorage over alternatives

| Alternative | Reason for rejection |
|-------------|---------------------|
| Continuation-local storage (`cls-hooked`) | Legacy, unmaintained, performance overhead ~15% vs ALS ~3% |
| Explicit parameter passing | Parameter pollution, high refactoring cost, easy to omit |
| Request-object attachment | Not transport-agnostic, mutable, fails outside HTTP |
| Dependency injection container | Adds indirection, startup complexity, harder to trace |
| Zone.js | Overly broad, modifies global Promise, incompatible with some native modules |

`AsyncLocalStorage` is Node.js native (stable since v16), zero-dependency, performs within 3% of raw async/await, and works identically for HTTP requests, WebSocket message handlers, and background job processors.

---

## Consequences

### Positive

- **Eliminates parameter pollution:** Function signatures contain only business parameters. Tenant context is ambient within the async scope.
- **Transport independence:** The same business logic code runs correctly inside HTTP handlers, background jobs, CLI scripts, and test cases without modification.
- **Immutable by construction:** Deep-frozen context objects prevent the accidental mutation bugs that caused INC-2026-0412.
- **Single point of validation:** JWT verification, signature checking, and tenant existence validation happen in exactly one place. No downstream code can skip or duplicate these checks.
- **Automatic propagation:** Context flows across `await` boundaries without manual forwarding. Developers cannot forget to pass it.
- **Observability built-in:** Every OpenTelemetry span automatically includes `tenant.id` from `getTenantContext()` via a custom span processor.
- **Safe defaults:** `getTenantContext()` returning `null` outside scope makes missing-context bugs obvious rather than silent.
- **Testability:** `withTenantContext(ctx, async () => { ... })` provides a clean, scope-bound way to set context in tests without mocking request objects.

### Negative

- **Node.js specific:** `AsyncLocalStorage` is Node.js. Python services use `contextvars`, Go uses goroutine-local patterns. We must maintain three language-specific implementations with identical semantics. A shared conformance test suite mitigates divergence risk.
- **Debugging complexity:** Async context is invisible in stack traces. We add `getTenantContext()` to error metadata in the error boundary to compensate.
- **Nested scope footgun:** Calling `tenantContextStore.run()` inside an existing run creates a nested scope that shadows the outer context. We lint against nested `run()` calls and provide `withTenantContext()` which uses the outer context as a base.
- **Memory-leak risk if misused:** Storing the ALS instance on a per-request basis rather than as a singleton causes memory growth. The lint rule `no-als-instance-per-request` catches this.
- **Migration cost:** ~340 call sites across 8 services require mechanical refactoring. We provide a codemod (see Migration section) that automates ~85% of changes.

---

## Compliance

### Automated Enforcement (Three Layers)

**IDE / Local Development:**
- ESLint rule `no-tenant-id-parameter`: Error on function parameters matching `/tenant[_-]?id/i` in production source. Exception: adapter layers translating external APIs.
- ESLint rule `no-req-tenant-access`: Error on `req.headers["x-tenant-id"]` or `req.tenant` access outside `middleware/auth/`.
- ESLint rule `no-mutable-tenant-state`: Error on assignment to `req.tenant` or property mutation of tenant context objects.

**Pre-commit:**
- `lint-staged` runs ESLint on changed files.
- `tenant-context-smell-check` script warns if a diff adds a `tenantId` parameter.

**CI Gate:**
- `check_tenant_context` job runs on every PR:
  - ESLint rules are errors (exit 1 on violation)
  - Integration test: `test/cross-tenant-isolation.spec.ts` verifies that Service A cannot read Service B's tenant data even with a forged header
  - Static analysis report: count of `tenantId` parameters, `req.tenant` accesses, direct header reads — tracked in dashboard, must not increase

### Runtime Enforcement
- `getTenantContext()` returns `null` outside scope (fail-safe, non-blocking in development, monitored in production).
- `getTenantContextOrThrow()` throws `TenantContextMissingError` when context is required. Used by all database access helpers.
- RLS policies use `current_setting('app.tenant_id', true)` which returns empty string if unset, matching no rows.

### Manual Verification
- Quarterly architecture review spot-checks 10 random services for context access patterns.
- Security audit includes cross-tenant isolation test as a mandatory checklist item.

---

## Migration

### Timeline

| Phase | Version | Date | Behavior |
|-------|---------|------|----------|
| Soft deprecation | v1.2.0 | 2026-07-10 | ESLint warnings, dashboard tracking, codemod available |
| Hard enforcement | v1.3.0 | 2026-10-10 | ESLint errors, CI fails on violations, no new `tenantId` parameters allowed |
| Removal | v1.4.0 | 2027-01-10 | Legacy adapter code removed, all services must comply |

### Codemod: `migrate-tenant-context`

```bash
npx @fabric/codemod migrate-tenant-context --target ./services/api --write
```

The codemod performs these transforms:

**Before:**
```typescript
// services/api/src/workflows/service.ts
async function processWorkflow(
  workflowId: string,
  tenantId: string,
  options: ProcessOptions,
): Promise<WorkflowResult> {
  const db = await getDbForTenant(tenantId);
  const rules = await loadRules(tenantId, workflowId);
  // ...
}

// Route handler
router.post("/workflows/:id/process", auth, async (req, res) => {
  const result = await processWorkflow(req.params.id, req.tenant.id, req.body);
  res.json(result);
});
```

**After:**
```typescript
// services/api/src/workflows/service.ts
import { getTenantContext } from "@fabric/platform/context";

async function processWorkflow(
  workflowId: string,
  options: ProcessOptions,
): Promise<WorkflowResult> {
  const ctx = getTenantContextOrThrow();
  const db = await getDbFromContext(ctx);
  const rules = await loadRules(ctx.tenant_id, workflowId);
  // ...
}

// Route handler — tenant context set by middleware, no parameter needed
router.post("/workflows/:id/process", auth, async (req, res) => {
  const result = await processWorkflow(req.params.id, req.body);
  res.json(result);
});
```

### Service-by-Service Rollout

| Service | Pattern Before | Migration Effort | Owner | Target Completion |
|---------|---------------|-----------------|-------|-------------------|
| `services/api/` | Parameter passing | Medium (120 call sites) | @team-platform | 2026-08-15 |
| `services/orchestrator/` | Parameter passing | Medium (85 call sites) | @team-agents | 2026-08-30 |
| `services/web/` | Request-object mutation | Low (40 call sites) | @team-web | 2026-08-01 |
| `services/analytics/` | Direct header access | High (95 call sites) | @team-data | 2026-09-15 |
| `tools/ad-hoc-scripts/` | Direct header access | Low (variable) | @team-platform | 2026-08-15 |

### Checklist Per Service

- [ ] Run codemod on service directory
- [ ] Fix any codemod failures manually (complex destructuring, default parameters)
- [ ] Remove `tenantId` from all function signatures below the HTTP handler layer
- [ ] Replace `req.tenant` reads with `getTenantContext()`
- [ ] Replace direct header access with `getTenantContext()`
- [ ] Verify all database calls use `getDbFromContext()` (not `getDbForTenant(tenantId)`)
- [ ] Run integration tests: `test/cross-tenant-isolation.spec.ts` passes
- [ ] Update service README with "Tenant Context" section linking to this ADR
- [ ] Tag PR with `contract-adr-028`

---

## Appendix: Language-Specific Implementation Notes

### TypeScript / Node.js
```typescript
// platform/context/tenant-storage.ts
import { AsyncLocalStorage } from "async_hooks";

export interface TenantContext {
  readonly tenant_id: string;
  readonly tenant_tier: "shared" | "dedicated" | "enterprise";
  readonly region: string;
  readonly issued_at: string;
  readonly scope: readonly string[];
}

export const tenantContextStore = new AsyncLocalStorage<TenantContext>();

export function getTenantContext(): TenantContext | null {
  return tenantContextStore.getStore() ?? null;
}

export function getTenantContextOrThrow(): TenantContext {
  const ctx = getTenantContext();
  if (!ctx) throw new TenantContextMissingError();
  return ctx;
}

export function withTenantContext<T>(
  ctx: TenantContext,
  fn: () => Promise<T>,
): Promise<T> {
  return tenantContextStore.run(Object.freeze(ctx), fn);
}
```

### Python
```python
# platform/context/tenant_context.py
import contextvars
from dataclasses import dataclass, replace
from typing import Optional

_tenant_context_var: contextvars.ContextVar[Optional["TenantContext"]] = (
    contextvars.ContextVar("tenant_context", default=None)
)

@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tenant_tier: str  # "shared" | "dedicated" | "enterprise"
    region: str
    issued_at: str
    scope: tuple[str, ...]

def get_tenant_context() -> Optional[TenantContext]:
    return _tenant_context_var.get()

def get_tenant_context_or_raise() -> TenantContext:
    ctx = get_tenant_context()
    if ctx is None:
        raise TenantContextMissingError()
    return ctx
```

### Go
```go
// platform/context/tenantcontext.go
package context

import "context"

type tenantContextKey struct{}

func WithTenantContext(ctx context.Context, tc TenantContext) context.Context {
    return context.WithValue(ctx, tenantContextKey{}, tc)
}

func GetTenantContext(ctx context.Context) (TenantContext, bool) {
    tc, ok := ctx.Value(tenantContextKey{}).(TenantContext)
    return tc, ok
}
```

---

## References

- CONTRACT.md Section 2.1: Tenant Context Propagation
- ADR-029: Middleware and Auth Flow Contract Ratification
- `examples/canonical/context/tenant-context.ts`: Reference implementation
- `test/cross-tenant-isolation.spec.ts`: Compliance test
- INC-2026-0412, INC-2026-0528, INC-2026-0614: Incident reports
