---
title: "ADR-037: Separation of Workflow State, Context, and Orchestration"
category: "architecture"
audience: "advanced"
last-reviewed: "2026-07-20"
freshness: "current"
related: ["../../explanations/adr/ADR-006-langgraph-for-agent-orchestration", "../../explanations/adr/ADR-011-langgraph-for-workflow-orchestration", "../../explanations/adr/ADR-022-layer4-internal-decomposition", "../../explanations/adr/ADR-028-tenant-context-ratification"]
---

# ADR-037: Separation of Workflow State, Context, and Orchestration

**Status:** Proposed

**Date:** 2026-07-20

**Deciders:** Platform Engineering, Agent Engineering

---

## Context

The Layer 4 workflow executor (`services/layer4-agents/src/layer4_agents/engine/executor.py`)
combines three distinct responsibilities in a single module: workflow state
management, request/workflow context lifecycle, and task orchestration. This
module is 1,540 NLOC with cyclomatic complexity 24, has received 26 commits in
90 days, and is a confirmed bug magnet with 4 fixes in 6 months. The
`_set_workflow_request_context` and `_reset_workflow_request_context` symbols
are among the top bug-magnet symbols identified by repowise.

Context leakage between concurrent workflows is a known risk because context
set/reset logic is interleaved with orchestration code. A structural split
alone will not resolve context leakage — the separation must be accompanied by
clear lifecycle semantics.

This ADR establishes a durable architectural pattern for workflow execution
responsibilities. The current module names are examples of the initial
implementation, not normative references.

## Decision

### Architectural Rule

Workflow execution is decomposed into three distinct responsibilities with an
acyclic dependency direction: state management, context lifecycle, and task
orchestration. The orchestrator requests transitions; only the state-machine
component validates and commits transition semantics.

### Three Responsibilities

1. **State transition model:** Transition validity checking, state persistence,
   and recovery from partial execution. The state machine owns the transition
   lifecycle — no other component may mutate workflow state directly.

2. **Request/workflow context lifecycle:** Context establishment, propagation,
   cleanup, and cancellation safety. Context is managed as an independent
   lifecycle, not as a side-effect of orchestration.

3. **Task orchestration:** Task dispatch, result aggregation, and coordination
   of external side-effects. The orchestrator depends on the state machine and
   context boundary but does not own either.

### Dependency Direction (Acyclic)

```
facade/API
    ↓
orchestrator
    ↓
state machine + context boundary
    ↓
ports/interfaces
    ↓
persistence and external adapters
```

- State machine code must not import orchestrator or request-layer implementation.
- Context boundary code must not import orchestrator implementation.
- The orchestrator imports both state machine and context boundary.
- This direction prevents cycles and ensures that state and context logic can
  be tested without instantiating the orchestrator.

### State-Machine Ownership

- The orchestrator requests transitions; only the state-machine component
  validates and commits transition semantics.
- Transitions are validated before side effects are executed.
- Persistence is performed by the state machine, not the orchestrator.
- Retries are idempotent — replaying a transition for the same workflow step
  produces the same state.
- Recovery from partial execution: the state machine can resume from the last
  persisted state without re-executing completed steps.
- The orchestrator cannot mutate state directly; it must request transitions
  through the state machine API.

### Context Lifecycle Semantics

- Uses `contextvars` (Python) or language-equivalent for request-scoped context.
- Token-based reset (not flag-based) — cleanup in `finally` blocks.
- Cancellation safety — context is cleaned up on `asyncio.CancelledError` and
  `GeneratorExit`.
- No context leakage between concurrent workflows — each workflow has its own
  context scope.
- Propagation into spawned tasks is explicit, not implicit. Spawning a task
  without explicitly propagating context results in a null context, not
  inherited context.
- Behavior for resumed workflows: context is re-established from persisted
  state, not inherited from a stale scope.
- Exception safety: context is cleaned up regardless of whether the workflow
  completes normally, raises, or is cancelled.

### Re-exports Are Temporary

The original module becomes a thin facade that re-exports public symbols from
the extracted modules. Re-exports serve backward compatibility only:

- Public API of the facade remains unchanged — all existing imports continue
  to work.
- Internal imports are prohibited from using the compatibility facade.
- Deprecation warnings are emitted on facade usage.
- A removal milestone is defined in the migration plan (not in this ADR).

### Current Implementation Examples (Non-Normative)

These module names are the initial implementation of this pattern. They may
change without amending this ADR:

- `engine/executor.py` → facade
- `engine/state_machine.py` → state transitions
- `engine/context.py` → context lifecycle
- `engine/orchestrator.py` → task dispatch

## Alternatives Considered

