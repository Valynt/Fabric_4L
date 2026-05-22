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
| [ADR-001](./ADR-001-six-layer-architecture.md) | Six-Layer Architecture | ✅ Accepted | 2025-01-15 |
| [ADR-002](./ADR-002-hybrid-graph-database.md) | Neo4j + pgvector Hybrid Graph | ✅ Accepted | 2025-02-01 |
| [ADR-003](./ADR-003-authentication-strategy.md) | JWT + API Key Authentication | ✅ Accepted | 2025-02-15 |
| [ADR-004](./ADR-004-ontology-extraction.md) | Ontology-Guided LLM Extraction | ✅ Accepted | 2025-03-01 |
| [ADR-005](./ADR-005-agent-orchestration.md) | LangGraph for Agent Orchestration | ✅ Accepted | 2025-03-15 |
| [ADR-020](./ADR-020-layer2-5-signal-refinery.md) | Layer 2.5 Signal Refinery | ✅ Accepted | 2026-05-22 |

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
2. Use the next available ADR number
3. Submit for review via PR
4. Update this index

---

*Last updated: 2026-05-22*
