# AGENTS — services/layer3-knowledge (L3, port 8003)

Scoped instructions; universal rules live in the root `AGENTS.md`.

## Responsibility

Neo4j knowledge graph, GraphRAG, hybrid retrieval, pgvector, subgraph APIs.
Graph projections are rebuildable; PostgreSQL remains authoritative.

## Canonical runtime path

`services/layer3-knowledge/src/` — all net-new logic lands here (see
`docs/reference/layer-runtime-path-governance.md`). API routes:
`services/layer3-knowledge/src/api/routes/`.

## Layer rules

- Preserve Neo4j entity relationships and hybrid retrieval behavior.
- Keep graph query APIs contract-aligned.
- Every graph traversal, index, search filter, and vector retrieval carries a
  tenant filter; missing filters fail closed (see
  `release/v1/tasks/V1-TENANCY-012.yaml`).
- Avoid breaking GraphRAG, subgraph, and entity-context consumers.

## Validation

```bash
make test-layer3
make lint-layer3
make typecheck-layer3
pytest tests/tenancy/test_search_index_tenant_scope.py
```