### Single monolithic executor

- **Pros:** Single file to navigate; no cross-module imports; no re-export maintenance.
- **Cons:** 1,540 NLOC, CCN 24, 26 commits/90d, 4 bug fixes in 6mo; complexity and churn make it a defect magnet; context leakage risk from interleaved concerns; untestable in isolation.
- **Why rejected:** The module's complexity metrics (CCN 24, 1,540 NLOC, 4 bug fixes in 6 months) demonstrate that the current structure is unsustainable.

### Two-way split (state + execution)

- **Pros:** Fewer modules; simpler dependency graph.
- **Cons:** Context lifecycle is a distinct concern from both state and orchestration; merging context into either creates coupling that makes testing and reasoning harder; context set/reset bugs (the current bug magnets) would remain in whichever module absorbs them.
- **Why rejected:** The bug magnets are specifically in context management — it must be separated to be properly tested and fixed.

### Event-sourced state machine

- **Pros:** Full audit trail and replay; natural fit for workflow recovery; durable state without custom persistence.
- **Cons:** Adds infrastructure complexity (event store, projection, snapshotting); operational overhead; learning curve; over-engineered at current workflow volume.
- **Why rejected:** Current scale does not justify the infrastructure. Revisit if workflow volume exceeds 10k/day or if full audit trail becomes a compliance requirement.

### External workflow engine (Temporal, Cadence)

- **Pros:** Durability and replay out of the box; battle-tested; reduces custom infrastructure.
- **Cons:** New operational dependency; limits flexibility in workflow definition; vendor lock-in risk; team must learn new paradigm; may not integrate cleanly with existing LangGraph orchestration (ADR-006, ADR-011).
- **Why rejected:** Current LangGraph integration is established and functional. Revisit if cross-service workflow orchestration becomes a primary requirement or if durability guarantees exceed what custom state management can provide.

### Conditions for revisiting

- If workflow volume exceeds 10k/day, revisit event-sourced state machine.
- If cross-service workflow orchestration becomes primary, revisit external workflow engine.
- If context leakage incidents recur after separation, revisit context lifecycle implementation (possibly moving to a more restrictive scope model).

## Consequences

### Positive

- **Independent testability:** Each responsibility can be tested in isolation
  without instantiating the others.
- **Reduced churn:** Changes to state logic do not touch orchestration code,
  reducing merge conflicts and review burden.
- **Bug isolation:** Fixes are scoped to the relevant module, reducing
  regression risk.
- **Context leakage prevention:** Separating context lifecycle from
  orchestration makes leakage detectable and preventable by construction.
- **Clear ownership:** State machine owns transitions; context boundary owns
  lifecycle; orchestrator owns dispatch. No ambiguity.

### Negative

- **More modules to navigate:** Developers must understand the dependency
  direction and which module owns which responsibility.
- **Re-export maintenance:** The facade must be maintained until the removal
  milestone, with deprecation warnings.
- **Migration sequencing:** Extraction must be done carefully to avoid
  breaking existing imports; requires intermediate testing at each step.

## Compliance and Migration

### Existing noncompliant paths

`services/layer4-agents/src/layer4_agents/engine/executor.py` — single module
combining all three responsibilities.

### Migration owner

Agent Engineering

### Enforcement mechanism

- **Architectural conformance test:** Verifies acyclic dependency direction
  between extracted modules (planned).
- **Context leakage test:** Concurrent workflows do not cross-contaminate
  context (planned).
- **Test coverage:** Each extracted module has independent test files (planned).

### Rollback strategy

The facade preserves backward compatibility. If extraction introduces
regressions, the original module can be restored by removing the extracted
modules and reverting the facade to the original implementation.

### Evidence required to transition to Accepted

- Dependency direction test passes (no cyclic imports)
- Context leakage test passes (concurrent workflows do not cross-contaminate)
- Each extracted module has independent test files
- No internal imports use the compatibility facade
- Deprecation warnings emitted on facade usage

## Current Enforcement (Exists)

- None — the current monolithic executor has no structural separation enforcement.

## Planned Enforcement (Not Yet Existing)

- Architectural conformance test for acyclic dependency direction
- Context leakage test for concurrent workflow isolation
- Module-level test coverage for each extracted responsibility

## References

- ADR-006: LangGraph for Agent Orchestration
- ADR-011: LangGraph for Workflow Orchestration
- ADR-022: Layer 4 Internal Decomposition (service-level decomposition, complementary to this module-level separation)
- ADR-028: Tenant Context Propagation Contract (context lifecycle patterns)
- `services/layer4-agents/src/layer4_agents/engine/executor.py` (current implementation — motivates this ADR)
