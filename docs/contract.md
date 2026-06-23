# Fabric 4L Canonical Platform Contract — Engineering Specification

## TL;DR

Fabric 4L currently bleeds velocity because six critical cross-layer concerns each have 2–3 partially-good patterns competing simultaneously. This document specifies a single unambiguous canonical contract for each concern, paired with automated enforcement and a concrete deprecation map. The goal is to convert Fabric 4L from an evolving codebase into a governed product platform where the right way is the easy way, and the wrong way fails CI.

---

## 1. Problem Statement

The single biggest drag on Fabric 4L is not lack of ideas or components. It is the presence of multiple partially-good patterns competing across every layer. This pattern competition creates compounding slowdown that affects architecture review, implementation, test design, CI gating, onboarding, and bug triage.

The most effective action is to create and enforce one canonical contract for the whole platform across six specific dimensions, with four concrete deliverables: an architecture contract doc, a canonical reference implementation, automated lint and CI enforcement, and a deprecation map for non-canonical patterns.

---

## 2. The Six Canonical Contracts

### 2.1 Tenant Context Propagation

**Status:** `proposed` | **Target:** `ratified` 2026-05-23 | **Enforcement:** 2026-06-23

**Canonical Pattern:** Request-Scoped Async Context with Middleware Injection

Tenant context flows as an immutable request-scoped object established at the authentication boundary and propagated automatically across all asynchronous boundaries via AsyncLocalStorage. It is never passed as an explicit function parameter.

**Contract Rules:**
- Storage mechanism: AsyncLocalStorage (Node.js) or language-equivalent
- Initial injection: Single auth middleware validates JWT/headers, extracts tenant_id
- Propagation: Automatic via AsyncLocalStorage.run()
- Cross-service propagation: `x-fabric-tenant-id` header with signature verification
- Message queue propagation: Explicit tenant_id field in every message payload
- Access pattern: `getTenantContext()` helper; returns null if called outside scope
- Required fields: tenant_id (UUIDv4), tenant_tier (shared|dedicated|enterprise), region, issued_at, scope
- Immutability: Context object is deeply frozen; modifications via `withTenantContext(ctx, overrides)`
- Lifetime: Context lives for duration of request async scope

**Anti-patterns being deprecated:**
- Passing tenantId as parameter through service layers (parameter pollution)
- Reading tenant ID directly from req.headers or JWT claims outside auth middleware
- Storing mutable tenant state on request object
- Deriving tenant context differently in different services

**Enforcement:**
- ESLint: `no-tenant-id-parameter` - flags function parameters named tenantId variants
- ESLint: `no-req-tenant-access` - flags direct header access outside auth middleware
- Runtime: getTenantContext() returns null outside async scope (fail-safe)
- Integration test: Cross-tenant isolation test runs on every CI build [VERIFY:DOC-TENANT-001]

---

### 2.2 DB Session and Isolation Pattern

**Status:** `ratified` | **Ratified:** 2026-04-25 | **Enforcement:** 2026-06-23

**Canonical Pattern:** PostgreSQL Row-Level Security via `SET LOCAL app.tenant_id`

All tenant-scoped database access uses shared-schema PostgreSQL with mandatory `tenant_id` columns and RLS policies enforced via `SET LOCAL app.tenant_id` at the start of every transaction. This is the **Enforced Canon** per the Unified Recommendation memo (2026-04-25).

**Contract Specification:**

| Concern | Canonical Decision | Rationale |
|---------|-------------------|----------|
| Isolation model | Shared schema with `tenant_id` NOT NULL column + PostgreSQL RLS | Simplest model that provides strong isolation; covers ~100% of current tenants |
| Session variable | `SET LOCAL app.tenant_id = :tenant_id` | Transaction-scoped; automatically cleared on commit/rollback |
| RLS policy expression | `tenant_id::text = current_setting('app.tenant_id', true)` | Consistent across all layers; `true` flag returns empty string if unset (fail-safe) |
| Admin bypass | `SET LOCAL app.tenant_id = ''` with `admin_role` / `system_role` | Empty string bypasses RLS via dedicated admin policy; requires super_admin role |
| FastAPI dependency | `get_db_from_context()` reads tenant from `RequestContext` | Single canonical path; context set by `GovernanceMiddleware` |
| Background tasks | Explicit `SET LOCAL` using tenant_id from task payload | Celery/background tasks must set tenant context before any DB operation |

