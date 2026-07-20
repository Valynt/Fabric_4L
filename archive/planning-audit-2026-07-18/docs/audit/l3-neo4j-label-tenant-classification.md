# L3 Neo4j Label Tenant Classification Audit

**Audit ID:** phase-1-schema-audit  
**Date:** 2026-05-05  
**Plan:** sunspot-longshot-crimson-avenger.md  
**Auditor:** automated + manual review  

---

## Executive Summary

This audit inventories all Neo4j node labels accessed by Layer 3 route modules, their tenant property status, schema constraints, and indexes. **Critical finding: 6 labels lack proper tenant isolation**, with 4 route modules completely unscoped and 1 route module using a non-canonical property name (`tenantId` instead of `tenant_id`).

| Risk Level | Count | Description |
|------------|-------|-------------|
| 🔴 **Critical** | 4 | Route modules with zero tenant scoping |
| 🟡 **High** | 2 | Labels with wrong/missing tenant property name |
| 🟠 **Medium** | 4 | Labels missing composite (id, tenant_id) constraints |
| 🔵 **Low** | 2 | Labels missing tenant_id indexes |

---

## 1. Route Module Inventory

### 1.1 Completely Tenant-Scoped (Canonical Pattern)

| Module | Status | Pattern | Notes |
|--------|--------|---------|-------|
| `entities.py` | ✅ **SCOPED** | `Neo4jTenantSession` + `tenant_id` | Canonical reference implementation. All queries filter on `e.tenant_id = $tenant_id`. |

### 1.2 Partially Scoped (Non-Canonical Property Name)

| Module | Status | Pattern | Issue |
|--------|--------|---------|-------|
| `formulas.py` | ⚠️ **PARTIAL** | Raw driver, manual `tenantId` param | Uses `tenantId` (camelCase) instead of canonical `tenant_id` (snake_case). Queries use `WHERE f.tenantId = $tenant_id OR f.tenantId IS NULL` — the `IS NULL` clause is a bypass vulnerability. Also MERGEs `:Variable` nodes with `tenantId`. |

### 1.3 Completely Unscoped

| Module | Status | Labels Touched | Auth Pattern |
|--------|--------|----------------|--------------|
| `benchmarks.py` | 🔴 **UNSCOPED** | `:Benchmark`, `:BenchmarkPolicy` | API key |
| `variables.py` | 🔴 **UNSCOPED** | `:Variable`, `:SourceBinding` | API key (some endpoints unauthenticated) |
| `models.py` | 🔴 **UNSCOPED** | `:ValueModel` | Custom JWT extraction (no signature verification) |
| `formula_governance.py` | 🔴 **UNSCOPED** | `:Formula`, `:FormulaVersion` | API key |

---

## 2. Label-by-Label Analysis

### 2.1 `:Formula`

| Attribute | Status | Detail |
|-----------|--------|--------|
| **tenant property** | 🟡 **WRONG NAME** | `tenantId` (camelCase) instead of `tenant_id` (snake_case) |
| **composite constraint** | ❌ **MISSING** | No `(id, tenant_id)` constraint in `constraints.py` |
| **tenant index** | ❌ **MISSING** | No `formula_tenant_idx` in `INDEXES` |
| **create locations** | 1 | `formulas.py:963` — `CREATE (f:Formula {..., tenantId: $tenant_id})` |
| **read locations** | 5 | `formulas.py` (5 queries with `WHERE f.tenantId = $tenant_id OR f.tenantId IS NULL`) |
| **update locations** | 1 | `formula_governance.py` — status transitions, version creation |

**Impact:** The `tenantId` property name mismatch means:
1. Existing composite constraints on `(id, tenant_id)` do NOT cover `:Formula` nodes
2. The `Neo4jTenantSession` wrapper injects `$tenant_id` but `:Formula` nodes store `tenantId` — scoping queries will fail to match
3. The `OR f.tenantId IS NULL` clause in `formulas.py` allows reading unowned formulas across tenants

### 2.2 `:FormulaVersion`

