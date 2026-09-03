---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Service Map

This page maps every maintained service to its port, runtime path, API module, and classification. Use it before adding new code so you target the canonical path and avoid architectural drift.

<span class="vp-badge vp-badge--role">Developer</span>

## Port assignments

| Port | Service | Classification | Runtime path |
|------|---------|----------------|--------------|
| 8001 | Layer 1 — Ingestion | `production` | `services/layer1-ingestion/src/layer1_ingestion/` |
| 8002 | Layer 2 — Extraction | `production` | `services/layer2-extraction/src/layer2_extraction/` |
| 8003 | Layer 3 — Knowledge | `production` | `services/layer3-knowledge/src/` |
| 8004 | Layer 4 — Agents | `production` | `services/layer4-agents/src/layer4_agents/` |
| 8005 | Layer 5 — Ground Truth | `production` | `services/layer5-ground-truth/src/layer5_ground_truth/` |
| 8006 | Layer 6 — Benchmarks | `production` | `services/layer6-benchmarks/src/layer6_benchmarks/` |
| — | API Gateway | `production` | `services/api/` |
| — | Layer 2.5 Signal Refinery | `experimental` | `services/layer2-5-signal-refinery/` |

!!! tip "Port mnemonic"
    Ports map directly to layer numbers: `8000 + layer_number`. This convention is used by dev scripts, Docker Compose, and Kubernetes manifests.

## Service responsibilities

### Layer 1 — Ingestion
- Playwright-based web crawling
- Celery job distribution via Redis queues
- PostgreSQL job state and source registry
- Compliance auditing (robots.txt, rate limits, PII redaction)
- Tenant-scoped ingestion pipelines

### Layer 2 — Extraction
- Ontology-guided LLM extraction
- Pydantic v2 schema validation
- RDF/OWL serialization with PROV-O provenance
- Batch ingest and deduplication
- Direct `extract-and-ingest` path to Layer 3

### Layer 3 — Knowledge
- Neo4j graph storage and traversal
- pgvector hybrid retrieval
- GraphRAG indexing and query
- Subgraph APIs for frontend visualization
- Formula evaluation and value tree resolution

### Layer 4 — Agents
- LangGraph workflow orchestration
- Checkpoint/resume with PostgreSQL-backed state
- ROI calculator and business case generator
- Tiered skill system (7 tiers from navigation to audit)
- Provider-agnostic LLM adapters

### Layer 5 — Ground Truth
- TruthObject validation state machine
- Maturity ladder (0–5)
- Evidence-backed claim tracking
- Sync to Layer 3 as `:GroundTruth` nodes

### Layer 6 — Benchmarks
- Benchmark dataset management by industry
- Peer comparison with percentile ranking
- Statistical range validation
- Dataset lineage tracking

## API gateway pattern

The `services/api/` directory provides a shared gateway and auth enforcement layer. It is not a traffic proxy for all requests; rather, it hosts cross-cutting concerns:

- Authentication resolution (JWT, API key, service-to-service)
- Tenant context injection
- Rate limiting
- Canonical error envelope formatting
- Request ID and correlation ID assignment

!!! note "Layers expose their own routes"
    Each layer runs its own FastAPI application and serves its own OpenAPI spec. The gateway supplements rather than replaces layer APIs.

## Shared packages

| Package | Path | Purpose |
|---------|------|---------|
| `shared` | `packages/shared/src/value_fabric/shared/` | Tenant context, base models, identity middleware, RBAC helpers |
| `platform-contract` | `packages/platform-contract/` | Cross-layer contract definitions and test harness |

### Canonical import roots

```python
# Correct
from value_fabric.shared.identity.dependencies import get_request_context
from value_fabric.shared.identity.context import RequestContext

# Incorrect (parameter pollution — being deprecated)
def my_service(tenant_id: UUID): ...
```

## Runtime API modules

| Layer | Canonical routes path |
|-------|-----------------------|
| Layer 1 | `services/layer1-ingestion/src/layer1_ingestion/api/routes/` |
| Layer 2 | `services/layer2-extraction/src/layer2_extraction/api/routes/` |
| Layer 3 | `services/layer3-knowledge/src/api/routes/` |
| Layer 4 | `services/layer4-agents/src/api/routes/` |
| Layer 5 | `services/layer5-ground-truth/src/layer5_ground_truth/api/` |
| Layer 6 | `services/layer6-benchmarks/src/layer6_benchmarks/api/routes/` |

## Service classification rules

CI preflight enforces that any layer-style deployment entering Kubernetes manifests is listed in the classification set above. The three classes are:

- `production` — Part of the supported customer-facing platform.
- `internal` — Operator or control-plane component; not a product surface.
- `experimental` — Pre-GA or incubation scope; may change without normal compatibility guarantees.

## Validation

```bash
# Verify service entrypoints expose non-empty OpenAPI contracts
pytest tests/contract/test_layer_service_entrypoint_smoke.py

# Check runtime path parity (canonical vs compatibility)
pytest tests/contract/test_layer_runtime_parity.py

# Validate architecture conformance
make gate-arch
```

## Related pages

- [System Overview](./system-overview.md) — Architecture diagram and layer responsibilities
- [Data Flow](./data-flow.md) — How requests traverse services
- `docs/reference/layer-runtime-path-governance.md`
