---
title: "ADR-002: Six-Layer Architecture"
category: "explanations"
audience: "advanced"
last-reviewed: "2026-05-27"
freshness: "current"
related: ["../../core-concepts/architecture", "../../reference/layer1-ingestion-api", "../why-knowledge-graph"]
---

# ADR-002: Six-Layer Architecture

**Status:** ✅ Accepted

**Date:** 2025-01-15

**Deciders:** Architecture Team, Engineering Leads

---

## Context

We needed to design a platform that could:
1. Ingest unstructured web content at scale
2. Extract structured business value using LLMs
3. Build a queryable knowledge graph
4. Enable agentic AI workflows
5. Validate outputs against ground truth
6. Run continuous benchmarks

Early prototypes used a monolithic approach, but we observed:
- **Tight coupling** made changes risky
- **Different scaling needs** (ingestion vs. inference)
- **Team autonomy** blocked by shared codebase
- **Technology diversity** required (Playwright, Neo4j, LangGraph)

## Decision

We will adopt a **six-layer service-oriented architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 6: Benchmarks          Continuous evaluation     │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Ground Truth        Validation & truth store    │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Agents              LangGraph orchestration   │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Knowledge Graph     Neo4j + pgvector hybrid   │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Extraction            LLM + ontology-guided   │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Ingestion             Playwright + Redis queue │
└─────────────────────────────────────────────────────────┘
```

Each layer is:
- **Independently deployable** (separate containers)
- **Technology-appropriate** (best tool for the job)
- **API-contracted** (OpenAPI specs)
- **Horizontally scalable** (stateless where possible)

### Service lifecycle classification (explicit)

To prevent architecture and deployment drift, service directories must be explicitly classified as one of:

- `production`: part of the supported production platform
- `internal`: operator/internal platform component, not customer-facing product surface
- `experimental`: pre-GA or incubation scope; may change without normal compatibility guarantees

| Service directory | Classification | Notes |
|---|---|---|
| `services/layer1-ingestion` | production | Layer 1 in the six-layer platform.
| `services/layer2-extraction` | production | Layer 2 in the six-layer platform.
| `services/layer3-knowledge` | production | Layer 3 in the six-layer platform.
| `services/layer4-agents` | production | Layer 4 in the six-layer platform.
| `services/layer5-ground-truth` | production | Layer 5 in the six-layer platform.
| `services/layer6-benchmarks` | production | Layer 6 in the six-layer platform.
| `services/layer2-5-signal-refinery` | experimental | Cross-layer refinement prototype between extraction and ground-truth.
| `services/layer7-billing` | internal | Billing/entitlements control-plane support; internal-facing.

CI preflight enforces that any layer-style deployment entering Kubernetes manifests is listed in this classification set.

## Consequences

### Positive
- ✅ **Team autonomy**: Teams own layers end-to-end
- ✅ **Independent scaling**: Scale L1 ingestion without scaling L4 agents
- ✅ **Technology flexibility**: Use Python for ML, TypeScript for frontend
- ✅ **Fault isolation**: L2 failure doesn't cascade to L3
- ✅ **Clear interfaces**: API contracts prevent breaking changes

### Negative
- ❌ **Operational complexity**: 6 services to monitor vs. 1
- ❌ **Network overhead**: Internal API calls add latency (~10-50ms)
- ❌ **Data consistency**: Cross-layer transactions require sagas
- ❌ **Local development**: More services to run locally

### Neutral
- 🔄 **Testing strategy**: Contract tests become critical
- 🔄 **Deployment**: CI/CD pipelines per layer

## Alternatives Considered

### Monolithic Django/Rails App
- **Pros:** Simple deployment, single codebase, easy transactions
- **Cons:** Technology lock-in, scaling coupling, team bottlenecks
- **Why rejected:** Would block ML team from using Python ecosystem

### Three-Layer Architecture (Ingestion/Processing/API)

- **Pros:** Simpler operations, fewer boundaries
- **Cons:** Knowledge graph and agents are too different to share layer
- **Why rejected:** Agents need different scaling (bursty) vs. steady-state extraction

### Serverless (Lambda/Cloud Functions)
- **Pros:** Zero ops, automatic scaling
- **Cons:** Cold start latency for agents, vendor lock-in, cost unpredictability
- **Why rejected:** Long-running agent workflows don't fit function model

## Implementation

Each layer exposes:
- **REST API** for synchronous operations
- **Redis queue** for async job distribution
- **Health endpoints** (`/health`, `/ready`) for orchestration
- **OpenTelemetry** for distributed tracing

See [Architecture Overview](../../core-concepts/architecture.md) for detailed diagrams.

## Related

- [Architecture Overview](../../core-concepts/architecture.md) — C4 model diagrams
- [Layer 1 API](../../reference/layer1-ingestion-api.md) — Ingestion service contract
- [ADR-003: Neo4j for Knowledge Graph](./ADR-003-neo4j-pgvector-hybrid-graph-database.md) — Rationale for L3 design

---

*Last updated: 2026-05-27 | Status: Accepted*