| Attribute | Status | Detail |
|-----------|--------|--------|
| **tenant property** | ❌ **NONE** | No tenant property of any name |
| **composite constraint** | ❌ **MISSING** | Not in `CONSTRAINTS` |
| **tenant index** | ❌ **MISSING** | Not in `INDEXES` |
| **create locations** | 3 | `formulas.py:965`, `formulas.py:1139`, `formula_governance.py:359` |
| **read locations** | 4 | `formulas.py`, `formula_governance.py` |

**Impact:** Formula versions are completely untraceable to tenants. A tenant can read another tenant's formula versions via `formula_governance.py` endpoints.

### 2.3 `:Variable`

| Attribute | Status | Detail |
|-----------|--------|--------|
| **tenant property** | 🟡 **INCONSISTENT** | `variables.py` creates WITHOUT tenant; `formulas.py` MERGEs with `tenantId` |
| **composite constraint** | ✅ **EXISTS** | `variable_id_tenant` in `CONSTRAINTS` |
| **tenant index** | ✅ **EXISTS** | `variable_tenant_idx` in `INDEXES` |
| **create locations** | 2 | `variables.py:361` (no tenant), `formulas.py:995` (with `tenantId`) |
| **read locations** | 6 | `variables.py` (6 endpoints, all unscoped) |

**Impact:** Variables created via `variables.py` have NO tenant property, bypassing the existing constraint (which only enforces uniqueness when `tenant_id` IS present). Variables created via `formulas.py` have `tenantId` (wrong name). The `variables.py` endpoints read all variables without filtering.

### 2.4 `:ValueModel`

| Attribute | Status | Detail |
|-----------|--------|--------|
| **tenant property** | ❌ **NONE** | No tenant property of any name |
| **composite constraint** | ❌ **MISSING** | Not in `CONSTRAINTS` |
| **tenant index** | ❌ **MISSING** | Not in `INDEXES` |
| **create locations** | 1 | `models.py:501` — `CREATE (m:ValueModel {...})` |
| **read locations** | 5 | `models.py` (list, folders, detail, delete) |

**Impact:** Value models are fully unscoped. The module has user-level ownership (`m.owner = $user_id`) but this is NOT tenant isolation — a user with the same ID across tenants can access all their models regardless of tenant.

### 2.5 `:Benchmark`

| Attribute | Status | Detail |
|-----------|--------|--------|
| **tenant property** | ❌ **NONE** | No tenant property of any name |
| **composite constraint** | ❌ **MISSING** | Not in `CONSTRAINTS` |
| **tenant index** | ❌ **MISSING** | Not in `INDEXES` |
| **create locations** | 0 | No CREATE/MERGE found in codebase |
| **read locations** | 3 | `benchmarks.py` (list, get, policy list/update) |

**Impact:** Benchmark nodes have no known creation path in application code — likely created by external ETL/ingestion. Without tenant properties, all benchmarks are globally visible. Note: `value_packs.py` uses a DIFFERENT label `:BenchmarkDataset` which IS scoped.

### 2.6 `:BenchmarkPolicy`

| Attribute | Status | Detail |
|-----------|--------|--------|
| **tenant property** | ❌ **NONE** | No tenant property of any name |
| **composite constraint** | ❌ **MISSING** | Not in `CONSTRAINTS` |
| **tenant index** | ❌ **MISSING** | Not in `INDEXES` |
| **create locations** | 0 | No CREATE/MERGE found in codebase |
| **read locations** | 1 | `benchmarks.py` (list, update) |

**Impact:** Policy updates in `benchmarks.py` affect global policies. No tenant-aware policy isolation exists.

### 2.7 `:SourceBinding`

| Attribute | Status | Detail |
|-----------|--------|--------|
| **tenant property** | ❌ **NONE** | No tenant property of any name |
| **composite constraint** | ❌ **MISSING** | Not in `CONSTRAINTS` |
| **tenant index** | ❌ **MISSING** | Not in `INDEXES` |
| **create locations** | 0 | No CREATE/MERGE found in codebase |
| **read locations** | 1 | `variables.py` (`list_source_bindings`) |

---

## 3. Constraint Compatibility Matrix