**Contract Rules:**
- Every tenant-scoped table MUST have a `tenant_id` column with NOT NULL constraint
- Every tenant-scoped table MUST have an RLS policy using `current_setting('app.tenant_id', true)`
- All production endpoints MUST use `get_db_from_context()` (not `get_db()`)
- Cross-tenant queries require BYPASS RLS role with audit logging
- The column MUST be named `tenant_id` (not `organization_id` or variants)

**Target Architecture (non-blocking, experimental):**

| Tenant Tier | Isolation Model | Status |
|-------------|----------------|--------|
| shared (default) | Shared schema + RLS | **Enforced Canon** |
| dedicated | Dedicated schema per tenant | Experimental (`examples/experimental/tenant-aware-pool/`) |
| enterprise | Dedicated database instance | Experimental |

> **Note:** `TenantAwarePool` and tiered isolation are preserved as target architecture in `examples/experimental/`. They are non-blocking and cannot be cited as enforced canon. See `examples/experimental/tenant-aware-pool/README.md`.

**Anti-patterns being deprecated:**
- Using `get_db()` without tenant context for production endpoints
- Using `organization_id` instead of `tenant_id` as the column name
- Ad-hoc tenant ID in raw SQL queries outside migrations/analytics
- Separate connection management per service with different pooling strategies
- `db_session()` context managers that do not execute `SET LOCAL app.tenant_id`

**Enforcement:**
- CI: `platform_contract_lint.py` flags `Depends(get_db)` in production routes
- Integration tests: Application-level and database-level RLS isolation tests
- Runtime: `validate_tenant_id()` rejects empty/malformed tenant IDs (fail-safe)

---

### 2.3 Middleware and Auth Flow

**Status:** `proposed` | **Target:** `ratified` 2026-05-23 | **Enforcement:** 2026-06-23

**Canonical Pattern:** Layered Middleware Stack with Declarable, Composable Phases

Request processing pipeline organized as strict ordered stack of eight phases. Each phase is a pure function that takes a context object and returns modified context or throws error.

**Contract Specification:**

| Phase | Order | Responsibility | Context Modifications | Can Terminate |
|-------|-------|---------------|----------------------|---------------|
| request_id | 1 | Assign x-request-id | Sets ctx.requestId | No |
| correlation | 2 | Extract/inject correlation IDs | Sets ctx.traceId, ctx.span | No |
| auth | 3 | Validate credentials, establish tenant context | Sets ctx.identity, ctx.tenantContext | Yes (401/403) |
| tenant_scope | 4 | Validate tenant access | May modify ctx.tenantContext.scope | Yes (403) |
| rate_limit | 5 | Apply rate limiting | No modifications | Yes (429) |
| validation | 6 | Validate request against OpenAPI | Sets ctx.validatedBody, ctx.validatedParams | Yes (400) |
| handler | 7 | Execute business logic | Sets ctx.result | Yes |
| response | 8 | Serialize response | Sets response body/headers | No |
| error_boundary | Global | Catch errors, normalize shape | Sets response body/status | Yes |

**Contract Rules:**
- Every route must declare required phases in route manifest
- Auth phase produces AuthContext; downstream code never re-validates [VERIFY:DOC-AUTH-001]
- Rate limiting keyed by tenant_id + endpoint_pattern + identity_hash
- Request/response validated against OpenAPI spec using generated validators
- Error responses follow canonical error shape (section 2.5)

**Anti-patterns being deprecated:**
- Inline app.use(middleware) scattered across route files
- Route handlers re-verifying authentication after middleware
- Per-route custom validation schemas duplicating OpenAPI
- Middleware sending HTTP responses directly instead of setting context

**Enforcement:**
- ESLint: `no-inline-middleware` - flags app.use() outside pipeline config
- CI: OpenAPI spec diff validation on PRs modifying routes
- Runtime: Middleware manifest validator at application startup

---

### 2.4 Tool Invocation Boundary

**Status:** `proposed` | **Target:** `ratified` 2026-05-23 | **Enforcement:** 2026-06-23

**Canonical Pattern:** Schema-First Unified Tool Registry with Generated Framework Bindings

