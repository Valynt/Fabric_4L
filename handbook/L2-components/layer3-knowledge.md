# L2 Component — layer3-knowledge

## Purpose

Knowledge/graph layer (`services/layer3-knowledge/`). Owns tenant-scoped graph storage and
retrieval, evidence search, and the deterministic ROI calculation authority (R-4). Every
calculation is reproducible from stored inputs, formulas, policies, and engine version;
requests/responses are immutable snapshots.

## Owned journey stages / behaviors

- BEH-02 hypothesis-capture — tenant-scoped graph queries feeding hypothesis generation/ranking
- BEH-03 driver-tree-modeling — persistent driver/lever/variable graph objects
  (`src/graph/`)
- BEH-04 formula-roi-calculation — deterministic calculation; tool manifests
  `contracts/tool-manifests/calculate_roi.json`, `evaluate_formula.json`,
  `sensitivity_analysis.json`
- BEH-05 evidence-and-cost-binding — evidence search and retrieval (`src/retrieval/`)

## Key verified paths

- `services/layer3-knowledge/src/api/main.py` — API entry; `api/` also has
  `auth_context.py`, `dependencies*.py`, `exception_mapping.py`, `rate_limiter.py`,
  `versioning.py`, `routers/`, `routes/`, `services/`
- src subdirs: `adapters/`, `agents/`, `analytics/`, `auth/`, `backup/`, `cache/`, `config/`,
  `db/`, `gateway/`, `graph/`, `ingestion/`, `load_balancing/`, `metrics/`, `migrations/`,
  `models/`, `performance/`, `rate_limiting/`, `retrieval/`, `schema/`, `security/`,
  `services/`, `tracing/`, `utils/`; root `config.py`, `logging_config.py`
- Root: `README.md`, `AGENTS.md`, `SECURITY_BOUNDARY_TEST_REPORT.md`, `pytest.ini`,
  `docker-compose.yml`

## Dependencies

- Contracts: `contracts/openapi/layer3-knowledge/`, `contracts/jsonschema/entity.json`,
  `signal.json`, `layer3-entity-resolution-contract.json`, `contracts/tool-manifests/query_graph.json`,
  `semantic_search.json`, `graph_traverse.json`.
- Called by `services/layer4-agents` (orchestration) and `services/api` (BFF). Never exposes
  public ingress.
- Persistence: PostgreSQL + Neo4j (tenant-scoped traversal, constraints, indexes).

## Primary gates

- **AG-05** tenant-isolation-and-behavior — Neo4j/graph/vector/retrieval isolation, Cypher safety.
- **AG-03** contract-compliance — cross-layer contract tests, calculation schema versioning
  (GAP-06 convergence).
- **AG-02** code-quality-and-tests — determinism proofs, property tests on calculation inputs.