| Label | Constraint Name | Properties | Status |
|-------|-----------------|------------|--------|
| `:Capability` | `capability_id_tenant` | `(id, tenant_id)` | ✅ |
| `:UseCase` | `usecase_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Persona` | `persona_id_tenant` | `(id, tenant_id)` | ✅ |
| `:ValueDriver` | `valuedriver_id_tenant` | `(id, tenant_id)` | ✅ |
| `:ValueMetric` | `valuemetric_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Product` | `product_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Feature` | `feature_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Service` | `service_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Solution` | `solution_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Technology` | `technology_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Organization` | `organization_id_tenant` | `(id, tenant_id)` | ✅ |
| `:BusinessUnit` | `businessunit_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Process` | `process_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Activity` | `activity_id_tenant` | `(id, tenant_id)` | ✅ |
| `:APQCProcess` | `apqcprocess_id_tenant` | `(id, tenant_id)` | ✅ |
| `:BIANServiceDomain` | `bianservicedomain_id_tenant` | `(id, tenant_id)` | ✅ |
| `:FIBOEntity` | `fiboentity_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Industry` | `industry_id_tenant` | `(id, tenant_id)` | ✅ |
| `:MarketSegment` | `marketsegment_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Geography` | `geography_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Regulation` | `regulation_id_tenant` | `(id, tenant_id)` | ✅ |
| `:DataSource` | `datasource_id_tenant` | `(id, tenant_id)` | ✅ |
| `:ExtractionEvent` | `extractionevent_id_tenant` | `(id, tenant_id)` | ✅ |
| `:ConfidenceScore` | `confidencescore_id_tenant` | `(id, tenant_id)` | ✅ |
| `:ValuePack` | `valuepack_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Variable` | `variable_id_tenant` | `(id, tenant_id)` | ✅ (but nodes often lack tenant_id) |
| `:BenchmarkDataset` | `benchmarkdataset_id_tenant` | `(id, tenant_id)` | ✅ |
| `:PainSignal` | `painsignal_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Evidence` | `evidence_id_tenant` | `(id, tenant_id)` | ✅ |
| `:Formula` | — | — | ❌ **MISSING** |
| `:Benchmark` | — | — | ❌ **MISSING** |
| `:ValueModel` | — | — | ❌ **MISSING** |
| `:BenchmarkPolicy` | — | — | ❌ **MISSING** |
| `:FormulaVersion` | — | — | ❌ **MISSING** |
| `:SourceBinding` | — | — | ❌ **MISSING** |

---

## 4. Index Compatibility Matrix

| Label | Index Name | Properties | Status |
|-------|-----------|------------|--------|
| `:Variable` | `variable_tenant_idx` | `[tenant_id]` | ✅ |
| `:BenchmarkDataset` | `benchmarkdataset_tenant_idx` | `[tenant_id]` | ✅ |
| `:Formula` | — | — | ❌ **MISSING** |
| `:Benchmark` | — | — | ❌ **MISSING** |
| `:ValueModel` | — | — | ❌ **MISSING** |
| `:BenchmarkPolicy` | — | — | ❌ **MISSING** |
| `:FormulaVersion` | — | — | ❌ **MISSING** |
| `:SourceBinding` | — | — | ❌ **MISSING** |

---

## 5. Property Name Standardization Issues

### 5.1 Canonical Property Name

The canonical tenant property name is **`tenant_id`** (snake_case). This is used by:
- All composite constraints in `constraints.py`
- All tenant indexes in `INDEXES`
- `entities.py` (canonical scoped module)
- `value_packs.py` for `:BenchmarkDataset`
- All retrieval services (`graph_rag.py`, `vector_store.py`)

### 5.2 Non-Canonical Usage

| Location | Property Name | Used On | Issue |
|----------|---------------|---------|-------|
| `formulas.py:963` | `tenantId` | `:Formula` | Wrong case — breaks constraint compatibility |
| `formulas.py:995` | `tenantId` | `:Variable` | Wrong case — inconsistent with `variables.py` |
| `formulas.py:1174` | `tenantId` | `:Variable` | Wrong case — same issue |

### 5.3 Missing Property

