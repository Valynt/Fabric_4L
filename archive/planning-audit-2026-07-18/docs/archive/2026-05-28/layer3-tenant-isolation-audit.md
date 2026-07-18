# Layer 3 Tenant Isolation Audit

**Date:** 2026-05-17  
**Scope:** All Cypher queries in `services/layer3-knowledge/src/`  
**Method:** Static analysis of all files containing `.run()`, `execute_query()`, `execute_write()`, `execute_read()`

---

## Summary

Layer 3 has strong tenant isolation infrastructure:

- `Neo4jTenantSessionSecured` in `api/dependencies_tenant_secured.py` force-injects `tenant_id` and `_tenant_id` into all query params — routes using this canonical session wrapper are safe even when they omit `tenant_id` from the explicit params dict.
- `TenantScopedCypher` builder enforces `WHERE n.tenant_id = $_tenant_id` in all generated queries.
- `_resolve_tenant_id()` in retrieval classes (`HybridSearch`, `GraphRAG`, `VectorStore`, `CentralityAnalyzer`, `CommunityDetector`) raises `ValueError`/`RuntimeError` if no tenant is provided — fail-closed.
- `db/tenant_queries.py` provides tenant-mandatory helpers for all common entity operations.

---

## Findings

### ✅ Verified — Correctly Scoped

| File | Pattern | Notes |
|---|---|---|
| `retrieval/hybrid_search.py` | `_resolve_tenant_id()` + `TenantScopedCypher` | Raises if no tenant |
| `retrieval/graph_rag.py` | `_resolve_tenant_id()` + `TenantScopedCypher` | All MATCH clauses include `tenant_id` |
| `retrieval/vector_store.py` | `_resolve_tenant_id()` + explicit `WHERE n.tenant_id` | Raises if no tenant |
| `analytics/centrality.py` | `_resolve_tenant_id()` + `TenantScopedCypher` | Raises if no tenant |
| `analytics/communities.py` | `_resolve_tenant_id()` + `TenantScopedCypher` | Raises if no tenant |
| `ingestion/neo4j_loader.py` | `MERGE (n {id: ..., tenant_id: ...})` | All MERGE/MATCH include tenant |
| `services/signal_persistence.py` | Explicit `tenant_id` in all MATCH/MERGE | Required param, no default |
| `services/evidence_search.py` | Explicit `WHERE node.tenant_id = $tenant_id` | Required param |
| `api/routes/entities.py` (list) | `TenantScopedCypher` via `Neo4jTenantSession` | Auto-injected |
| `api/routes/entities.py` (detail) | `Neo4jTenantSession.execute_query` auto-injects `tenant_id` | Safe — session wrapper adds it |
| `api/app_monolith.py` (`_update_entity`) | Explicit `tenant_id` required, MATCH filters by it | Correct |
| `api/app_monolith.py` (`_delete_entity`) | Explicit `tenant_id` required, MATCH filters by it | Correct |
| `api/app_monolith.py` (`_delete_entity_by_id`) | Raises `ValueError` if no `tenant_id` | Correct |

### ❌ Fixed — Was Missing Tenant Scope

| File | Issue | Fix Applied |
|---|---|---|
| `api/app_monolith.py` (`_create_entity`) | Created nodes without `tenant_id` property; called without `tenant_id` arg | Added `tenant_id` param (required), added `tenant_id: $tenant_id` to CREATE, added fail-closed guard |

---

## Hostile Test Recommendations

The following cross-tenant hostile tests should be added to `services/layer3-knowledge/tests/`:

```python
# test_tenant_isolation_hostile.py

async def test_create_entity_without_tenant_id_fails():
    """_create_entity must reject calls without tenant_id."""
    result = await _create_entity(driver, operation, tenant_id=None)
    assert result["success"] is False
    assert "tenant_id is required" in result["error"]

async def test_tenant_a_cannot_read_tenant_b_entity():
    """Entity created for tenant A must not be returned for tenant B."""
    # Create entity for tenant A
    await _create_entity(driver, operation, tenant_id="tenant-a")
    # Query as tenant B — must return empty
    result = await neo4j_tenant_b.execute_query(
        "MATCH (n:Entity {id: $id}) RETURN n", {"id": entity_id}
    )
    assert result == []

async def test_hybrid_search_raises_without_tenant():
    """HybridSearch must raise ValueError when no tenant context is set."""
    search = HybridSearch(driver)
    with pytest.raises(ValueError, match="tenant_id is required"):
        await search.search("query", tenant_id=None)
```

---

## Residual Risk

- `api/app_monolith.py` is a compatibility shim being migrated to canonical route files. The `_create_entity` fix above addresses the only unscoped write found. As migration continues, each function moved out of `app_monolith.py` should be verified for tenant scoping before the shim is removed.
- The `Neo4jTenantSessionSecured` auto-injection is a safety net, not the primary control. Routes should pass `tenant_id` explicitly in query params where possible to make the scoping visible in code review. Route modules must import it from `api/dependencies_tenant_secured.py`; `api/dependencies_tenant.py` is a warning-only compatibility shim until hard removal on **2026-09-30**.
