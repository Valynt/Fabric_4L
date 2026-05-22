---
title: "Architecture (redirect)"
status: "redirect"
canonical: "core-concepts/architecture.md"
last-reviewed: "2026-05-22"
---

# Architecture

> This page has been consolidated. The canonical platform architecture lives at
> **[`docs/core-concepts/architecture.md`](core-concepts/architecture.md)**.
>
> Earlier content here described an MVP-era mock-runtime model. The platform
> has since moved to a production six-layer microservices topology backed by
> PostgreSQL, Neo4j, pgvector, Redis, and S3 — see the canonical doc for the
> current view, including C4 diagrams, container topology, and data flow.

## Quick reference

| Layer | Service | Port | Purpose |
| ----- | ------- | ---- | ------- |
| 1 | layer1-ingestion    | 8001 | Playwright crawling, document parsing, ingestion jobs |
| 2 | layer2-extraction   | 8002 | Pydantic v2 + LLM-guided ontology extraction, RDF/OWL |
| 3 | layer3-knowledge    | 8003 | Neo4j + pgvector, GraphRAG, hybrid retrieval |
| 4 | layer4-agents       | 8004 | LangGraph workflows, ROI / whitespace / business case |
| 5 | layer5-ground-truth | 8005 | TruthObject validation, maturity ladder |
| 6 | layer6-benchmarks   | 8006 | Datasets, peer comparison, statistical validation |

## Where to read next

- **Canonical platform architecture (C4 + Mermaid):** [`core-concepts/architecture.md`](core-concepts/architecture.md)
- **System overview & component map:** [`architecture/system-overview.md`](architecture/system-overview.md), [`architecture/component-interaction-map.md`](architecture/component-interaction-map.md)
- **Six-layer rationale (ADR-001):** [`explanations/adr/ADR-002-six-layer-architecture.md`](explanations/adr/ADR-002-six-layer-architecture.md)
- **Canonical runtime paths (ADR-027):** [`reference/layer-runtime-path-governance.md`](reference/layer-runtime-path-governance.md)
- **Layer-4 agent-specific architecture:** [`agent-architecture.md`](agent-architecture.md)
- **Frontend navigation architecture:** [`NAVIGATION_ARCHITECTURE.md`](NAVIGATION_ARCHITECTURE.md)
- **Security model & tenant isolation:** [`core-concepts/security-model.md`](core-concepts/security-model.md), [`tenant-isolation.md`](tenant-isolation.md)
- **Frontend governance contract:** [`../DESIGN.md`](../DESIGN.md)