| Location | Labels | Issue |
|----------|--------|-------|
| `variables.py:361` | `:Variable` | CREATE does not set any tenant property |
| `models.py:501` | `:ValueModel` | CREATE does not set any tenant property |
| `formula_governance.py:359` | `:FormulaVersion` | CREATE does not set any tenant property |
| (external) | `:Benchmark`, `:BenchmarkPolicy` | No creation path in app code |

---

## 6. Existing Migration Script Analysis

**File:** `services/layer3-knowledge/src/migrations/migrate_tenant_ids.py`

| Capability | Status | Limitation |
|------------|--------|------------|
| Backfill `tenant_id` on nodes where `tenant_id IS NULL` | ✅ | Works for labels that already use `tenant_id` |
| Rename `tenantId` → `tenant_id` on `:Formula` | ❌ | Not implemented |
| Add `tenant_id` to labels that never had it | ⚠️ | Partial — only if node has `tenant_id IS NULL`, which is true for never-set properties |
| Create constraints after migration | ✅ | Creates constraints from `CONSTRAINTS` list only |
| Handle `:FormulaVersion` | ❌ | Not specifically addressed |
| Handle `:Benchmark` / `:BenchmarkPolicy` | ❌ | Not specifically addressed |

**Conclusion:** The existing migration script is insufficient for Phase 2. It needs enhancement to:
1. Rename `tenantId` → `tenant_id` on `:Formula` and `:Variable` nodes
2. Explicitly backfill `tenant_id` on `:ValueModel`, `:Benchmark`, `:BenchmarkPolicy`, `:FormulaVersion`, `:SourceBinding`
3. Create missing constraints for newly-scoped labels

---

## 7. Cross-Module Data Flow Risks

### 7.1 Variable Created via `formulas.py` → Read via `variables.py`

```
formulas.py MERGE (v:Variable {name: $name, tenantId: $tenant_id})
    ↓
variables.py MATCH (v:Variable {id: $variable_id}) RETURN v
    ↓
[NO TENANT FILTER] → Cross-tenant leak
```

### 7.2 Formula Created via `formulas.py` → Governed via `formula_governance.py`

```
formulas.py CREATE (f:Formula {..., tenantId: $tenant_id})
    ↓
formula_governance.py MATCH (f:Formula {id: $formula_id}) RETURN f
    ↓
[NO TENANT FILTER] → Cross-tenant leak
```

### 7.3 ValuePack with BenchmarkDataset → Read via benchmarks.py

```
value_packs.py CREATE/READ :BenchmarkDataset with tenant_id
    ↓
benchmarks.py MATCH (b:Benchmark) RETURN b
    ↓
Different label (:Benchmark vs :BenchmarkDataset) — may be same data, different isolation
```

---

## 8. Recommended Schema Changes (Phase 2 Input)

### 8.1 Constraints to Add

```python
# Add to CONSTRAINTS list in constraints.py
Constraint("formula_id_tenant", "Formula", ["id", "tenant_id"], "unique"),
Constraint("benchmark_id_tenant", "Benchmark", ["id", "tenant_id"], "unique"),
Constraint("valuemodel_id_tenant", "ValueModel", ["model_id", "tenant_id"], "unique"),
Constraint("benchmarkpolicy_id_tenant", "BenchmarkPolicy", ["id", "tenant_id"], "unique"),
Constraint("formulaversion_id_tenant", "FormulaVersion", ["id", "tenant_id"], "unique"),
Constraint("sourcebinding_id_tenant", "SourceBinding", ["id", "tenant_id"], "unique"),
```

**Note:** `:ValueModel` uses `model_id` as its primary identifier, not `id`. The constraint must match the actual identifier property.

### 8.2 Indexes to Add

```python
# Add to INDEXES list in constraints.py
Index("formula_tenant_idx", "Formula", ["tenant_id"], "btree"),
Index("formula_tenant_id_idx", "Formula", ["tenant_id", "id"], "btree"),
Index("benchmark_tenant_idx", "Benchmark", ["tenant_id"], "btree"),
Index("valuemodel_tenant_idx", "ValueModel", ["tenant_id"], "btree"),
Index("valuemodel_tenant_modelid_idx", "ValueModel", ["tenant_id", "model_id"], "btree"),
Index("benchmarkpolicy_tenant_idx", "BenchmarkPolicy", ["tenant_id"], "btree"),
Index("formulaversion_tenant_idx", "FormulaVersion", ["tenant_id"], "btree"),
Index("sourcebinding_tenant_idx", "SourceBinding", ["tenant_id"], "btree"),
```