Every tool is defined once as strongly-typed function with JSON Schema input contract and typed output. Framework bindings (LangChain, CrewAI, MCP) are thin auto-generated wrappers.

**Contract Specification:**

| Concern | Canonical Decision | Rationale |
|---------|-------------------|-----------|
| Tool definition | TypeScript function with typed inputs/outputs; JSON Schema generated | Single implementation; type safety; schema consistency |
| Tool registration | Central ToolRegistry with full metadata | Single discovery point; validation, permissions, observability |
| Framework binding | Thin auto-generated wrapper, max 10 lines, no logic | Eliminates duplicated business logic |
| Authentication | Tool inherits tenant context from orchestrating agent | No cross-tenant access possible |
| Error handling | Tool errors normalized to canonical shape | Agents can reason about failures |
| Observability | OpenTelemetry span per tool call with tool name, latency, tenant ID | Complete traceability |
| Tool description | Mandatory, min 50 chars, include when to use, when not, example | LLM selection accuracy |
| Input schema | JSON Schema with descriptions on every field; max 5-8 top-level params | LLM performance |

**Tool Output Contract (Canonical Shape):**

```typescript
interface ToolResult<T> {
  status: "success" | "error" | "partial";
  data?: T;
  error?: {
    code: string;
    message: string;
    recoverable: boolean;
    details?: Record<string, unknown>;
  };
  metadata: {
    execution_time_ms: number;
    tenant_id: string;
    tool_version: string;
    trace_id: string;
  };
}
```

**Anti-patterns being deprecated:**
- Tools defined as inline lambdas in agent configuration
- Framework-specific tool definitions duplicating business logic
- Tools throwing JavaScript exceptions instead of structured errors
- Tools accessing tenant context via function parameters
- Tools with ambiguous or missing JSON Schema descriptions

**Enforcement:**
- ESLint: `no-inline-tool-definition` - flags tool implementations outside tools/ directory
- ESLint: `no-throw-in-tool` - flags throw statements in tool implementations
- CI: Tool registry validation at build time
- CI: Framework binding parity check

---

### 2.5 Agent Output Shape and Traceability

**Status:** `proposed` | **Target:** `ratified` 2026-05-23 | **Enforcement:** 2026-06-23

**Canonical Pattern:** Structured Generation with Pydantic Schema Enforcement and OpenTelemetry Tracing

All agent outputs produced through structured generation using function calling/tool use mode with defined Pydantic schema. Raw text generation reserved for conversational endpoints only.

**Contract Specification:**

| Concern | Canonical Decision | Rationale |
|---------|-------------------|-----------|
| Output mode | Structured tool-use with Pydantic schema | Schema enforcement at generation time |
| Schema validation | Pydantic model_validate() on every output | Catches violations; errors fed back for retry |
| Retry policy | Max 2 retries on validation failure; return typed default after | Prevents infinite loops; ensures structured response |
| Traceability | OpenTelemetry spans for planning, tool selection, execution, validation | Complete visibility |
| Session management | Session ID via x-fabric-session-id; state changes as OTel span events | Cross-request continuity |
| Output persistence | Every output stored with session ID, trace ID, input hash, output JSON | Audit trail; replay testing |
| Raw text fallback | Only for endpoints marked output_mode: "text" | Prevents accidental unstructured output |
| Model version pinning | Exact model version specified; changes require config update | Prevents silent behavior changes |

**Canonical Agent Output Shape:**

```typescript
interface AgentOutput<T> {
  result: T;
  reasoning?: string;
  tool_calls: ToolCall[];
  confidence: number;
  trace_id: string;
  session_id: string;
  metadata: {
    model: string;
    model_version: string;
    latency_ms: number;
    token_usage: { prompt: number; completion: number; total: number };
    validation_passed: boolean;
    retry_count: number;
    finish_reason: string;
  };
}

interface ToolCall {
  tool_name: string;
  input_hash: string;
  output_status: "success" | "error" | "partial";
  latency_ms: number;
  span_id: string;
}
```

**Anti-patterns being deprecated:**
- JSON mode or raw text parsing of agent outputs
- Inline JSON.parse() calls on LLM response variables
- Agent runs without trace IDs or session correlation
- Storing raw prompts/completions in application logs (PII exposure)

---

### 2.6 Canonical API Error Envelope

**Status:** `ratified` | **Enforcement:** immediate

