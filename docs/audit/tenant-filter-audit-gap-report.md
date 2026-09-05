# Slice T — Neo4j / pgvector Tenant-Filter Audit: Gap Report

**Slice:** T (S22-A1 audit half, pulled forward)
**Mode:** Read-only investigation — **no code changes made**
**Branch:** `bmsull560-tenant-filter-audit`
**Date:** (audit session)
**Scope:** Catalog every graph (Neo4j/Cypher) and vector (pgvector / Neo4j-native vector / Pinecone) query in the monorepo; check each for tenant-filter presence; report gaps.

---

## 1. Executive Summary

The audit cataloged every graph and vector query surface across the monorepo and checked each for tenant-filter presence. **The tenant-isolation invariant is overwhelmingly upheld.** The vast majority of query sites route through approved fail-closed execution seams that either force-assign `tenant_id` or reject queries lacking an explicit tenant predicate.

**One genuine gap was confirmed** — the Layer 4 `Neo4jVariableRegistry` performs CRUD/search with **no tenant scoping whatsoever** (no `tenant_id` property on the model, no tenant filter on any query). This is assessed as **MEDIUM** severity (design gap) because pack variable definitions are global templates loaded at startup/CI, but it violates the invariant that *every graph query carries a tenant filter*.

A small number of **conditional / defense-in-depth** observations were noted where tenant filtering relies on a wrapper seam rather than being explicit in the query text — these are SAFE by design but worth documenting.

---

## 2. Approved Fail-Closed Execution Seams (the enforcement points)

These are the seams that make most query sites SAFE. Any query routed through them is tenant-protected even if the raw query text does not visibly contain a tenant predicate.

### Layer 3 (`services/layer3-knowledge`)
| Seam | Location | Behavior |
|------|----------|----------|
| `TenantQueryExecutor.run` | `db/query_execution.py` | Core fail-closed executor; force-assigns tenant |
| `run_scoped_query` | `db/query_execution.py` L629 | Takes `ScopedQuery` from builders |
| `run_validated_query` | `db/query_execution.py` L669 | Legacy raw Cypher; fail-closed structural validation; force-assigns tenant; `require_explicit_tenant_id=True` option |
| `run_tenant_query` / `run_system_query` | `db/query_execution.py` | Tenant-scoped / system-scoped |
| `TenantScopedCypher` | `packages/shared/.../isolation.py` L304 | Always injects `_tenant_id` param + tenant predicates |
| `custom_tenant_query` | `packages/shared/.../isolation.py` L665 | Requires `$_tenant_id`/`$tenant_id` reference AND explicit tenant predicate (raises ValueError otherwise) |
| `SystemCypher` | `packages/shared/.../isolation.py` L189 | Schema/migration/backup/health (system-scoped, no tenant data) |
| `Neo4jTenantSessionSecured.run` | `api/dependencies_tenant_secured.py` L106 | Validates Cypher text (blocks broad MATCH without tenant predicate), **auto-injects `tenant_id`/`_tenant_id` into params**, runs through `TenantQueryExecutor` |
| `ValidatedNeo4jSession` | `security/query_validator.py` L416 | Routes through `TenantQueryExecutor`, fail-closed |

### Layer 4 (`services/layer4-agents`)
| Seam | Location | Behavior |
|------|----------|----------|
| `fetch_tenant_validated_records` / `fetch_tenant_validated_single` | `services/tenant_cypher.py` | Validate query has explicit tenant_id predicate + force-assign params |
| `QueryGraphTool._inject_tenant_filter` | `tools/knowledge_tools.py` L100-160 | Injects `<alias>.tenant_id = $tenant_id` on first node alias |
| `QueryGraphTool._ensure_tenant_parameters` | `tools/knowledge_tools.py` L162-180 | Rejects tenant spoofing |
| `QueryGraphTool.execute` | `tools/knowledge_tools.py` L192+ | Requires valid `TenantContext` fail-closed |
| `ValidatedNeo4jSession` | (L4) | Routes through `TenantQueryExecutor` |
| `run_tenant_validated_query` | `services/tenant_query_helper.py` | Tenant-validated query helper |

