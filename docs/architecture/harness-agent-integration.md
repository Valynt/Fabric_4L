# Harness Agent Integration

## Overview

The Fabric Harness is the governed execution substrate for Layer 4 agentic workflows. It provides deterministic state machine transitions, human-in-the-loop gates, claim validation against Layer 5 Ground Truth, and full checkpoint/resume capability — all with strict tenant isolation.

The harness is **not** a replacement for LangGraph workflows. It is the control plane that governs how agent runs are created, advanced, validated, and published. LangGraph handles the execution graph; the harness handles lifecycle, governance, and auditability.

---

## Role in the Six-Layer Pipeline

```
Layer 1: Ingestion      — data sources, crawling, compliance
Layer 2: Extraction     — ontology-guided entity extraction
Layer 3: Knowledge      — Neo4j graph, hybrid retrieval
Layer 4: Agents  ◄───── Harness governs run lifecycle here
Layer 5: Ground Truth   — TruthObject validation (LiveL5Validator)
Layer 6: Benchmarks     — peer comparison, statistical validation
```

The harness sits at the Layer 4 boundary. It:
- Creates and tracks `HarnessRun` instances per tenant
- Enforces the state machine (INIT → … → DONE/FAILED/CANCELLED)
- Persists checkpoints at key states for replay and audit
- Blocks or degrades on validation failures before publishing output
- Emits structured trace events for every significant action

---

## Key Concepts

### HarnessRun

A `HarnessRun` represents a single execution of an agent workflow for a tenant. It carries:
- `workflow_type` — which workflow is being executed (e.g. `roi_calculator`, `business_case`)
- `current_state` — position in the state machine
- `status` — coarse lifecycle status (`running`, `waiting_for_human`, `failed`, `completed`, `cancelled`)
- `trace_id` — correlation ID for all events emitted during this run
- `tenant_id` — always set; all data access is scoped to this value

### State Machine

States progress linearly through the pipeline. Terminal states cannot be exited.

```
INIT
  └─► RESOLVE_CONTEXT
        └─► LOAD_VALUE_PACK
              └─► RETRIEVE_KNOWLEDGE
                    └─► GENERATE_HYPOTHESES
                          └─► MATCH_EVIDENCE
                                └─► QUANTIFY_IMPACT
                                      └─► VALIDATE_CLAIMS
                                            └─► HUMAN_REVIEW
                                                  └─► PUBLISH_OUTPUT
                                                        └─► DONE

Any state ──► FAILED
Any state ──► CANCELLED  (human_override=true required)
```

Transitions are validated by `StateMachine`. Invalid transitions raise `InvalidTransitionError`. Human override (`human_override=True`) bypasses policy checks for operator recovery.

### Checkpoints

A `HarnessCheckpoint` is written at configurable states (see `harness.runtime.yaml`). Each checkpoint stores:
- `state_name` — the state at which it was written
- `input_hash` — SHA-256 of the state payload, for deterministic replay verification
- `output_hash` — SHA-256 of the output, if available

Checkpoints enable replay: given a checkpoint, the harness can verify that re-running from that state with the same input produces the same output hash.

### Human Gates

A `HumanGate` blocks a run at a decision point until a human approves, rejects, modifies, or expires it. Gate types:
- `approve_claims` — validate claims before publishing
- `approve_assumptions` — review model assumptions
- `approve_customer_output` — final sign-off on customer-facing content
- `resolve_conflict` — resolve conflicting evidence

Gate lifecycle: `PENDING → APPROVED | REJECTED | MODIFIED | EXPIRED`

When a gate is decided, the run's status transitions from `waiting_for_human` back to `running` (on approval) or `failed` (on rejection).

### Validation Hook (LiveL5Validator)

The `ValidationHook` wraps a `ClaimValidator`. In production, `LiveL5Validator` is used:

1. Query `list_truths` scoped to `organization_id=request.tenant_id` (paginated, 100/page)
2. Match an existing `TruthObject` by normalized claim text
3. If found: map `TruthStatus → ValidationState`; downgrade stale approved truths to `NEEDS_REVIEW`
4. If not found: submit via `submit_truth`, return `NEEDS_REVIEW`
5. On any exception: return `INSUFFICIENT_EVIDENCE` — never raises, never silently approves

**TruthStatus mapping:**

| L5 TruthStatus | ValidationState |
|---|---|
| `extracted` | `NEEDS_REVIEW` |
| `supported` | `NEEDS_REVIEW` |
| `corroborated` | `NEEDS_REVIEW` |
| `approved` (fresh) | `PASSED` |
| `approved` (stale) | `NEEDS_REVIEW` |
| `disputed` | `FAILED` |
| anything else | `INSUFFICIENT_EVIDENCE` |

---

## Data Flow

```
Browser / UI
    │
    │  POST /v1/harness/runs
    │  GET  /v1/harness/runs/{id}
    │  POST /v1/harness/runs/{id}/transition
    │  POST /v1/harness/gates/{id}/decide
    │  POST /v1/harness/runs/{id}/validate
    ▼
FastAPI (src/api/routes/harness.py)
    │  tenant_id extracted from RequestContext (GovernanceMiddleware)
    │  SqlHarnessRegistry injected via get_harness_registry()
    ▼
SqlHarnessRegistry (src/harness/sql_stores.py)
    │  All reads/writes scoped to tenant_id
    │  Five SQL-backed stores: runs, gates, checkpoints, tools, events
    ▼
PostgreSQL (Alembic migration 031)
    │
    │  (on validate_claims)
    ▼
LiveL5Validator (src/harness/live_l5_validator.py)
    │  list_truths(organization_id=tenant_id)
    │  submit_truth(organization_id=tenant_id)
    ▼
Layer 5 Ground Truth Service (:8005)
    │
    └─► ValidationState returned to caller
```

