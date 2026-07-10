# Architecture Decision Records

Fabric 4L maintains a transparent index of all Architecture Decision Records (ADRs) to document significant technical choices, their rationale, and their consequences. This page serves as the canonical index — each ADR links to its full document in the repository.

**Repository:** [`docs/adr/`](https://github.com/bmsull560/Fabric_4L/tree/main/docs/adr)  
**Format:** Markdown, following [ADR-000: ADR Template and Guidelines](https://github.com/bmsull560/Fabric_4L/blob/main/docs/adr/ADR-000-adr-template.md)  
**Status Key:** Accepted | Rejected | Superseded | Deprecated | Draft

---

## Active Decisions

The following decisions are currently in effect and govern the Fabric 4L architecture.

| ADR | Title | Status | Date | Consequences |
|-----|-------|--------|------|-------------|
| ADR-021 | DB Session Isolation | Accepted | 2026-04-25 | PostgreSQL RLS required for all tables |
| ADR-028 | Tenant Context Propagation | Accepted | 2026-07-10 | AsyncLocalStorage required; no tenantId in function params |
| ADR-029 | Middleware Auth Flow | Accepted | 2026-07-10 | 8-phase pipeline enforced on all requests |
| ADR-030 | Tool Invocation Boundary | Accepted | 2026-07-10 | Schema-first tool registry; no ad-hoc tool registration |
| ADR-031 | Agent Output Shape | Accepted | 2026-07-10 | Canonical envelope required for all agent outputs |
| ADR-032 | UI Route/State Progression | Accepted | 2026-07-10 | State machine validation on all route transitions |

---

### ADR-021: DB Session Isolation

**Date:** 2026-04-25  
**Status:** Accepted  
**Full Document:** [`docs/adr/ADR-021-db-session-isolation.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/adr/ADR-021-db-session-isolation.md)

**Summary:**  
All database sessions must use row-level security (RLS) policies tied to the current tenant context. Database connections are scoped per-request and automatically enforce tenant isolation at the database level rather than relying on application-layer filtering. This eliminates an entire class of multi-tenant data leakage bugs.

**Key Consequences:**
- PostgreSQL RLS policies must be defined on every tenant-scoped table
- Connection pool must support per-tenant context propagation
- Raw SQL queries must include tenant context or bypass RLS intentionally (logged)
- All migrations must include RLS policy definitions

**Relevant Code:**
- [`backend/db/session.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/db/session.py) — Session factory with RLS context
- [`backend/db/rls_policies.sql`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/db/rls_policies.sql) — RLS policy definitions
- [`backend/migrations/versions/0021_add_rls_policies.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/migrations/versions/0021_add_rls_policies.py) — Migration

---

### ADR-028: Tenant Context Propagation

**Date:** 2026-07-10  
**Status:** Accepted  
**Full Document:** [`docs/adr/ADR-028-tenant-context-propagation.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/adr/ADR-028-tenant-context-propagation.md)

**Summary:**  
Tenant context is propagated through the system using AsyncLocalStorage (Node.js) and Python context variables, eliminating the need to pass `tenantId` as an explicit parameter through every function call. The context is established at the middleware layer and flows automatically through async call chains.

**Key Consequences:**
- No function signatures may include `tenantId` as a parameter
- AsyncLocalStorage / contextvars must be used consistently
- Context must be set in middleware and propagated through message queues
- Logging automatically includes tenant context without manual annotation

**Relevant Code:**
- [`backend/middleware/tenant_context.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/middleware/tenant_context.py) — Tenant context middleware
- [`backend/core/context.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/core/context.py) — Context variable definitions
- [`frontend/src/lib/tenant-context.ts`](https://github.com/bmsull560/Fabric_4L/blob/main/frontend/src/lib/tenant-context.ts) — Frontend context propagation

---

### ADR-029: Middleware Auth Flow

**Date:** 2026-07-10  
**Status:** Accepted  
**Full Document:** [`docs/adr/ADR-029-middleware-auth-flow.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/adr/ADR-029-middleware-auth-flow.md)

**Summary:**  
Authentication and authorization are implemented as an 8-phase middleware pipeline: (1) Request ID assignment, (2) CORS handling, (3) Rate limit check, (4) Token extraction, (5) Token validation, (6) Tenant resolution, (7) Permission check, (8) Context attachment. Each phase is independently testable and can be short-circuited on failure.

**Key Consequences:**
- All 8 phases execute on every request (no skipping)
- Custom middleware must fit into the pipeline architecture
- Each phase emits structured telemetry for debugging
- Pipeline order is fixed; reordering requires ADR amendment

**Relevant Code:**
- [`backend/middleware/auth_pipeline.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/middleware/auth_pipeline.py) — 8-phase pipeline implementation
- [`backend/middleware/__init__.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/middleware/__init__.py) — Middleware registration
- [`backend/tests/middleware/test_auth_pipeline.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/tests/middleware/test_auth_pipeline.py) — Pipeline tests

---

### ADR-030: Tool Invocation Boundary

**Date:** 2026-07-10  
**Status:** Accepted  
**Full Document:** [`docs/adr/ADR-030-tool-invocation-boundary.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/adr/ADR-030-tool-invocation-boundary.md)

**Summary:**  
All agent tools must be registered through a schema-first tool registry. Tools define their input/output schemas via Pydantic models and are validated at registration time. No ad-hoc tool creation or dynamic tool binding is permitted — all tool invocations pass through the registry boundary.

**Key Consequences:**
- All tools require Pydantic input/output schemas
- Tool registry validates schemas at startup
- Tool calls are audited and rate-limited through the registry
- New tools must be registered before deployment (no runtime registration)

**Relevant Code:**
- [`backend/agents/tools/registry.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/agents/tools/registry.py) — Tool registry
- [`backend/agents/tools/schemas.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/agents/tools/schemas.py) — Tool schema definitions
- [`backend/agents/tools/boundary.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/agents/tools/boundary.py) — Invocation boundary validator

---

### ADR-031: Agent Output Shape

**Date:** 2026-07-10  
**Status:** Accepted  
**Full Document:** [`docs/adr/ADR-031-agent-output-shape.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/adr/ADR-031-agent-output-shape.md)

**Summary:**  
All agent outputs must conform to a canonical envelope format: `{ "version": "1.0", "metadata": {...}, "payload": {...}, "provenance": {...} }`. This ensures consistent handling of agent outputs across all consumers, enables automatic provenance tracking, and supports schema evolution without breaking changes.

**Key Consequences:**
- All agent outputs must include the canonical envelope
- Provenance metadata is automatically populated
- Consumers can rely on consistent top-level structure
- Version field enables future envelope evolution

**Relevant Code:**
- [`backend/agents/output/envelope.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/agents/output/envelope.py) — Envelope implementation
- [`backend/agents/output/provenance.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/agents/output/provenance.py) — Provenance tracking
- [`frontend/src/types/agent-output.ts`](https://github.com/bmsull560/Fabric_4L/blob/main/frontend/src/types/agent-output.ts) — TypeScript envelope types

---

### ADR-032: UI Route/State Progression

**Date:** 2026-07-10  
**Status:** Accepted  
**Full Document:** [`docs/adr/ADR-032-ui-route-state-progression.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/adr/ADR-032-ui-route-state-progression.md)

**Summary:**  
UI route transitions are validated against a state machine. Each route has defined valid predecessor states, and unauthorized transitions are blocked. This prevents users from accessing wizard steps out of order or skipping required configuration screens.

**Key Consequences:**
- Route definitions include allowed predecessor states
- State machine validation runs on every navigation attempt
- Deep links are validated against current state
- Invalid transitions redirect to the appropriate starting point

**Relevant Code:**
- [`frontend/src/lib/state-machine.ts`](https://github.com/bmsull560/Fabric_4L/blob/main/frontend/src/lib/state-machine.ts) — State machine implementation
- [`frontend/src/router/guards.ts`](https://github.com/bmsull560/Fabric_4L/blob/main/frontend/src/router/guards.ts) — Route guards
- [`frontend/src/router/state-rules.ts`](https://github.com/bmsull560/Fabric_4L/blob/main/frontend/src/router/state-rules.ts) — Route-to-state mapping

---

## Superseded Decisions

The following decisions have been replaced by newer ADRs. They are preserved for historical context but are no longer in effect.

| ADR | Title | Status | Superseded By | Reason |
|-----|-------|--------|---------------|--------|
| ADR-014 | Request Context Bag | Superseded | ADR-028 (Tenant Context Propagation) | Explicit context bag required too much boilerplate; AsyncLocalStorage provides cleaner propagation |
| ADR-018 | JWT Session Storage | Superseded | ADR-029 (Middleware Auth Flow) | Monolithic auth middleware became unmaintainable; 8-phase pipeline provides better separation |
| ADR-024 | Tool Decorator Pattern | Superseded | ADR-030 (Tool Invocation Boundary) | Decorator-based registration lacked schema validation; schema-first registry is safer |

### ADR-014: Request Context Bag

**Superseded by:** ADR-028 (2026-07-10)

The original approach used an explicit `RequestContext` dataclass that was passed as a parameter through every function call chain. While explicit, this created significant boilerplate and was error-prone — developers frequently omitted the context parameter. ADR-028 replaces this with implicit context propagation via AsyncLocalStorage, eliminating the boilerplate while maintaining full traceability.

**Migration Path:** All functions previously accepting `ctx: RequestContext` have been refactored to use `tenant_context.get_current_tenant()` instead. See [v1.1-to-v1.2 migration guide](/migrations/v1.1-to-v1.2) for details.

---

### ADR-018: JWT Session Storage

**Superseded by:** ADR-029 (2026-07-10)

The original authentication middleware was a single monolithic function handling all auth concerns. As the system grew, this became difficult to test and extend. ADR-029 decomposes auth into 8 independently testable phases, each with clear responsibilities and telemetry.

**Migration Path:** The monolithic `auth_middleware()` function is deprecated and will be removed in v2.0. All new endpoints use the pipeline. See the deprecation timeline in the full ADR document.

---

### ADR-024: Tool Decorator Pattern

**Superseded by:** ADR-030 (2026-07-10)

Tools were originally registered via a `@tool` Python decorator that introspected function signatures. This approach lacked compile-time schema validation and made it difficult to audit the complete tool inventory at startup. ADR-030 replaces this with an explicit schema-first registry.

**Migration Path:** All `@tool` decorators must be replaced with explicit `registry.register()` calls with Pydantic schemas. A migration script is available at `scripts/migrate-tool-decorators.py`.

---

## Deprecated Decisions

The following decisions are deprecated and scheduled for removal. They remain in the codebase for backward compatibility but should not be used in new code.

| ADR | Title | Status | Deprecation Date | Target Removal |
|-----|-------|--------|------------------|----------------|
| ADR-007 | SQLite Primary Store | Deprecated | 2026-01-15 | v2.0.0 |
| ADR-011 | Synchronous Worker Model | Deprecated | 2026-03-01 | v2.0.0 |
| ADR-016 | Inline Agent Configuration | Deprecated | 2026-05-20 | v1.3.0 |

### ADR-007: SQLite Primary Store

**Deprecation Date:** 2026-01-15  
**Target Removal:** v2.0.0

SQLite was the original primary data store for development environments. It has been replaced by PostgreSQL across all environments to ensure consistency between development and production. SQLite support remains for backward compatibility but is not tested in CI.

**Relevant Code:**
- [`backend/db/compat/sqlite.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/db/compat/sqlite.py) — Compatibility layer (marked deprecated)

---

### ADR-011: Synchronous Worker Model

**Deprecation Date:** 2026-03-01  
**Target Removal:** v2.0.0

The original worker model used synchronous Celery tasks. This has been replaced by an async worker model using `asyncio` and `arq` for better resource utilization and concurrency. Synchronous task definitions are still supported via a compatibility shim.

**Relevant Code:**
- [`backend/workers/sync_compat.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/workers/sync_compat.py) — Sync compatibility shim

---

### ADR-016: Inline Agent Configuration

**Deprecation Date:** 2026-05-20  
**Target Removal:** v1.3.0

Agent configurations were originally embedded inline in workflow definitions. This made configuration reuse impossible and led to configuration drift. All agent configurations now live in the configuration store and are referenced by ID. Inline configuration is still parsed but emits a deprecation warning.

**Relevant Code:**
- [`backend/agents/config/inline_compat.py`](https://github.com/bmsull560/Fabric_4L/blob/main/backend/agents/config/inline_compat.py) — Inline config parser (deprecated)

---

## Decision Statistics

| Metric | Count |
|--------|-------|
| Total ADRs | 33 |
| Active (Accepted) | 15 |
| Superseded | 3 |
| Deprecated | 3 |
| Draft | 2 |
| Rejected | 10 |

---

## How to Propose a New ADR

1. **Copy the template:** [`docs/adr/ADR-000-adr-template.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/adr/ADR-000-adr-template.md)
2. **Assign the next number:** Check the latest ADR in the repository
3. **Write the proposal:** Fill in all sections — context, decision, consequences
4. **Open a PR:** Submit to `bmsull560/Fabric_4L` with the `adr-proposal` label
5. **Review process:**
   - 1 Staff+ engineer must approve
   - 48-hour minimum review window
   - All CI checks must pass
6. **Ratification:** Merge to `main`; status changes from `Draft` to `Accepted`
7. **Update this index:** Add the new ADR to the appropriate table above

---

## How to Supersede an ADR

1. Write a new ADR that references the one being superseded
2. In the new ADR's "Consequences" section, explain why the old approach is inadequate
3. Update the superseded ADR's status to `Superseded` and add `Superseded By` field
4. Provide a migration path in both the new ADR and the migration guides
5. Update this index page

---

## Related Documentation

- [Architecture Overview](/explanations/architecture) — High-level system architecture
- [Six-Layer Model](/explanations/six-layer-model) — Detailed layer descriptions
- [Security Model](/explanations/security-model) — Security architecture and threat model
- [Migration Guides](/migrations/) — Version upgrade instructions
