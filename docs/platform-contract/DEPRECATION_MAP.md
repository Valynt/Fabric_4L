# Fabric 4L Platform Contract - Deprecation Map

> Forbidden in new code. Migration deadlines are enforced by CI warnings that escalate to errors.

| Deprecated Pattern | Canonical Replacement | Migration Deadline | Notes | Migration Status | Validation |
|---|---|---|---|
| request.state.context | request.state.governance_context | 2026-05-15 | Layer 3 still uses old name | complete | `rg` scan across canonical runtime paths (no hits) |
| TenantContext (L4) | shared.identity.RequestContext | 2026-05-15 | services/layer4-agents/src/layer4_agents/tenant/context.py | waived-with-exception | DEP-EXC-2026-05-15-L4-TENANTCONTEXT |
| get_db() | get_db_from_context() | 2026-06-01 | Health checks excepted | waived-with-exception | DEP-EXC-2026-06-04-DB-CONTEXT |
| get_db_with_tenant() | get_db_from_context() | 2026-06-01 | Header-based session creation | waived-with-exception | DEP-EXC-2026-06-04-DB-CONTEXT |
| db_session() context manager | db_session_for_context() | 2026-06-01 | Background tasks | waived-with-exception | DEP-EXC-2026-06-04-DB-CONTEXT |
| get_tiered_db_session() | get_db_from_context() | 2026-06-15 | Tier routing not yet implemented | complete | `rg` scan across canonical runtime paths (no hits); deprecated surface retained for compatibility tests only |
| get_db_with_optional_tenant() | get_db_from_context() + require_super_admin() | 2026-06-15 | Admin routes only | complete | `rg` scan across canonical runtime paths (no hits); deprecated surface retained for compatibility tests only |
| Layer 3 AuthenticationMiddleware | shared.identity.GovernanceMiddleware | 2026-05-15 | Remove duplicate middleware | waived-with-exception | DEP-EXC-2026-05-15-L3-AUTHMIDDLEWARE |
| Raw dict agent returns | AgentResultEnvelope | 2026-12-31 | Gradual migration | in-progress | Extended by S1-T1-CI-STABILIZE; migrations continue |
| ToolRegistry.execute() direct call | ToolGateway.execute() | 2026-08-31 | Agents must use ctx['tool_gateway'] | waived-with-exception | DEP-EXC-2026-07-17-TOOL-REGISTRY |
| GraphRAGEngine.query() direct call | MemoryGateway.query() | 2026-07-15 | Agents must use ctx['memory_gateway'] | complete | MemoryGateway wired into BaseAgent.run() and ConversationService gate context; tests in services/layer4-agents/tests/test_base_agent_memory_gateway.py |
| datetime.utcnow() | datetime.now(timezone.utc) | 2026-06-01 | Deprecated in Python 3.12 | waived-with-exception | DEP-EXC-2026-06-04-UTCNOW |
| asyncio.get_event_loop().time() | asyncio.get_running_loop().time() | 2026-06-01 | Deprecated in Python 3.10 | waived-with-exception | DEP-EXC-2026-06-04-LOOP-TIME |
| useWorkflowStore + usePilotStore | useValuePilotStore (merged) | 2026-05-30 | Consolidate to one 7-step store | waived-with-exception | DEP-EXC-2026-06-04-VALUE-PILOT-STORE |
| window.location.href | useLocation from wouter | 2026-05-15 | Immediate | waived-with-exception | DEP-EXC-2026-05-15-WEB-HREF |
| React Context for server state | TanStack Query hooks | 2026-06-15 | Billing/Auth contexts excepted | waived-with-exception | DEP-EXC-2026-06-15-WEB-CONTEXT |
| `{"detail": ...}` error-only HTTP payloads | Canonical error envelope: `{"message","code","trace_id"}` | 2026-06-15 | Layer 1 keeps temporary `error=authentication_required` compatibility field for legacy clients | waived-with-exception | DEP-EXC-2026-06-15-ERROR-ENVELOPE |


## Release Checklist — Planned Release 2026-05-15

Entries with deadlines on or before **2026-05-15** (authoritative backlog from this map):

