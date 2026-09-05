# Architecture Map — Fabric_4L (Swarm Baseline, 2026-09-05)

Source of truth: ARCHITECTURE.md + release/v1/launch-contract.yaml on main @ 4bb4e142.

## Six-layer core (tenant isolation via PostgreSQL RLS + GovernanceMiddleware)
| Layer | Service | Port | Purpose |
|---|---|---|---|
| 1 | layer1-ingestion | 8001 | Ingestion, Playwright crawling, Celery jobs |
| 2 | layer2-extraction | 8002 | Ontology-guided LLM extraction, RDF/OWL, provenance |
| 3 | layer3-knowledge | 8003 | Neo4j graph, GraphRAG, hybrid retrieval, pgvector |
| 4 | layer4-agents | 8004 | LangGraph workflows, agent runtime, ROI, billing |
| 5 | layer5-ground-truth | 8005 | TruthObject validation, evidence claims |
| 6 | layer6-benchmarks | 8006 | Peer comparison, statistical validation |
Adjacent: layer2-5-signal-refinery (8007, out-of-scope for Core GA), billing (owned by L4).

## Key paths
- Runtime: services/layer{1-6}-*/src/, packages/shared/src/value_fabric/shared/
- Frontend: apps/web/ (React+TS, tenant-scoped router /t/:tenantSlug/...)
- Contracts: contracts/openapi, contracts/jsonschema (regenerated from source of truth)
- Launch control plane: release/v1/ (frozen), production-readiness/risk_register.yaml

## Missing implementations (gaps at baseline)
- Canonical readiness docs stale (June); generated artifacts/* never committed — freshness is CI's job.
- Open canonical tasks: release/v1/tasks/ (10 files, see TASK_DAG.md).
- L4 runtime: list_runs worker-local pending durable run-store follow-up (documented in code).
- Environment-dependent evidence (P0-001/002/003, P1-001..009) cannot be produced by agents.
