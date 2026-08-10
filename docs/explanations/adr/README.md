---
title: "Architecture Decision Records (ADRs)"
category: "explanations"
audience: "advanced"
last-reviewed: "2026-06-23"
freshness: "current"
related: ["../why-knowledge-graph", "../../core-concepts/architecture", "../../core-concepts/security-model"]
---

# Architecture Decision Records (ADRs)

> **What are ADRs?**  
> Architecture Decision Records capture the context, decision, and consequences of significant architectural choices. They help new team members understand *why* we built things this way, not just *how*.

---

## When to Write an ADR

Write an ADR when a decision is durable, cross-cutting, or expensive to reverse.
At minimum, use an ADR for:

- **Layer boundaries or canonical runtime paths**: adding, removing, splitting, or renaming layer/service ownership, import roots, deployable service boundaries, or compatibility shims.
- **Cross-service contracts**: changing API shapes, event envelopes, schema ownership, generated clients, or service-to-service communication patterns.
- **Tenant isolation, security, or compliance posture**: changing authentication, authorization, tenant scoping, auditability, encryption, data retention, or fail-closed behavior.
- **Production infrastructure or managed-service strategy**: selecting or replacing databases, queues, object stores, hosting models, network topology, CI/CD gates, or runtime deployment patterns.
- **Agent, provider, or governance architecture**: changing provider boundaries, workflow orchestration, model governance, prompt/output contracts, or human approval gates.
- **Accepted exceptions or deprecations**: approving a temporary deviation from a platform rule, superseding an ADR, or setting a compatibility-removal timeline.

## When Not to Write an ADR

Do not write an ADR for changes that are fully explained by an existing ADR,
runbook, contract, or local implementation note. Prefer a normal PR description
or targeted documentation update for:

- Bug fixes that preserve existing behavior and contracts.
- Local implementation details that do not affect a public API, layer boundary, security control, or deployment model.
- Test-only changes that do not redefine release gates or policy.
- Operational instructions that belong in a runbook.
- One-off cleanup that does not create a reusable rule or lasting decision.

## ADR Review Criteria

An ADR is ready for review only when it includes:

- A clear problem statement and scope boundary.
- The concrete decision, status, date, and decision owner.
- The alternatives considered, including why rejected options were not chosen.
- The consequences for contracts, tenant isolation, security, operations, tests, and documentation.
- A validation or enforcement path, such as CI checks, architecture tests, contract tests, runtime guards, or manual evidence requirements.
- Any owner and follow-up obligations, including removal dates for temporary compatibility, exception, or migration decisions.