- [x] `request.state.context` → `request.state.governance_context` (deadline: 2026-05-15) — **complete**. Validation: `rg -n "request.state.context" value_fabric/layer*/ services/layer*/src/ apps/web/src/` returned no hits.
- [x] `TenantContext (L4)` → `shared.identity.RequestContext` (deadline: 2026-05-15) — **waived-with-exception**. Canonical Layer 4 alias removal is blocked by compatibility shims and shared error class naming collisions outside L4 request context usage.
- [x] `Layer 3 AuthenticationMiddleware` → `shared.identity.GovernanceMiddleware` (deadline: 2026-05-15) — **waived-with-exception**. `value_fabric/layer3/auth/middleware.py` still exports compatibility middleware required by legacy imports.
- [x] `window.location.href` → `useLocation from wouter` (deadline: 2026-05-15) — **waived-with-exception** for external billing redirects and telemetry-only URL capture; no internal navigation redirectors remain in canonical runtime paths.

Reference validation scope required by release policy:

- `value_fabric/layer*/`
- `services/layer*/src/`
- `apps/web/src/`

### Contract Exceptions Recorded for This Release Window

| Exception ID | Deprecation | Type | Owner | Risk | Expiry | Tracking |
|---|---|---|---|---|---|---|
| DEP-EXC-2026-05-15-L4-TENANTCONTEXT | `TenantContext (L4)` | TE | layer4-agents@valuefabric.ai | Medium: non-request-scoped naming compatibility can obscure contract intent | 2026-12-31 | PR: this change set + targeted release tests |
| DEP-EXC-2026-05-15-L3-AUTHMIDDLEWARE | `Layer 3 AuthenticationMiddleware` | TE | layer3-knowledge@valuefabric.ai | Medium: duplicate middleware surface can hide governance-context regressions | 2026-12-31 | PR: this change set + targeted release tests |
| DEP-EXC-2026-05-15-WEB-HREF | `window.location.href` | TE | web-platform@valuefabric.ai | Low: external redirect/telemetry usage only; navigation bypass risk constrained by scope | 2026-12-31 | PR: this change set + targeted release tests |
| DEP-EXC-2026-06-04-DB-CONTEXT | `get_db()`, `get_db_with_tenant()`, `db_session()` | TE | platform-engineering@valuefabric.ai | High: legacy DB dependency surfaces can obscure tenant-context ownership | 2026-06-30 | `docs/governance/deprecations.json` + release suite |
| DEP-EXC-2026-06-04-UTCNOW | `datetime.utcnow()` | TE | layer3-knowledge@valuefabric.ai | Medium: naive timestamp migration may affect persisted/API timestamp shape | 2026-06-30 | `docs/governance/deprecations.json` + release suite |
| DEP-EXC-2026-06-04-LOOP-TIME | `asyncio.get_event_loop().time()` | TE | platform-engineering@valuefabric.ai | Low: runtime loop API migration remains mechanical but overdue | 2026-06-30 | release suite |
| DEP-EXC-2026-06-04-VALUE-PILOT-STORE | `useWorkflowStore + usePilotStore` | TE | frontend-platform@valuefabric.ai | Medium: store consolidation touches user workflow state and needs frontend owner validation | 2026-06-30 | release suite |
| DEP-EXC-2026-06-15-WEB-CONTEXT | `React Context for server state` | TE | frontend-platform@valuefabric.ai | Medium: billing/auth contexts retain Context-based state; migration to TanStack Query requires frontend owner validation | 2026-07-15 | release suite |
| DEP-EXC-2026-06-15-ERROR-ENVELOPE | `{"detail": ...}` error-only HTTP payloads | TE | platform-engineering@valuefabric.ai | Low: Layer 1 legacy `error=authentication_required` compatibility field retained for existing clients; canonical envelope used elsewhere | 2026-07-15 | release suite |
| DEP-EXC-2026-07-17-TOOL-REGISTRY | `ToolRegistry.execute() direct call` | TE | agent-platform@valuefabric.ai | Medium: whitespace.py and roi_calculator.py workflows still call tool_registry.execute directly; migration to ToolGateway requires agent workflow owner validation. Time-boxed renewal recorded during CI-baseline incident repair (PR #1021) | 2026-08-31 | release suite |

## Layer 3 API Alias Deprecation Governance (Contract Council Tracked)

| Alias Field | Canonical Field | Contract Location | Target Removal Date | Owner | Migration Status | Contract Council Approval |
|---|---|---|---|---|---|---|
| `GraphNode.label` | `GraphNode.name` | `contracts/openapi/layer3-knowledge.json#/components/schemas/GraphNode` | 2026-10-01 | Layer 3 Knowledge Team | In progress — compatibility still active, consumers migrating | Contract Council Decision CC-2026-04-18-L3-ALIASES |
| `GraphNode.type` | `GraphNode.entity_type` | `contracts/openapi/layer3-knowledge.json#/components/schemas/GraphNode` | 2026-10-01 | Layer 3 Knowledge Team | In progress — compatibility still active, consumers migrating | Contract Council Decision CC-2026-04-18-L3-ALIASES |
| `GraphNode.confidence` | `GraphNode.confidence_score` | `contracts/openapi/layer3-knowledge.json#/components/schemas/GraphNode` | 2026-10-01 | Layer 3 Knowledge Team | In progress — compatibility still active, consumers migrating | Contract Council Decision CC-2026-04-18-L3-ALIASES |
| `GraphEdge.relationship_type` | `GraphEdge.type` | `contracts/openapi/layer3-knowledge.json#/components/schemas/GraphEdge` | 2026-10-01 | Layer 3 Knowledge Team | In progress — compatibility still active, consumers migrating | Contract Council Decision CC-2026-04-18-L3-ALIASES |
| `FormulaMetadata.formula_id` | `FormulaMetadata.id` | `contracts/openapi/layer3-knowledge.json#/components/schemas/FormulaMetadata` | 2026-10-01 | Layer 3 Knowledge Team + UI Platform | In progress — compatibility alias documented with v2.5 removal target in OpenAPI | Contract Council Decision CC-2026-04-18-L3-ALIASES |

**Removal rule:** aliases above must not be deleted before (1) the listed target date has passed, and (2) Contract Council approval is explicitly recorded in this table.

## Recommendation Guardrail: Layer 3 + Layer 4 Agent Consolidation

Use this wording by default in architecture recommendations:

- **"Evaluate consolidation feasibility"**

Do **not** recommend direct consolidation of Layer 3 and Layer 4 agent implementations unless analysis confirms both are true:

1. **Platform contract compliance:** tenant context propagation, DB/session boundaries, and output envelope/tool boundary rules remain compliant after the change.
2. **Low-risk dependency impact:** Layer 3 agent responsibilities (graph traversal/projection, ROI calculation, whitespace analysis, provenance, narrative synthesis, and scenario modeling) can be consolidated without introducing breaking API/runtime coupling risk.

## Migration Guide

### 1. TENANT_CONTEXT -> governance_context

Find all instances:

```bash
grep -r "request.state.context" services/ packages/shared/src/value_fabric/shared/
```

Replace with `request.state.governance_context`.

### 2. get_db() -> get_db_from_context()

Find all instances:

```bash
grep -r "Depends\s*(\s*get_db\b" services/ packages/shared/src/value_fabric/shared/
grep -r "with\s+db_session\s*(" services/ packages/shared/src/value_fabric/shared/
grep -r "get_db_with_tenant" services/ packages/shared/src/value_fabric/shared/
grep -r "get_db_with_optional_tenant" services/ packages/shared/src/value_fabric/shared/
grep -r "get_tiered_db_session" services/ packages/shared/src/value_fabric/shared/
```

Replace endpoints to use `Depends(get_db_from_context)`.
Replace background tasks to use `db_session_for_context()`.

### 3. useWorkflowStore + usePilotStore -> useValuePilotStore

Merge functionality into a single store in `client/src/stores/valuePilotStore.ts`.
Deprecate the old stores.

### 4. ToolRegistry.execute() -> ToolGateway.execute() (GATE Phase 2)

Find all instances:

```bash
grep -rn "registry.execute\|tool_registry.execute" services/layer4-agents/
```

Replace with `ctx['tool_gateway'].execute(tool_name, input_data)` inside agent `execute()` methods.
The `ToolGateway` is automatically injected by `BaseAgent.run()` when `tool_registry` and `abom` are present in context.

### 5. GraphRAGEngine.query() -> MemoryGateway.query() (GATE Phase 3)

Find all instances:

```bash
grep -rn "graph_rag.*query\|retrieval_engine.*query" services/layer4-agents/
```

Replace with `ctx['memory_gateway'].query(query_text)` inside agent `execute()` methods.
The `MemoryGateway` must be created and injected into context by the orchestration layer.