All HTTP APIs must return the same top-level error envelope for 4xx/5xx responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "request_id": "req_abc123",
    "details": {
      "safe_metadata_only": true
    }
  }
}
```

Required guarantees:
- `error.code` is machine-readable and stable.
- `error.message` is safe for consumers and does not leak internal state.
- `error.request_id` maps to trace/request correlation (`X-Request-ID` header).
- `error.details` is optional and must contain only sanitized metadata.

Common failure classes and canonical mapping:
- Validation failures → `422` + `VALIDATION_ERROR`
- Authentication failures → `401` + `AUTHENTICATION_ERROR`
- Authorization failures → `403` + `AUTHORIZATION_ERROR`
- Tenant boundary denials → `403` + `TENANT_ISOLATION_ERROR`
- Throttling/rate limits → `429` + `THROTTLED`
- Unhandled internal errors → `500` + `INTERNAL_ERROR`

---

### 2.7 UI State Progression and Route Model

**Status:** `proposed` | **Target:** `ratified` 2026-05-23 | **Enforcement:** 2026-06-23

**Canonical Pattern:** State-Machine-Driven Navigation with Declarative Route Manifests

UI state progression modeled as finite state machine where states correspond to pages/screens and transitions correspond to user actions or workflow events.

**Contract Specification:**

| Concern | Canonical Decision | Rationale |
|---------|-------------------|-----------|
| Routing model | URL path maps to state machine state; state machine determines valid transitions | Prevents invalid state navigation |
| State definition | id, route (URL pattern), guards, onEnter, transitions | Complete declarative specification |
| Navigation API | navigate(toState, params?) - validates transition before executing | Invalid transitions are no-ops with warnings |
| Deep linking | URL translated to state on load; redirect if invalid | Supports bookmarking |
| Route guards | Pure functions reading tenant context; no side effects | Deterministic, testable |
| Back navigation | Uses state machine history stack, not browser history | Respects workflow constraints |
| Programmatic navigation | Only via navigate(); no direct URL manipulation | Centralized for logging/analytics |

**Route Manifest Pattern:**

```typescript
const routeManifest: RouteManifest = {
  "/dashboard": {
    state: "dashboard",
    guards: [requireTenantContext, requireActiveSession],
    onEnter: [trackPageView("dashboard"), fetchDashboardData],
    transitions: {
      "VIEW_ANALYTICS": "analytics",
      "MANAGE_SETTINGS": "settings",
    },
  },
};
```

**Anti-patterns being deprecated:**
- Imperative router.push("/path") calls scattered through handlers
- Route guards performing API calls or mutations
- URL string concatenation for path construction
- Browser history as source of truth for workflow state
- Components rendering based on direct URL parsing

**Enforcement:**
- ESLint: `no-imperative-navigation` - flags router.push(), history.push(), direct navigate()
- ESLint: `no-url-concatenation` - flags string concatenation producing URL-like paths
- CI: Route manifest validation at build time
- CI: Dead transition detection

---

## 3. Deliverables

### 3.1 Architecture Contract Document (CONTRACT.md)

**Location:** Repository root  
**Status:** ✅ COMPLETE  
**Acceptance Criteria:**
- [x] Status markers for all six canonical contracts
- [x] Each contract has decision, rationale, anti-patterns, enforcement subsections
- [x] Changelog section tracking every modification
- [ ] Decision log referencing ADRs (pending ADR-009)

### 3.2 Canonical Reference Implementation (/examples/canonical/)

**Location:** `/examples/canonical/`  
**Status:** ✅ COMPLETE  
**Required Files (11 total):**

| File | Purpose | Status | Lines |
|------|---------|--------|-------|
| middleware/pipeline.ts | Eight-phase middleware stack | ✅ Complete | 520 |
| db/session-manager.ts | Tiered isolation with pooled connections | ✅ Complete | 450 |
| context/tenant-context.ts | AsyncLocalStorage-based context | ✅ Complete | 440 |
| tools/registry.ts | Schema-first tool registration | ✅ Complete | 380 |
| tools/example-tool.ts | Complete tool implementation | ✅ Complete | 420 |
| agent/orchestrator.ts | Structured generation agent | ✅ Complete | 500 |
| ui/route-manifest.ts | State-machine route model | ✅ Complete | 480 |
| ui/guards.ts | Example route guards | ✅ Complete | 380 |
| errors/error-shape.ts | Canonical error shape | ✅ Complete | 350 |
| errors/error-boundary.ts | Error boundary | ✅ Complete | 520 |
| README.md | Documentation | ✅ Complete | 150 |

**Total:** ~3,690 lines of production-quality reference code

### 3.3 Lint and CI Enforcement Strategy

**Location:** `eslint-plugin-fabric-contracts/`, `.github/workflows/contract-compliance.yml`  
**Status:** 🔄 IN PROGRESS  
**Three Layers:**

1. **IDE and local development:** Custom ESLint plugin with immediate inline feedback
2. **Pre-commit hooks:** Husky + lint-staged on staged files
3. **CI gate:** Full lint suite + contract validation scripts

**Custom ESLint Rules (12 total):**

| Rule ID | Targets | Severity |
|---------|---------|----------|
| no-tenant-id-parameter | Function parameters named tenantId variants | Error |
| no-req-tenant-access | Direct header access outside auth middleware | Error |
| no-raw-tenant-query | Raw SQL with tenant_id outside migrations | Error |
| no-explicit-db-connect | db.connect() with tenant identifiers | Error |
| no-inline-middleware | app.use() outside pipeline config | Error |
| no-inline-tool-definition | Tools outside tools/ directory | Error |
| no-throw-in-tool | throw in tool implementations | Error |
| no-json-parse-agent-output | JSON.parse() on LLM responses | Error |
| no-imperative-navigation | router.push(), history.push() | Error |
| no-url-concatenation | URL string concatenation | Error |
| no-private-imports | Deep imports bypassing public API | Error |
| no-circular-dependencies | Circular package imports | Error |

### 3.4 Deprecation Map (DEPRECATIONS.md)

**Location:** Repository root  
**Status:** ✅ COMPLETE  
**Migration Strategies:**
- **Strangler Fig:** Parallel operation, incremental shift (most common)
- **Adapter:** Compatibility layer exposing old interface, delegating to new
- **Big-bang:** Coordinated sprint refactoring all instances (rare)

**Contents:**
- 10 deprecated patterns identified with migration paths
- Instance counts and owning teams tracked
- Weekly auto-update command documented
- Compliance dashboard with per-service scores

---

## 4. Acceptance Criteria

### 4.1 Contract Documentation
- [x] CONTRACT.md exists at repository root with six canonical contracts
- [x] Each contract has decision, rationale, anti-patterns, enforcement subsections
- [ ] Status markers accurately reflect implementation state
- [ ] Changelog contains dated entries for all modifications
- [ ] Decision log references specific ADRs

### 4.2 Reference Implementation
- [x] /examples/canonical/ exists with all 11 specified files (~3,690 lines)
- [ ] Compiles without errors (requires @types/node for standalone files)
- [ ] Passes dedicated test suite (100%) - tests to be added
- [x] New developer can scaffold tool by copying example-tool.ts (<10 lines to modify)
- [ ] Integration test suite imports and validates reference

### 4.3 Enforcement
- [ ] All 12 custom ESLint rules implemented
- [ ] `npm run lint` fails with exit code 1 on violations
- [ ] Error messages reference CONTRACT.md sections
- [ ] CI pipeline includes lint step
- [ ] CI includes 4 validation scripts
- [ ] No false positives on legitimate patterns

### 4.4 Deprecation
- [x] DEPRECATIONS.md exists with all required entries (10 patterns tracked)
- [x] Every entry has all required columns (7 columns per entry)
- [ ] At least one deprecated pattern fully removed (pending migration)
- [ ] Weekly automated report generates instance counts (script exists)
- [x] Dashboard shows compliance score per service (documented in DEPRECATIONS.md)

### 4.5 Organizational Integration
- [ ] Architecture review checklist includes CONTRACT.md verification
- [x] Onboarding docs include canonical contract section (`CONTRIBUTING.md`)
- [x] PR templates include contract compliance checkbox (`.github/pull_request_template.md`)
- [x] Engineering wiki has contract governance page (`docs/governance.md`, `docs/governance/launch-drift-prevention-sop.md`)
- [ ] Quarterly review meeting scheduled

---

## 5. Why This Is the Highest ROI Move

This investment converts Fabric 4L from a smart evolving codebase into a governed product platform. That conversion produces velocity without chaos — the ability to move fast because the path is clear, not because the constraints are absent.

**Measurable impact within one quarter:**

| Metric | Current State | Target | Measurement |
|--------|--------------|--------|-------------|
| Time to implement new tool | 2-3 days | 4 hours | Engineering time tracking |
| Cross-tenant data leak incidents | 1/quarter | Zero | Security incident tracker |
| Architecture review rounds per PR | 2.3 avg | 1.0 | PR analytics |
| New engineer time to first correct PR | 3 weeks | 5 days | Onboarding survey |
| Deprecated pattern instances | Growing | -20%/quarter | Weekly static analysis |
| CI failure rate from contract violations | Not measured | Zero | CI analytics |

These savings compound quarter over quarter.

---

## Appendix A: Anti-Pattern Detection Heuristics

| Anti-Pattern | AST Selector |
|--------------|-------------|
| tenantId parameter | FunctionDeclaration > Identifier[name=/tenant[_-]?id/i] |
| Direct header access | MemberExpression[object.name='req'][property.value='headers'] |
| Raw tenant_id in query | TemplateElement[value.raw=/tenant_id/i] |
| Inline tool definition | Property[key.name='tools'] with function definitions |
| JSON.parse on LLM | CallExpression[callee.name='JSONParse'] |
| router.push | CallExpression[callee.property.name='push'] |
| URL concatenation | BinaryExpression[operator='+'] with "/" prefix |
| Private import | source.value matching `/@.*\/(src\|lib\|dist)\//` |
| Circular dependency | Graph analysis via eslint-plugin-import |