---

## Tenant Isolation Model

Tenant isolation is enforced at every layer:

1. **API layer**: `tenant_id` is extracted from `RequestContext` set by `GovernanceMiddleware`. It is never read from the request body.
2. **Registry layer**: `validate_claims` cross-checks every `request.tenant_id` against the authenticated `tenant_id` and raises `HarnessRegistryError` on mismatch.
3. **Repository layer**: all SQL queries filter by `tenant_id`. The `TenantEnforcedAsyncSession` fails closed if SQL executes before tenant context is set.
4. **L5 layer**: `list_truths` and `submit_truth` are always called with `organization_id=request.tenant_id`. The `Layer5GroundTruthClient` constructor does not receive a fallback `tenant_id`.

---

## Security and RBAC

- All harness routes require authentication (`require_authenticated` dependency).
- The `harness.service.yaml` `security.required_role` field can restrict write endpoints to a specific RBAC role.
- Trace events are emitted for every state transition, gate decision, and validation outcome — providing a full audit trail.
- Secrets (`L5_SERVICE_TOKEN`, `DATABASE_URL`) are never committed; they are injected via environment variables or ExternalSecrets in production.

---

## Relationship to LangGraph Workflows

The existing `/v1/workflows/*` surface (LangGraph-backed) and `/v1/harness/*` (harness-backed) are **separate surfaces** for now. They share the same FastAPI app and authentication middleware but have independent persistence and state models.

Future work may bridge them: a LangGraph workflow could create a `HarnessRun` at startup and use the harness for checkpointing and gate management while LangGraph handles the execution graph.

---

## Extension Points

### Custom Validators

Implement `ClaimValidator` (async `validate()` and `health()`) and pass it to `ValidationHook(primary_validator=...)`. The `MockValidator` and `UnavailableValidator` in `validation_hooks.py` serve as reference implementations.

### New Workflow Types

Add a new entry to `HarnessWorkflowType` in `models.py` and a corresponding section in `harness.runtime.yaml`. No other changes are required.

### Pack Integration

Value packs can set `value_pack_id` on `HarnessRun` creation. The `LiveL5Validator` uses `value_pack_id` to infer `claim_type` for L5 queries (`roi_assumption`, `benchmark`, or `outcome`).

### CommandCenter Right-Rail

The `HarnessRunDetail` component is designed to be embeddable. To surface harness run status in the CommandCenter right-rail, import `HarnessRunDetail` and pass the relevant `runId`.

---

## API Reference

### Endpoints

All endpoints are under the `/v1/harness` prefix and require an authenticated tenant context.

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/harness/runs` | Create a new harness run |
| `GET` | `/v1/harness/runs` | List runs for the authenticated tenant |
| `GET` | `/v1/harness/runs/{run_id}` | Get a single run by ID |
| `POST` | `/v1/harness/runs/{run_id}/transition` | Advance or cancel a run's state |
| `DELETE` | `/v1/harness/runs/{run_id}` | Cancel a run (soft delete) |
| `GET` | `/v1/harness/runs/{run_id}/checkpoints` | List checkpoints for a run |
| `GET` | `/v1/harness/runs/{run_id}/checkpoints/latest` | Get the most recent checkpoint |
| `GET` | `/v1/harness/runs/{run_id}/gates` | List human gates for a run |
| `POST` | `/v1/harness/runs/{run_id}/gates` | Create a human gate on a run |
| `POST` | `/v1/harness/gates/{gate_id}/decide` | Approve or reject a gate (gate-scoped; `decision_by` derived from auth context) |
| `POST` | `/v1/harness/runs/{run_id}/validate` | Trigger claim validation via L5 |
| `GET` | `/v1/harness/health` | Harness component health check |

### Request / Response Models (`src/harness/api_models.py`)

| Model | Direction | Description |
|---|---|---|
| `CreateRunRequest` | Request | Fields to create a new `HarnessRun` |
| `RunResponse` | Response | Single run representation |
| `RunListResponse` | Response | Paginated list of runs |
| `TransitionRequest` | Request | State transition action and reason |
| `TransitionResponse` | Response | Updated run after transition |
| `CheckpointResponse` | Response | Single checkpoint |
| `CheckpointListResponse` | Response | List of checkpoints for a run |
| `CreateGateRequest` | Request | Fields to create a `HumanGate` |
| `GateResponse` | Response | Single gate representation |
| `GateListResponse` | Response | List of gates for a run |
| `GateDecisionRequest` | Request | Approve/reject decision with notes |
| `ClaimValidationRequest` | Request | Individual claim to validate |
| `ValidateClaimsRequest` | Request | Batch of claims to validate |
| `ValidationResultResponse` | Response | Single claim validation result |
| `ValidationSummaryResponse` | Response | Aggregate publish decision across validated claims |
| `ValidateClaimsResponse` | Response | Batch validation results |
| `HarnessHealthResponse` | Response | Health check payload |
| `TraceEventResponse` | Response | Single trace event |
