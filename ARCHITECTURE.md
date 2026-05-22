# Architecture

Value Fabric uses a six-layer microservices architecture with strict tenant isolation via PostgreSQL RLS.

For full details, see:

- [System Overview](docs/architecture/system-overview.md)
- [Architecture Concepts](docs/core-concepts/architecture.md)
- [ADR-001: Six-Layer Architecture](docs/explanations/adr/ADR-001-six-layer-architecture.md)
- [Component Interaction Map](docs/architecture/component-interaction-map.md)

## Layers

| Layer | Service | Port | Purpose |
| --- | --- | --- | --- |
| 1 | layer1-ingestion | 8001 | Intelligent data ingestion, Playwright crawling, Celery jobs, PostgreSQL state, compliance-aware ingestion |
| 2 | layer2-extraction | 8002 | Ontology-guided extraction, Pydantic v2, LLM extraction, RDF/OWL generation, provenance, batch ingest |
| 3 | layer3-knowledge | 8003 | Knowledge graph, Neo4j, GraphRAG, hybrid retrieval, pgvector, subgraph APIs |
| 4 | layer4-agents | 8004 | Agentic workflow engine, LangGraph workflows, ROI calculator, business case generation, checkpoints |
| 5 | layer5-ground-truth | 8005 | TruthObject validation, maturity ladder, evidence-backed claims |
| 6 | layer6-benchmarks | 8006 | Peer comparison, statistical validation, datasets, benchmark policies |

## Core Patterns

- **Tenant isolation** — Every data read/write is scoped by `tenant_id` via GovernanceMiddleware and PostgreSQL RLS.
- **Contract-first** — Tool schemas, agent outputs, and API response shapes are declared in `contracts/` and enforced by CI.
- **Provider-agnostic agents** — Core orchestration in `services/layer4-agents/src/engine/` is decoupled from specific LLM vendors.
- **Runtime packages** — `value_fabric/layer*/` are shim packages that delegate to canonical service implementations in `services/layer*/src/`.
- **Packs** — Domain-specific ontologies, formulas, and benchmarks live in `packs/` and extend the platform without modifying core logic.

## Source of Truth Paths

| Concern | Path |
| --- | --- |
| Runtime Python packages | `value_fabric/layer{1–6}/`, `value_fabric/shared/` |
| Service implementations | `services/layer{1–6}-*/src/` |
| Frontend | `apps/web/` |
| API contracts | `contracts/` |
| Kubernetes manifests | `k8s/` |
| Monitoring | `monitoring/` |
| Documentation | `docs/` |
