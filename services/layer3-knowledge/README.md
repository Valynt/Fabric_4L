# Layer 3: Knowledge Graph & Semantic Layer

> Canonical routing/versioning source: [Service Routing and API Version Matrix](../../docs/reference/service-routing-and-api-version-matrix.md).

> Canonical runtime path policy: [Layer Runtime Path Governance Matrix](../../docs/reference/layer-runtime-path-governance.md).

> Contract source of truth: [`contracts/openapi/layer3-knowledge.json`](../../contracts/openapi/layer3-knowledge.json).

Layer 3 consumes ontology-guided outputs from Layer 2 and exposes graph retrieval, evidence traversal, and semantic APIs for downstream workflows.

## Architecture ownership (canonical runtime vs service wrapper)

### Canonical runtime code (`value_fabric/layer3/`)

All net-new Layer 3 runtime logic belongs in `value_fabric/layer3/` per path governance.

Primary responsibilities:

- Route handler logic under `value_fabric/layer3/api/routes/` (entities, value trees, formulas, evidence, products, benchmarks, calculators, tenant resolution, compatibility aliases).
- FastAPI runtime composition and route-group registration under `value_fabric/layer3/api/`.
- Layer 3 domain services (knowledge graph, retrieval, provenance, analytics, pack-aware semantics).
- Canonical models/schemas used by the Layer 3 runtime contract.

### Deployable service wrapper (`services/layer3-knowledge/src/`)

`services/layer3-knowledge/src/` exists as a deployable wrapper and compatibility boundary, **not** the place for net-new business logic.

Wrapper responsibilities:

- Service entrypoint/wiring for deployment packaging.
- Compatibility re-exports/shims that forward to canonical runtime modules.
- Environment/bootstrap glue needed to run Layer 3 in service form.

Contributor rule of thumb:

- New endpoint behavior/model logic → `value_fabric/layer3/`.
- Wrapper edits in `services/layer3-knowledge/src/` should remain thin, explicit, and wiring-only.

## Quick start (routing-aligned)

### Prerequisites

- Python environment with project dependencies.
- Neo4j 5.x reachable by Layer 3.
- Optional vector backend credentials if semantic vector search is enabled.

### Run the Layer 3 service wrapper locally

```bash
# from repository root
cd services/layer3-knowledge
python -m uvicorn src.main:app --host 0.0.0.0 --port 8003 --reload
curl -X POST http://localhost:8003/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How can data processing capabilities benefit finance teams?",
    "entity_type": "Capability",
    "max_hops": 3,
    "max_results": 10
  }'
```

Layer 3 canonical external port in the routing matrix is **8003**.

### Smoke-check core health routes

```bash
curl http://localhost:8003/health
curl http://localhost:8003/ready
curl http://localhost:8003/metrics
curl -X POST http://localhost:8003/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "real-time analytics",
    "search_type": "hybrid",
    "top_k": 10
  }'
```

## API surface reconciliation notes

The prior README examples used outdated routes/ports (for example `:8001/v1/query`, `:8001/v1/search`, and older analytics endpoints). Current examples in this document use the canonical `8003` Layer 3 port.

For current behavior, use the OpenAPI contract as source of truth:

- Contract file: `contracts/openapi/layer3-knowledge.json`
- Runtime route modules: `value_fabric/layer3/api/routes/`

### Current route families (by canonical module)

- System/ops: `system.py` (`/health`, `/ready`, `/metrics`, detailed health variants)
- Value trees and graph traversal: `value_trees.py`
- Query/search and entity discovery: `query_search.py`, `entities.py`, `entity_compat.py`
- Evidence/provenance: `evidence.py`, `provenance_audit.py`
- Formulas/calculators/ROI/value packs: `formulas.py`, `formula_governance.py`, `calculators.py`, `roi_calculator.py`, `value_packs.py`, `variables.py`, `models.py`, `products.py`, `benchmarks.py`, `competitive_intel.py`
- Compatibility aliases and tenant helpers: `compat_aliases.py`, `tenant_resolution.py`

### Versioning/prefix notes

- Most Layer 3 functional endpoints are mounted under `/v1`.
- Operational routes remain at root (`/health`, `/ready`, `/metrics`).
- Some compatibility paths exist for backward compatibility and should not be treated as net-new API design targets.

## Contract-first changes (Layer 3 contributor checklist)

Before changing Layer 3 APIs, models, or endpoint semantics:

1. Confirm canonical runtime target in the [Layer Runtime Path Governance Matrix](../../docs/reference/layer-runtime-path-governance.md).
2. Verify route and version prefix expectations in the [Service Routing and API Version Matrix](../../docs/reference/service-routing-and-api-version-matrix.md).
3. Update and validate the Layer 3 OpenAPI contract: [`contracts/openapi/layer3-knowledge.json`](../../contracts/openapi/layer3-knowledge.json).
4. Reconcile any impacted tests (contract tests, route tests, tenant isolation tests) before merge.
5. If compatibility aliases are touched, document migration intent and avoid introducing new business logic in wrapper/shim paths.