---

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](./ADR-001-fabric-harness-as-the-governed-execution-spine-for-agentic-value-workflows.md) | Fabric Harness as the Governed Execution Spine for Agentic Value Workflows | ✅ Accepted | — |
| [ADR-002](./ADR-002-six-layer-architecture.md) | Six-Layer Architecture | ✅ Accepted | 2025-01-15 |
| [ADR-003](./ADR-003-neo4j-pgvector-hybrid-graph-database.md) | Neo4j + pgvector Hybrid Graph Database | ✅ Accepted | 2025-02-01 |
| [ADR-004](./ADR-004-jwt-api-key-authentication-strategy.md) | JWT + API Key Authentication Strategy | ✅ Accepted | 2025-02-15 |
| [ADR-005](./ADR-005-ontology-guided-llm-extraction.md) | Ontology-Guided LLM Extraction | ✅ Accepted | 2025-03-01 |
| [ADR-006](./ADR-006-langgraph-for-agent-orchestration.md) | LangGraph for Agent Orchestration | ✅ Accepted | 2025-03-15 |
| [ADR-007](./ADR-007-openapi-typescript-generator-selection.md) | OpenAPI TypeScript Generator Selection | ✅ Accepted | 2026-05-05 |
| [ADR-008](./ADR-008-opentelemetry-for-observability.md) | OpenTelemetry for Observability | ✅ Accepted | April 2026 |
| [ADR-009](./ADR-009-jwt-api-key-hybrid-authentication.md) | JWT + API Key Hybrid Authentication | ✅ Accepted | April 2026 |
| [ADR-010](./ADR-010-postgresql-rls-for-multi-tenancy.md) | PostgreSQL + RLS for Multi-Tenancy | ✅ Accepted | April 2026 |
| [ADR-011](./ADR-011-langgraph-for-workflow-orchestration.md) | LangGraph for Workflow Orchestration | ✅ Accepted | April 2026 |
| [ADR-012](./ADR-012-circuit-breaker-pattern-for-external-service-resilience.md) | Circuit Breaker Pattern for External Service Resilience | ✅ Accepted | April 2026 |
| [ADR-013](./ADR-013-repository-pattern-for-data-access.md) | Repository Pattern for Data Access | ✅ Accepted | April 2026 |
| [ADR-014](./ADR-014-multi-layer-architecture-vs-monolith.md) | Multi-Layer Architecture vs Monolith | ✅ Accepted | April 2026 |
| [ADR-015](./ADR-015-opentelemetry-for-observability.md) | OpenTelemetry for Observability | ✅ Accepted | April 2026 |
| [ADR-016](./ADR-016-neo4j-for-knowledge-graph-storage.md) | Neo4j for Knowledge Graph Storage | ✅ Accepted | April 2026 |
| [ADR-017](./ADR-017-jwt-api-key-hybrid-authentication.md) | JWT + API Key Hybrid Authentication | ✅ Accepted | April 2026 |
| [ADR-018](./ADR-018-layer-5-canonical-source.md) | Layer 5 Canonical Source | ✅ Accepted | — |
| [ADR-019](./ADR-019-replayability-event-envelope-and-layer-4-replay-harness.md) | Replayability Event Envelope and Layer 4 Replay Harness | ✅ Accepted | — |
| [ADR-020](./ADR-020-layer-2-5-signal-refinery.md) | Layer 2.5 Signal Refinery | ✅ Accepted | 2026-05-22 |
| [ADR-021](./ADR-021-layer-3-canonical-runtime-path.md) | Layer 3 Canonical Runtime Path | ✅ Accepted | 2026-05-13 |
| [ADR-022](./ADR-022-layer4-internal-decomposition.md) | Layer 4 Internal Decomposition | Proposed | 2026-05-22 |
| [ADR-023](./ADR-023-billing-service-extraction.md) | Billing Service Extraction | Superseded by Layer 7 ownership rationalization | 2026-05-29 |
| [ADR-024](./ADR-024-circuit-breaker-inventory.md) | Circuit Breaker Inventory | ✅ Accepted | 2026-05-27 |
| [ADR-025](./ADR-025-layer-25-signal-refinery.md) | Layer 2.5 Signal Refinery as Official Architecture Extension | ✅ Accepted | 2026-06-10 |
| [ADR-026](./ADR-026-deterministic-entity-id-generation.md) | Deterministic Entity ID Generation | ✅ Accepted | — |
| [ADR-027](./ADR-027-shim-removal.md) | Namespace Shim Removal | ✅ Accepted | 2026-06-04 |
| [ADR-028](./ADR-028-tenant-context-ratification.md) | Tenant Context Propagation Contract Ratification | ✅ Accepted | 2026-07-10 |
| [ADR-029](./ADR-029-middleware-auth-ratification.md) | Middleware and Auth Flow Contract Ratification | ✅ Accepted | 2026-07-10 |
| [ADR-030](./ADR-030-neo4j-hosting-decision.md) | Neo4j Hosting Decision | ✅ Accepted | 2026-06-23 |
| [ADR-031](./ADR-031-agent-output-ratification.md) | Agent Output Shape and Traceability Contract Ratification | ✅ Accepted | 2026-07-10 |
| [ADR-032](./ADR-032-ui-route-state-ratification.md) | UI Route/State Progression Contract Ratification | ✅ Accepted | 2026-07-10 |
| [ADR-033](./ADR-033-tool-boundary-ratification.md) | Tool Invocation Boundary Contract Ratification | ✅ Accepted | 2026-07-10 |
| [ADR-034](./ADR-034-request-context-contract.md) | RequestContext Contract Definition | ✅ Accepted | 2026-05-25 |
| [ADR-035](./ADR-035-verified-tenant-context-boundary.md) | Verified Tenant Context Boundary | Accepted — partially implemented | 2026-07-20 |
| [ADR-036](./ADR-036-tenant-bound-graph-query-execution.md) | Tenant-Bound Graph Query Execution | Proposed | 2026-07-20 |
| [ADR-037](./ADR-037-separation-of-workflow-state-context-and-orchestration.md) | Separation of Workflow State, Context, and Orchestration | Proposed | 2026-07-20 |
| [ADR-038](./ADR-038-externalized-secret-management-and-automated-detection.md) | Externalized Secret Management and Automated Secret Detection | Accepted — partially implemented | 2026-07-20 |

---

## ADR Template

```markdown
# ADR-XXX: [Title]

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-YYY

**Date:** YYYY-MM-DD

**Deciders:** [Names]

---

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing or have agreed to implement?

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive
- 

### Negative
- 

### Neutral
- 

## Alternatives Considered

### [Alternative 1]
- Pros: 
- Cons: 
- Why rejected: 

## Related

- Links to related ADRs
- Links to implementation docs
```

---

## When To Write An ADR

Create or update an ADR when a change makes a durable architecture decision that future contributors need to understand. Use ADRs for changes that:

- Change layer boundaries, canonical runtime paths, deployable service ownership, or cross-service communication patterns.
- Change authentication, authorization, tenant isolation, data residency, encryption, secrets, or other security-critical behavior.
- Add, remove, or extend compatibility shims, facade layers, public API contracts, generated client contracts, or migration/deprecation policy.
- Select or replace core infrastructure, storage, messaging, orchestration, observability, AI provider, or package/runtime tooling.
- Introduce production rollout, rollback, resilience, disaster recovery, or managed-service posture that operators must follow.
- Resolve a recurring governance dispute where code comments or implementation-only documentation would not preserve the rationale.

Do not create an ADR for routine implementation details, local refactors that do not change ownership or contracts, small bug fixes, test-only changes, or documentation wording updates unless they encode one of the decision types above.

Every new ADR must include status, date, deciders or owning roles, context, decision, consequences, alternatives considered, related implementation paths, and validation evidence or the gate that will prove the decision.

---

## Contributing

To propose a new ADR:

1. Copy the template above
2. Use the next sequential ADR number (`ADR-###-slug.md`)
3. Submit for review via PR
4. Update this index

---

*Last updated: 2026-07-20*