---

## 3. Graph Query Catalog (Neo4j / Cypher)

### 3.1 Layer 3 — Knowledge Graph (`services/layer3-knowledge`)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 1 | `services/competitive_intel_service.py` | `_run_cypher` → `run_validated_query` (`require_explicit_tenant_id=True`) | Yes (all queries include `tenant_id`) | ✅ SAFE |
| 2 | `security/query_validator.py` | `ValidatedNeo4jSession` | Routes through `TenantQueryExecutor` | ✅ SAFE |
| 3 | `analytics/similarity.py` | `run_scoped_query` + `TenantScopedCypher` | All `$_tenant_id` | ✅ SAFE |
| 4 | `retrieval/hybrid_search.py` | `run_scoped_query` + `TenantScopedCypher` | All `$_tenant_id` | ✅ SAFE |
| 5 | `retrieval/graph_rag.py` | `run_scoped_query` + `TenantScopedCypher` | All `$_tenant_id` | ✅ SAFE |
| 6 | `services/evidence_search.py` | `run_validated_query` + `require_explicit_tenant_id=True` | `WHERE node.tenant_id = $tenant_id` | ✅ SAFE |
| 7 | `services/entity_resolution.py` | `run_validated_query` + `require_explicit_tenant_id=True` | `WHERE node.tenant_id = $tenant_id` | ✅ SAFE |
| 8 | `services/case_study_service.py` | `run_validated_query` + `require_explicit_tenant_id=True` | All queries include `tenant_id` | ✅ SAFE |
| 9 | `services/product_service.py` | `_run_cypher` → `run_validated_query` | `tenant_id` in query/params; wrapper protects tenant-owned labels | ✅ SAFE |
| 10 | `api/routes/entities.py` L191/344/371/479 | `neo4j.execute_query` with `TenantScopedCypher.custom_tenant_query` | Builder-scoped | ✅ SAFE |
| 11 | `api/routes/entities.py` L235/252/275 | Direct `neo4j.execute_query` raw Cypher | `tenant_id` predicates in query text; relies on `Neo4jTenantSessionSecured` auto-inject | ⚠️ CONDITIONAL (SAFE via seam) |
| 12 | `db/dual_store_coordinator.py` | pgvector fallback writes/compensating deletes | Requires explicit `tenant_id` (raises ValueError if missing) | ✅ SAFE |