---

## Appendix B: Contract Status Definitions

| Status | Meaning | CI Behavior | IDE Behavior |
|--------|---------|-------------|--------------|
| proposed | Under discussion | Report-only; violations logged | Yellow underline |
| ratified | Decision made; team agrees | Warnings; dashboard tracks | Yellow underline |
| enforced | Fully canonical; violations are bugs | CI fails; PR blocked | Red squiggles |
| deprecated | Old pattern being phased out | Old pattern tracked | Info message |

Status progression: proposed → ratified → enforced

---

## Appendix C: Related Documents

| Document | Location | Relationship |
|----------|----------|--------------|
| ARCHITECTURE.md | Repository root | High-level architecture; references CONTRACT.md |
| adr/00XX-*.md | adr/ directory | Deliberation and alternatives analysis |
| DEPRECATIONS.md | Repository root | Living deprecation map |
| /examples/canonical/ | examples/canonical/ | Reference implementation |
| .github/workflows/contract-compliance.yml | .github/workflows/ | CI pipeline |
| eslint-plugin-fabric-contracts | Package registry | Custom ESLint rules |

---

## Document Metadata

- **Version:** 1.0
- **Status:** Proposed
- **Ratification target:** 2026-05-23
- **First enforcement target:** 2026-06-23
- **Next review:** Quarterly after enforcement
- **Author:** Platform Engineering
- **Approvers:** Architecture Review Board (pending)