Related governance references:

- Root agent/platform rules: [`AGENTS.md`](../../AGENTS.md)
- Layer runtime parity checks: `tests/contract/test_layer_runtime_parity.py`
- Service entrypoint smoke checks: `tests/contract/test_layer_service_entrypoint_smoke.py`

## Route dependency import inventory (as of 2026-05-19)

Inventory command:

```bash
rg "from \\.\\.\\.api\.dependencies_tenant(_secured)? import" services/layer3-knowledge/src/api/routes -n
```

Result: every route under `services/layer3-knowledge/src/api/routes` imports Neo4j tenant dependencies from `dependencies_tenant_secured` only; zero route imports target `dependencies_tenant`.

## Canonical Neo4j tenant dependency

Layer 3 route modules must import tenant-scoped Neo4j dependencies only from
`services/layer3-knowledge/src/api/dependencies_tenant_secured.py`. This secured
wrapper is the **single approved route dependency** because it:

- derives tenant context from `RequestContext` or an already-authenticated route helper;
- creates `Neo4jTenantSessionSecured` sessions with query validation enabled;
- force-injects the authenticated `tenant_id` and `_tenant_id` into query parameters; and
- supports `TenantScopedCypher` / `ScopedQuery` objects for builder-generated Cypher.

Approved imports:

```python
from ...api.dependencies_tenant_secured import (
    Neo4jTenantSession,
    create_neo4j_tenant_session,
    get_neo4j_with_tenant,
)
```

Do not import `services/layer3-knowledge/src/api/dependencies_tenant.py` from new
code. That file is a compatibility shim only, logs deprecation warnings on import,
and is hard-removal targeted for **2026-09-30**. CI enforces this with:

```bash
python scripts/ci/check_layer3_legacy_tenant_dependency_imports.py
```

Current route inventory (all canonical imports):

- `src/api/routes/benchmarks.py` → `create_neo4j_tenant_session`
- `src/api/routes/calculators.py` → `create_neo4j_tenant_session`
- `src/api/routes/entities.py` → `Neo4jTenantSession`, `get_neo4j_with_tenant`
- `src/api/routes/formula_governance.py` → `create_neo4j_tenant_session`
- `src/api/routes/formulas.py` → `create_neo4j_tenant_session`
- `src/api/routes/knowledge.py` → `create_neo4j_tenant_session`
- `src/api/routes/models_router.py` → `create_neo4j_tenant_session`
- `src/api/routes/signals.py` → `Neo4jTenantSession`, `get_neo4j_with_tenant`
- `src/api/routes/variables.py` → `create_neo4j_tenant_session`

## Scheduled removals & deprecations

Layer 3 follows Value Fabric deprecation policy:

- Machine-readable register: `docs/deprecation_register.json`
- Human-readable inventory: `docs/deprecation_inventory.md`
- CI gate: `make check-deprecations`

Deprecated endpoints emit warning headers:

- `Warning: 299 - "Deprecated since {date}"`
- `X-Deprecated-Since`, `X-Target-Removal-Date`, `X-Deprecation-Owner`

See [API Reference - Deprecation Policy](../../docs/API_REFERENCE.md#deprecation-policy).

### Graph field deprecation transition (v2.4 target)

Layer 3 graph response models currently include both canonical and legacy alias fields during the deprecation window:

- GraphNode canonical: `label`, `type`, `confidence`
- GraphNode legacy aliases: `name`, `entity_type`, `confidence_score`
- GraphEdge canonical: `type`
- GraphEdge legacy alias: `relationship_type`

### Compatibility deprecation phases and removal gate

- `warning_only`: legacy routes/fields stay active and emit counters.
- `disable_non_prod`: legacy routes return `410 Gone` in non-production environments.
- `removed`: legacy routes and legacy graph aliases are disabled.

Hard-removal threshold (must be met before production removal):

- `layer3_deprecated_route_hits_total` aggregate over lookback window: `0`
- `layer3_legacy_field_usage_total` aggregate over lookback window: `0`

Target removal is **v2.4 / 2026-07-01**. Monitor runtime counters before removal:
`graph_node_request_legacy_fields`, `graph_node_response_legacy_fields`, `graph_edge_request_legacy_fields`, `graph_edge_response_legacy_fields`.
See `docs/DEPRECATIONS.md#graph-legacy-field-removal-checklist` for mandatory cutover steps.

## Dependency locking

- Canonical Python lock artifact for this service: `uv.lock` (source of truth).
- Regenerate lock state after dependency edits in `pyproject.toml`:

```bash
cd services/layer3-knowledge
uv lock
uv export --locked --no-dev --format requirements-txt -o requirements.lock
```

- CI and Docker builds must consume `uv.lock` deterministically (`uv sync --locked` or equivalent).


## Migration reproducibility reference

- `docs/reference/migration-reproducibility-invariants.md` (mandatory migration invariants and incident-state reconstruction)
