# Layer 3 Mutation Path Inventory

**Generated**: 2026-05-25
**Purpose**: Catalog all direct Cypher MERGE/CREATE/DELETE relationship operations for migration to AuditedGraphMutation

## Summary

- **Total files with direct mutations**: 12
- **Routes with direct mutations**: 6
- **Services with direct mutations**: 5
- **Ingestion modules with direct mutations**: 2
- **Files using AuditedGraphMutation**: 1 (audited_mutation.py itself)

## Routes (api/routes/)

### value_packs.py
**Location**: `services/layer3-knowledge/src/api/routes/value_packs.py`
**Lines**: 363-370, 372-380, 1485-1517
**Operations**:
- DELETE existing relationships (hasDriver, hasFormula, hasBenchmark)
- CREATE new relationships with dynamic interpolation
- MERGE ValuePack, ValueDriver, UseCase, EconomicModel nodes and relationships
**Risk**: HIGH - Dynamic relationship type interpolation, allowlisted but bypasses audit
**Priority**: P1

### signals.py
**Location**: `services/layer3-knowledge/src/api/routes/signals.py`
**Lines**: 70-84
**Operations**:
- MERGE ValueSignal node
- MERGE SIGNAL_FOR relationship to Account
**Risk**: MEDIUM - Direct MERGE, no audit
**Priority**: P1

### models_router.py
**Location**: `services/layer3-knowledge/src/api/routes/models_router.py`
**Lines**: 538+
**Operations**:
- DELETE ValueModel with relationships
**Risk**: MEDIUM - Direct DELETE, no audit
**Priority**: P1

### formulas.py
**Location**: `services/layer3-knowledge/src/api/routes/formulas.py`
**Lines**: 1118, 1303
**Operations**:
- MERGE Variable nodes with ON CREATE/ON MATCH
**Risk**: MEDIUM - Direct MERGE, no audit
**Priority**: P2

### evidence.py
**Location**: `services/layer3-knowledge/src/api/routes/evidence.py`
**Lines**: 365
**Operations**:
- MERGE HAS_EVIDENCE relationship between ValueDriver and Evidence
**Risk**: MEDIUM - Direct MERGE, no audit
**Priority**: P1

### benchmarks.py
**Location**: `services/layer3-knowledge/src/api/routes/benchmarks.py`
**Lines**: 345
**Operations**:
- MERGE BenchmarkPolicy node
**Risk**: LOW - Node creation only, no relationships
**Priority**: P2

## Services (services/)

### signal_persistence.py
**Location**: `services/layer3-knowledge/src/services/signal_persistence.py`
**Lines**: 105-109, 151-154, 200, 341
**Operations**:
- MERGE PainSignal node
- MERGE exhibits relationship (Account -> PainSignal)
- MERGE Evidence node
- MERGE supportedBy relationship (PainSignal -> Evidence)
- MERGE mapsTo relationship (PainSignal -> ValueDriver)
- MERGE quantifiedBy relationship (PainSignal -> Formula)
**Risk**: HIGH - Multiple relationship writes, no audit
**Priority**: P1

### product_service.py
**Location**: `services/layer3-knowledge/src/services/product_service.py`
**Lines**: 460
**Operations**:
- MERGE ENABLES_CAPABILITY relationship (Product -> Capability)
**Risk**: MEDIUM - Direct MERGE, no audit
**Priority**: P1

### evidence_search.py
**Location**: `services/layer3-knowledge/src/services/evidence_search.py`
**Lines**: 292
**Operations**:
- MERGE Evidence node
**Risk**: LOW - Node creation only
**Priority**: P2

### competitive_intel_service.py
**Location**: `services/layer3-knowledge/src/services/competitive_intel_service.py`
**Lines**: 423
**Operations**:
- MERGE COMPETES_WITH relationship
**Risk**: MEDIUM - Direct MERGE, no audit
**Priority**: P2

### case_study_service.py
**Location**: `services/layer3-knowledge/src/services/case_study_service.py`
**Lines**: 259, 273, 352
**Operations**:
- MERGE DEMONSTRATES relationship (Product -> Evidence)
- MERGE supportedBy relationship (PainSignal -> Evidence)
- DELETE case study and relationships
**Risk**: MEDIUM - Multiple relationship writes, no audit
**Priority**: P1

## Ingestion (ingestion/)

### sync_manager.py
**Location**: `services/layer3-knowledge/src/ingestion/sync_manager.py`
**Lines**: 275, 347
**Operations**:
- DELETE SyncMetadata node
- CREATE SyncMetadata node
**Risk**: LOW - System metadata, not tenant-owned business data
**Priority**: P3 (system scope, may bypass gateway with justification)

### neo4j_loader.py
**Location**: `services/layer3-knowledge/src/ingestion/neo4j_loader.py`
**Lines**: 511-525, 594-605, 668, 728, 741
**Operations**:
- MERGE entity nodes (batch)
- CALL apoc.merge.relationship (if APOC enabled)
- MERGE relationships (batch, grouped by type)
- DELETE relationships by source_id
- DELETE entities by source_id
**Risk**: HIGH - Bulk operations, batch writes, no audit
**Priority**: P1 (but may need special handling for bulk performance)

## Migration Priority Order

### Phase 1A (Critical - Immediate)
1. `value_packs.py` - Dynamic relationship interpolation, high-risk
2. `signal_persistence.py` - Multiple relationship types, high volume
3. `neo4j_loader.py` - Bulk ingestion, needs special bulk API

### Phase 1B (High Priority)
4. `signals.py` - Signal creation
5. `evidence.py` - Evidence linking
6. `product_service.py` - Product-capability linking
7. `case_study_service.py` - Case study relationships

### Phase 1C (Medium Priority)
8. `models_router.py` - Model deletion
9. `formulas.py` - Variable creation
10. `competitive_intel_service.py` - Competitive intel relationships
11. `evidence_search.py` - Evidence node creation

### Phase 1D (Low Priority / System Scope)
12. `benchmarks.py` - Benchmark policy creation
13. `sync_manager.py` - System metadata (may remain as-is with documentation)

## Bypass Paths to Block

1. **Direct session.run() in routes** - All routes should use AuditedGraphMutation
2. **Direct session.run() in services** - All services should use AuditedGraphMutation
3. **Bulk operations in neo4j_loader** - Need bulk API in AuditedGraphMutation
4. **APOC merge.relationship** - Need native Cypher equivalent in gateway

## Required Enhancements to AuditedGraphMutation

1. **Node operations**:
   - `write_node(label, properties)` - CREATE/MERGE with audit
   - `delete_node(label, id)` - DELETE with audit

2. **Bulk operations**:
   - `write_nodes_batch(label, properties_list)` - Batch node writes
   - `write_relationships_batch(rel_type, triples_list)` - Batch relationship writes
   - `delete_by_source(source_id)` - Bulk delete by source

3. **Context enrichment**:
   - Add `request_id` parameter
   - Add `account_id` parameter
   - Add `operation_source` parameter (route/service name)

4. **Metrics integration**:
   - Hook into PrometheusMetrics for mutation rate
   - Track mutation failures by type

5. **Runtime guard**:
   - Add to TenantQueryExecutor to reject CREATE/MERGE/DELETE on tenant-owned labels
   - Allow only through AuditedGraphMutation