---

## Changelog

| Date | Author | Change | Rationale |
|------|--------|--------|-----------|
| 2026-04-23 | Platform Team | Initial draft | Establish canonical contracts for six cross-layer concerns |
| 2026-04-25 | Platform Team | Ratify Section 2.2 | RLS via SET LOCAL ratified as Enforced Canon per Unified Recommendation memo; TenantAwarePool moved to experimental |
| 2026-05-13 | Platform Team | Close organizational governance controls | Link contributor onboarding, PR governance confirmations, and engineering governance SOP to the canonical contract |

## OpenAPI Dynamic Shape Guardrails (Type Safety)

To keep generated frontend API types free of `any` in response models, dynamic response structures must be modeled explicitly in OpenAPI:

- Use `oneOf` / `anyOf` (+ discriminator when practical) for polymorphic payloads.
- Use `type: object` + `additionalProperties` with a typed value schema for map/dictionary payloads.
- Avoid untyped object blobs (`{}` or free-form object) unless contract behavior requires opaque passthrough data.
- Response model updates must be followed by type regeneration (`pnpm --dir apps/web run generate:types`) and generated-type guard checks.

The repo now enforces a generated-response guard (`test:generated-response-types`) that fails if generated response schema entries regress to `Response: any` in L4/L5 type surfaces.