### 8.3 Enterprise Existence Constraints to Add

```python
# Add to TENANT_CONSTRAINTS list in constraints.py
Constraint("benchmark_tenant_id", "Benchmark", "tenant_id", "exists"),
Constraint("valuemodel_tenant_id", "ValueModel", "tenant_id", "exists"),
Constraint("benchmarkpolicy_tenant_id", "BenchmarkPolicy", "tenant_id", "exists"),
Constraint("formulaversion_tenant_id", "FormulaVersion", "tenant_id", "exists"),
Constraint("sourcebinding_tenant_id", "SourceBinding", "tenant_id", "exists"),
```

---

## 9. Migration Script Requirements (Phase 2 Input)

### 9.1 Cypher Migration: Rename `tenantId` → `tenant_id`

```cypher
// Rename on :Formula
MATCH (f:Formula)
WHERE f.tenantId IS NOT NULL
SET f.tenant_id = f.tenantId
REMOVE f.tenantId

// Rename on :Variable (created via formulas.py)
MATCH (v:Variable)
WHERE v.tenantId IS NOT NULL
SET v.tenant_id = v.tenantId
REMOVE v.tenantId
```

### 9.2 Cypher Migration: Backfill Missing `tenant_id`

```cypher
// :ValueModel
MATCH (m:ValueModel)
WHERE m.tenant_id IS NULL
SET m.tenant_id = 'default'

// :Benchmark
MATCH (b:Benchmark)
WHERE b.tenant_id IS NULL
SET b.tenant_id = 'default'

// :BenchmarkPolicy
MATCH (bp:BenchmarkPolicy)
WHERE bp.tenant_id IS NULL
SET bp.tenant_id = 'default'

// :FormulaVersion
MATCH (fv:FormulaVersion)
WHERE fv.tenant_id IS NULL
SET fv.tenant_id = 'default'

// :SourceBinding
MATCH (sb:SourceBinding)
WHERE sb.tenant_id IS NULL
SET sb.tenant_id = 'default'

// :Variable (nodes created via variables.py)
MATCH (v:Variable)
WHERE v.tenant_id IS NULL AND v.tenantId IS NULL
SET v.tenant_id = 'default'
```

### 9.3 Backfill Strategy Notes

- **`:Formula`**: Already has `tenantId` → rename to `tenant_id`. Some nodes may have `tenantId IS NULL` (created before tenant scoping) → backfill with `'default'`.
- **`:Variable`**: Mixed population — some have `tenantId` (from `formulas.py`), some have neither (from `variables.py`). Rename first, then backfill remainder.
- **`:ValueModel`**: Never had tenant property → backfill all with `'default'`.
- **`:Benchmark` / `:BenchmarkPolicy`**: No creation path in app code → backfill all with `'default'`.
- **`:FormulaVersion`**: Never had tenant property → backfill all with `'default'`.
- **`:SourceBinding`**: Never had tenant property → backfill all with `'default'`.

---

## 10. Audit Checklist

- [x] All L3 route modules inventoried
- [x] All Neo4j labels touched by route modules identified
- [x] Property presence/absence documented per label
- [x] Constraint inventory cross-referenced with `constraints.py`
- [x] Index inventory cross-referenced with `INDEXES`
- [x] Property name standardization issues identified
- [x] CREATE query locations mapped
- [x] Cross-module data flow risks analyzed
- [x] Existing migration script gap analysis completed
- [x] Recommended schema changes documented
- [x] Backfill strategy documented

---

## 11. Sign-off

| Role | Name | Date | Status |
|------|------|------|--------|
| Auditor | automated | 2026-05-05 | ✅ Complete |
| Security Review | — | — | Pending |
| DBA Review | — | — | Pending |

**Next Step:** Proceed to Phase 2 (Canonical Property Migration) using the schema changes and migration scripts documented in Section 8 and Section 9.
