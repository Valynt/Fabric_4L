# Slice T — Neo4j / pgvector Tenant-Filter Audit: Gap Report

**Slice:** T (S22-A1 audit half, pulled forward)
**Mode:** Read-only investigation — **no code changes made**
**Branch:** `bmsull560-tenant-filter-audit`
**Date:** 2026-09-05
**Scope:** Catalog every graph (Neo4j/Cypher) and vector (pgvector / Neo4j-native vector / Pinecone) query in the monorepo, plus the related full-text (BM25) retrieval surfaces that share the same tenant-filter invariant; check each for tenant-filter presence; report gaps.

---

## 1. Executive Summary

The audit cataloged every graph and vector query surface across the monorepo and checked each for tenant-filter presence. **The tenant-isolation invariant is overwhelmingly upheld.** The vast majority of query sites route through approved fail-closed execution seams that either force-assign `tenant_id` or reject queries lacking an explicit tenant predicate.

**38 query surfaces were cataloged** (30 graph/Cypher, 5 vector, 3 full-text BM25). The full-text (BM25) surfaces are included because they share the same tenant-filter invariant and are part of the hybrid retrieval path; they are counted separately from the graph and vector surfaces so the totals reconcile with the catalog tables below.

**Two gaps were confirmed.** The primary one is the Layer 4 `Neo4jVariableRegistry`, which performs CRUD/search with **no tenant scoping whatsoever** (no `tenant_id` property on the model, no tenant filter on any query). This is assessed as **MEDIUM** severity (design gap) because pack variable definitions are global templates loaded at startup/CI, but it violates the invariant that *every graph query carries a tenant filter*. A second, **LOW** defense-in-depth gap exists in the `query_graph` tool, whose tenant filter scopes only the first node alias of a MATCH clause (see GAP-2).

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
| `TenantScopedCypher` | `packages/shared/src/value_fabric/shared/identity/isolation.py` L304 | Always injects `_tenant_id` param + tenant predicates |
| `custom_tenant_query` | `packages/shared/src/value_fabric/shared/identity/isolation.py` L665 | Requires `$_tenant_id`/`$tenant_id` reference AND explicit tenant predicate (raises ValueError otherwise) |
| `SystemCypher` | `packages/shared/src/value_fabric/shared/identity/isolation.py` L189 | Schema/migration/backup/health (system-scoped, no tenant data) |
| `Neo4jTenantSessionSecured.run` | `api/dependencies_tenant_secured.py` L106 | Validates Cypher text (blocks broad MATCH without tenant predicate), **auto-injects `tenant_id`/`_tenant_id` into params**, runs through `TenantQueryExecutor` |
| `ValidatedNeo4jSession` | `security/query_validator.py` L416 | Routes through `TenantQueryExecutor`, fail-closed |

### Layer 4 (`services/layer4-agents`)
| Seam | Location | Behavior |
|------|----------|----------|
| `fetch_tenant_validated_records` / `fetch_tenant_validated_single` | `services/tenant_cypher.py` | Validate query has explicit tenant_id predicate + force-assign params |
| `QueryGraphTool._inject_tenant_filter` | `tools/knowledge_tools.py` L100-160 | Injects `<alias>.tenant_id = $tenant_id` on first node alias |
| `QueryGraphTool._ensure_tenant_parameters` | `tools/knowledge_tools.py` L162-180 | Rejects tenant spoofing |
| `QueryGraphTool.execute` | `tools/knowledge_tools.py` L192+ | Requires valid `TenantContext` fail-closed |
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
| 12 | `api/routes/variables.py` | `create_neo4j_tenant_session(tenant_id)` + `WHERE v.tenant_id = $tenant_id` (L223/288/377/452/512/539/604/720/755) | Yes — all queries tenant-scoped | ✅ SAFE |
| 13 | `db/dual_store_coordinator.py` | pgvector fallback writes/compensating deletes | Requires explicit `tenant_id` (raises ValueError if missing) | ✅ SAFE |

