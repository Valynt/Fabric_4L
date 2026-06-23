---
title: "Architecture Decision Records (ADRs)"
category: "explanations"
audience: "advanced"
last-reviewed: "2026-04-19"
freshness: "current"
related: ["../why-knowledge-graph", "../../core-concepts/architecture", "../../core-concepts/security-model"]
---

# Architecture Decision Records (ADRs)

> **What are ADRs?**  
> Architecture Decision Records capture the context, decision, and consequences of significant architectural choices. They help new team members understand *why* we built things this way, not just *how*.

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
| [ADR-025](./ADR-025-layer-25-signal-refinery.md) | Layer 2.5 Signal Refinery as Official Architecture Extension | ✅ Accepted | 2026-06-10 |
| [ADR-027](./ADR-027-shim-removal.md) | Namespace Shim Removal | ✅ Accepted | 2026-06-04 |
| [ADR-028](./ADR-028-circuit-breaker-inventory.md) | Circuit Breaker Inventory | ✅ Accepted | 2026-05-27 |
| [ADR-029](./ADR-029-deterministic-entity-id-generation.md) | Deterministic Entity ID Generation | ✅ Accepted | — |
| [ADR-030](./ADR-030-neo4j-hosting-decision.md) | Neo4j Hosting Decision | Proposed | — |
| [ADR-031](./ADR-031-request-context-contract.md) | RequestContext Contract Definition | ✅ Accepted | 2026-05-25 |

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

## Contributing

To propose a new ADR:

1. Copy the template above
2. Use the next sequential ADR number (`ADR-###-slug.md`)
3. Submit for review via PR
4. Update this index

---

*Last updated: 2026-05-22*