### 3.2 Layer 4 — Agents (`services/layer4-agents`)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 13 | `services/context_gatherer.py` | `MATCH (s:Signal {tenant_id: $tenant_id})` etc. via `run_tenant_validated_query` | Yes | ✅ SAFE |
| 14 | `services/formula_governance_service.py` | All `MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 15 | `services/intelligence_orchestrator.py` | All `MATCH (... {tenant_id: $tenant_id})` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 16 | `services/value_pack_service.py` | All `MATCH (vp:ValuePack {tenant_id: $tenant_id})` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 17 | `services/value_hypothesis_engine.py` | `where_clauses = ["vh.tenant_id = $tenant_id", ...]` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 18 | `services/narrative_builder_service.py` | `where_clauses = ["n.tenant_id = $tenant_id"]` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 19 | `tools/knowledge.py` | Direct Neo4j queries | All tenant-filtered | ✅ SAFE |
| 20 | `tools/knowledge_tools.py` (`QueryGraphTool`) | `_inject_tenant_filter` on first node alias | Injects `<alias>.tenant_id = $tenant_id`; rejects spoofing; fail-closed | ✅ SAFE |
| 21 | `workflows/whitespace.py` L288 | `MATCH (c:Capability)` via `query_graph` tool | Injected by tool | ✅ SAFE |
| 22 | `workflows/queries.py` | Deprecated builders with optional tenant_id | Injected by `query_graph` tool | ✅ SAFE |
| 23 | `workflows/business_case.py` L378 | Passes tenant_id through `query_graph` | Injected by tool | ✅ SAFE |
| 24 | `integration/layer3_client.py` | HTTP client (not direct query) | Tenant propagated via `X-Tenant-ID` header | ✅ SAFE |
| 25 | `agents/audit_orchestrator/persistence.py` | Direct Neo4j queries | All tenant-filtered | ✅ SAFE |
| 26 | `api/routes/analysis_workspace.py` | Direct Neo4j queries | All tenant-filtered | ✅ SAFE |
| 27 | **`services/variable_registry_service.py`** | `Neo4jVariableRegistry` CRUD/search | **NO tenant scoping** | 🔴 **GAP** |

---

## 4. Vector Query Catalog

### 4.1 Neo4j-native vector store (ACTIVE backend)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 28 | `retrieval/vector_store.py` | `_build_vector_search_query` L174-187 (`db.index.vector.queryNodes`) | `WHERE node.tenant_id = $_tenant_id` | ✅ SAFE |
| 29 | `services/evidence_search.py` L86/112 | `db.index.vector.queryNodes('evidence_embedding_idx', ...)` | `WHERE node.tenant_id = $tenant_id` | ✅ SAFE |
| 30 | `services/entity_resolution.py` L61 | `_build_vector_query` (`db.index.vector.queryNodes`) | `WHERE node:{entity_type} AND node.tenant_id = $tenant_id` | ✅ SAFE |

### 4.2 pgvector (fallback / secondary store)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 31 | `db/dual_store_coordinator.py` | pgvector fallback writes/compensating deletes | Requires explicit `tenant_id` (raises ValueError if missing) | ✅ SAFE |

> **Note:** `scripts/ci/check_vector_store_health.py` confirms `pgvector_required=false` — pgvector is a fallback, not the active backend. The active vector store is Neo4j-native vector indexes.

### 4.3 Pinecone (Layer 4)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 32 | `tools/knowledge_tools.py` (`SemanticSearchTool`) | `index.query(...)` | Requires valid `TenantContext` (fail-closed); `filter_dict = {"tenant_id": str(tenant_ctx.tenant_id)}` injected into Pinecone metadata filter | ✅ SAFE |

### 4.4 Full-text (BM25) — related retrieval surface

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 33 | `retrieval/hybrid_search.py` L321 | `db.index.fulltext.queryNodes` via `TenantScopedCypher.custom_tenant_query` | `$_tenant_id` | ✅ SAFE |
| 34 | `retrieval/graph_rag.py` L546-576 | `db.index.fulltext.queryNodes` via `TenantScopedCypher.custom_tenant_query` | `$_tenant_id` | ✅ SAFE |
| 35 | `services/evidence_search.py` L188/209 | `db.index.fulltext.queryNodes` via `run_validated_query` | `tenant_id` | ✅ SAFE |

---

## 5. Confirmed Gaps

### GAP-1 (MEDIUM): Layer 4 `Neo4jVariableRegistry` — no tenant scoping

**File:** `services/layer4-agents/src/layer4_agents/services/variable_registry_service.py`
**Interface:** `services/layer4-agents/src/layer4_agents/interfaces/variable_registry.py`

| Method | Line | Query | Tenant filter |
|--------|------|-------|---------------|
| `register_variable` | L83 | `CREATE (v:Variable {id: $variable_id, ...})` | ❌ None (no `tenant_id` property) |
| `get_variable` | L116 | `MATCH (v:Variable {id: $variable_id})` | ❌ None |
| `update_variable` | L213 | `MATCH (v:Variable {id: $variable_id})` | ❌ None |
| `search_variables` | L264 | `MATCH (v:Variable)` (broad match) | ❌ None |

**Root cause:** The `Variable` dataclass has **no `tenant_id` field**. The registry stores pack-level variable definitions (global templates) via `PackVariableLoader` at startup/CI. It is an internal service interface with **no API route exposure**.

**Risk assessment:**
- **Severity: MEDIUM** — pack variable definitions are global templates, not per-tenant data, so cross-tenant data leakage is limited. However, it **violates the invariant** that every graph query carries a tenant filter, and `search_variables` uses a broad `MATCH (v:Variable)` with no predicate at all.
- **Exploitability:** Low — no API route references `IVariableRegistry`; it is used by `PackVariableLoader` (startup/CI) and pack variable resolution.
- **Impact if exploited:** A compromised internal caller could read/modify pack variable definitions across tenants. Since these are global templates, the blast radius is limited but non-zero.

**Recommended fix (NOT applied — out of scope for this read-only audit):** Add `tenant_id` to the `Variable` model and scope all four queries to `tenant_id`. Route through `fetch_tenant_validated_records` (the L4 fail-closed seam). This belongs in the enforcement sprint touching `shared/security`.

---

## 6. Conditional / Defense-in-Depth Observations (SAFE by design, worth documenting)

These are not gaps — tenant filtering is enforced by a wrapper seam rather than being explicit in the query text. They are SAFE but rely on the seam being correct.

| # | File | Observation |
|---|------|-------------|
| C1 | `api/routes/entities.py` L235/252/275 | Direct `neo4j.execute_query` raw Cypher with `tenant_id` predicates in query text; relies on `Neo4jTenantSessionSecured` auto-injecting `tenant_id` into params. SAFE via seam. |
| C2 | `tools/knowledge_tools.py` (`QueryGraphTool._inject_tenant_filter`) | Only filters the **first node alias** in a MATCH clause. For multi-node MATCH (e.g., `MATCH (a)-[:REL]->(b)`), only `a` is tenant-scoped; `b` is reached transitively. This is the tool's design and the approved enforcement point, but worth noting as a partial/conditional concern. |
| C3 | `workflows/queries.py` | Deprecated query builders with **optional** `tenant_id`. SAFE only because `query_graph` tool injects the filter. If these builders are ever called outside the tool, tenant scoping is not guaranteed. |

---

## 7. Methodology & Tooling

- **Existing audit tooling run:**
  - `scripts/ci/check_l3_cypher_tenant_inventory.py` → **342 findings** (278 Safe / 12 Unsafe / 52 Unknown). All 52 "Unknown" manually verified as SAFE (they use approved fail-closed surfaces). The 12 "Unsafe" were reviewed and confirmed to be false positives from the AST scanner (e.g., `.run()` on non-Neo4j objects, docstring examples).
  - `scripts/ci/check_layer3_cypher_scope.py` → scope report.
  - `scripts/audit/layer4_direct_neo4j_calls.py` → ~45 call sites (naive `.run()` matcher; requires UTF-8 workaround on Windows due to cp1252 bug).
  - `scripts/ci/check_vector_store_health.py` → confirms `pgvector_required=false` (Neo4j-native vector is active).
- **Manual verification:** Every query surface in the catalog above was manually inspected for tenant-filter presence and execution seam.
- **Key insight:** The audit must distinguish actual Neo4j `.run()` calls from other `.run()` calls (langgraph state, graph objects, pandas). The naive L4 audit script flags any `.run()`.

---

## 8. Read-Only Verification

- **No code changes were made.** `git status --short` on branch `bmsull560-tenant-filter-audit` shows a clean working tree (only this report artifact exists outside the repo, in the session artifacts directory).
- Enforcement (fail-closed helper) was **not** implemented — it stays in its original slot touching `shared/security`, per the task scope.

---

## 9. Summary Table

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 CRITICAL | 0 | — |
| 🟠 HIGH | 0 | — |
| 🟡 MEDIUM | 1 | GAP-1: L4 `Neo4jVariableRegistry` no tenant scoping |
| ⚪ LOW | 3 | C1-C3: conditional/defense-in-depth observations (SAFE by design) |

**Bottom line:** The tenant-isolation invariant is upheld across all active graph and vector query surfaces. One MEDIUM design gap exists in the L4 `Neo4jVariableRegistry` (internal, no API exposure). No CRITICAL or HIGH gaps were found.