### 3.2 Layer 4 — Agents (`services/layer4-agents`)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 14 | `services/context_gatherer.py` | `MATCH (s:Signal {tenant_id: $tenant_id})` etc. via `run_tenant_validated_query` | Yes | ✅ SAFE |
| 15 | `services/formula_governance_service.py` | All `MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 16 | `services/intelligence_orchestrator.py` | All `MATCH (... {tenant_id: $tenant_id})` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 17 | `services/value_pack_service.py` | All `MATCH (vp:ValuePack {tenant_id: $tenant_id})` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 18 | `services/value_hypothesis_engine.py` | `where_clauses = ["vh.tenant_id = $tenant_id", ...]` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 19 | `services/narrative_builder_service.py` | `where_clauses = ["n.tenant_id = $tenant_id"]` via `fetch_tenant_validated_records` | Yes | ✅ SAFE |
| 20 | `tools/knowledge.py` | Direct Neo4j queries | All tenant-filtered | ✅ SAFE |
| 21 | `tools/knowledge_tools.py` (`QueryGraphTool`) | `_inject_tenant_filter` on first node alias | Injects `<alias>.tenant_id = $tenant_id`; rejects spoofing; fail-closed | ✅ SAFE |
| 22 | `tools/competitive_tools.py` | `_query_graph_for_competitor` L229-270 | `MATCH (c:Competitor {name: $name, tenant_id: $tenant_id})` + `WHERE cap/risk/cs.tenant_id = $tenant_id` | ✅ SAFE |
| 23 | `workflows/whitespace.py` L288 | `MATCH (c:Capability)` via `query_graph` tool | Injected by tool | ✅ SAFE |
| 24 | `workflows/queries.py` | Deprecated builders with optional tenant_id | Injected by `query_graph` tool | ✅ SAFE |
| 25 | `workflows/business_case.py` L378 | Passes tenant_id through `query_graph` | Injected by tool | ✅ SAFE |
| 26 | `workflows/roi_calculator.py` L426/511 | `query_graph` tool calls (benchmark_variables, value_drivers) | `tenant_id` passed into tool input; injected by tool | ✅ SAFE |
| 27 | `integration/layer3_client.py` | HTTP client (not direct query) | Tenant propagated via `X-Tenant-ID` header | ✅ SAFE |
| 28 | `agents/audit_orchestrator/persistence.py` | Direct Neo4j queries | All tenant-filtered | ✅ SAFE |
| 29 | `api/routes/analysis_workspace.py` | Direct Neo4j queries | All tenant-filtered | ✅ SAFE |
| 30 | **`services/variable_registry_service.py`** | `Neo4jVariableRegistry` CRUD/search | **NO tenant scoping** | 🔴 **GAP** |

---

## 4. Vector Query Catalog

### 4.1 Neo4j-native vector store (ACTIVE backend)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 31 | `retrieval/vector_store.py` | `_build_vector_search_query` L174-187 (`db.index.vector.queryNodes`) | `WHERE node.tenant_id = $_tenant_id` | ✅ SAFE |
| 32 | `services/evidence_search.py` L86/112 | `db.index.vector.queryNodes('evidence_embedding_idx', ...)` | `WHERE node.tenant_id = $tenant_id` | ✅ SAFE |
| 33 | `services/entity_resolution.py` L61 | `_build_vector_query` (`db.index.vector.queryNodes`) | `WHERE node:{entity_type} AND node.tenant_id = $tenant_id` | ✅ SAFE |

### 4.2 pgvector (fallback / secondary store)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 34 | `db/dual_store_coordinator.py` | pgvector fallback writes/compensating deletes | Requires explicit `tenant_id` (raises ValueError if missing) | ✅ SAFE |

> **Note:** `scripts/ci/check_vector_store_health.py` confirms `pgvector_required=false` — pgvector is a fallback, not the active backend. The active vector store is Neo4j-native vector indexes.

### 4.3 Pinecone (Layer 4)

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 35 | `tools/knowledge_tools.py` (`SemanticSearchTool`) | `index.query(...)` | Requires valid `TenantContext` (fail-closed); `filter_dict = {"tenant_id": str(tenant_ctx.tenant_id)}` injected into Pinecone metadata filter | ✅ SAFE |

### 4.4 Full-text (BM25) — related retrieval surface

> **Note:** These full-text (BM25) surfaces are part of the hybrid retrieval path and share the same tenant-filter invariant. They are cataloged here for completeness and counted separately (rows 36-38) so the 38-surface total reconciles with the graph (30) and vector (5) counts above.

| # | File | Query site | Tenant filter | Status |
|---|------|-----------|---------------|--------|
| 36 | `retrieval/hybrid_search.py` L321 | `db.index.fulltext.queryNodes` via `TenantScopedCypher.custom_tenant_query` | `$_tenant_id` | ✅ SAFE |
| 37 | `retrieval/graph_rag.py` L546-576 | `db.index.fulltext.queryNodes` via `TenantScopedCypher.custom_tenant_query` | `$_tenant_id` | ✅ SAFE |
| 38 | `services/evidence_search.py` L188/209 | `db.index.fulltext.queryNodes` via `run_validated_query` | `tenant_id` | ✅ SAFE |

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

### GAP-2 (LOW): `QueryGraphTool._inject_tenant_filter` scopes only the first node alias

**File:** `services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py` L100-160

`_inject_tenant_filter` injects `<alias>.tenant_id = $tenant_id` on the **first node alias** of a MATCH clause only. For a multi-node MATCH such as `MATCH (a:Account) MATCH (b:Account) RETURN b`, only `a` is tenant-scoped; `b` is not, so `b` can return records from every tenant. The same applies to multi-node patterns like `MATCH (a)-[:REL]->(b)` where `b` is reached transitively.

**Risk assessment:**
- **Severity: LOW** — the tool is the approved enforcement point and rejects tenant spoofing (`_ensure_tenant_parameters`), and all current in-repo call sites pass a single-node MATCH or rely on the first alias being the tenant-owned node. No current call site is known to exploit the multi-alias path. However, the seam does not guarantee tenant isolation for arbitrary multi-alias queries, so it is a defense-in-depth gap rather than fully SAFE.
- **Exploitability:** Low — requires an LLM/agent to author a multi-alias MATCH that returns a non-first alias; the tool's `_ensure_tenant_parameters` still blocks tenant-parameter spoofing.
- **Impact if exploited:** Cross-tenant read of graph nodes reachable via a non-first alias.

**Recommended fix (NOT applied — out of scope for this read-only audit):** Extend `_inject_tenant_filter` to scope **every** matched node alias, or reject multi-clause/multi-alias MATCH queries that do not carry an explicit tenant predicate on each alias. This belongs in the enforcement sprint touching `shared/security`.

---

## 6. Conditional / Defense-in-Depth Observations (SAFE by design, worth documenting)

These are not gaps — tenant filtering is enforced by a wrapper seam rather than being explicit in the query text. They are SAFE but rely on the seam being correct.

| # | File | Observation |
|---|------|-------------|
| C1 | `api/routes/entities.py` L235/252/275 | Direct `neo4j.execute_query` raw Cypher with `tenant_id` predicates in query text; relies on `Neo4jTenantSessionSecured` auto-injecting `tenant_id` into params. SAFE via seam. |
| C2 | `workflows/queries.py` | Deprecated query builders with **optional** `tenant_id`. SAFE only because `query_graph` tool injects the filter. If these builders are ever called outside the tool, tenant scoping is not guaranteed. |

---

## 7. Methodology & Tooling

- **Existing audit tooling run:**
  - `scripts/ci/check_l3_cypher_tenant_inventory.py` → **342 findings** (278 Safe / 12 Unsafe / 52 Unknown). All 52 "Unknown" manually verified as SAFE (they use approved fail-closed surfaces). The 12 "Unsafe" were reviewed and confirmed to be false positives from the AST scanner (e.g., `.run()` on non-Neo4j objects, docstring examples).
  - `scripts/ci/check_layer3_cypher_scope.py` → scope report.
  - `scripts/audit/layer4_direct_neo4j_calls.py` → ~45 call sites (naive `.run()` matcher; requires UTF-8 workaround on Windows due to cp1252 bug).
  - `scripts/ci/check_vector_store_health.py` → confirms `pgvector_required=false` (Neo4j-native vector is active).
- **Manual verification:** Every query surface in the catalog above was manually inspected for tenant-filter presence and execution seam.
- **Key insight:** The audit must distinguish actual Neo4j `.run()` calls from other `.run()` calls (langgraph state, graph objects, pandas). The naive L4 audit script flags any `.run()`.

### Relationship to the canonical Cypher audit artifacts

This report is a **distinct Slice T evidence artifact** scoped to the tenant-filter audit. It complements, and does not replace, the canonical Cypher audit artifacts:
- `docs/audit/l3-l4-cypher-scope-report.md` — the canonical cross-layer Cypher scope report.
- `docs/audit/l3-cypher-tenant-inventory.json` — the machine-readable L3 tenant-inventory artifact.

Where this report and the canonical artifacts overlap (e.g., the L3 inventory's 342 findings), this report records the manual tenant-filter classification and the confirmed gaps. Any future change to the enforcement seams or the `query_graph` tool should update both this report and the canonical artifacts to avoid drift.

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
| ⚪ LOW | 3 | GAP-2: `query_graph` first-alias-only tenant filter; C1-C2: conditional/defense-in-depth observations (SAFE by design) |

**Bottom line:** The tenant-isolation invariant is upheld across all active graph and vector query surfaces. Two gaps exist: one MEDIUM design gap in the L4 `Neo4jVariableRegistry` (internal, no API exposure) and one LOW defense-in-depth gap in the `query_graph` tool's first-alias-only tenant filter. No CRITICAL or HIGH gaps were found.