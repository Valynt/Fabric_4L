# Layer 3 Neo4j Migration Registry

This file tracks all Neo4j schema and data migrations for the Layer 3 Knowledge Graph service.

## Policy

- Migrations are numbered sequentially (`NNN_description.py`).
- All migrations must be idempotent (`IF NOT EXISTS` / `IF EXISTS`).
- Each entry must include: ID, description, date applied, owner, and whether it is reversible.
- Migrations are applied in order. Do not renumber or delete entries.

## Registry

| ID | File | Description | Date Applied | Owner | Reversible |
|---|---|---|---|---|---|
| 028 | `028_l3_tenant_standardization.py` | Rename `tenantId` → `tenant_id` on :Formula/:Variable; backfill `tenant_id = 'default'` on :ValueModel/:Benchmark/:BenchmarkPolicy/:FormulaVersion/:SourceBinding | 2026-05-12 | layer3-knowledge | No (data rename) |
| 029 | `029_backfill_sync_metadata_tenant.py` | Backfill `tenant_id` on sync metadata nodes | 2026-05-12 | layer3-knowledge | No (data backfill) |
| 030 | `030_neo4j_tenant_id_constraints_and_indexes.py` | Add NOT NULL existence constraints + btree indexes on `tenant_id` for :Benchmark, :BenchmarkPolicy, :Variable, :SourceBinding, :ValueModel, :Formula, :FormulaVersion | 2026-05-21 | layer3-knowledge | Yes (`DROP CONSTRAINT`/`DROP INDEX`) |

## Named Migrations (no sequence number — utility scripts)

| File | Description | Owner |
|---|---|---|
| `create_composite_tenant_indexes.py` | Composite (tenant_id, name) indexes for :Capability, :UseCase, :Persona, :ValueDriver, :Product, :Organization, :PainSignal, :Evidence | layer3-knowledge |
| `migrate_tenant_ids.py` | Batch backfill `tenant_id` on all existing nodes using APOC periodic iterate | layer3-knowledge |

## Running Migrations

```bash
# Dry run (prints Cypher, no changes)
python -m migrations.030_neo4j_tenant_id_constraints_and_indexes --dry-run

# Execute
NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=<pw> \
  python -m migrations.030_neo4j_tenant_id_constraints_and_indexes
```

## Reverting Migration 030

```cypher
-- Drop constraints
DROP CONSTRAINT benchmark_tenant_id_not_null IF EXISTS;
DROP CONSTRAINT benchmarkpolicy_tenant_id_not_null IF EXISTS;
DROP CONSTRAINT variable_tenant_id_not_null IF EXISTS;
DROP CONSTRAINT sourcebinding_tenant_id_not_null IF EXISTS;
DROP CONSTRAINT valuemodel_tenant_id_not_null IF EXISTS;
DROP CONSTRAINT formula_tenant_id_not_null IF EXISTS;
DROP CONSTRAINT formulaversion_tenant_id_not_null IF EXISTS;

-- Drop indexes
DROP INDEX benchmark_tenant_id_idx IF EXISTS;
DROP INDEX benchmarkpolicy_tenant_id_idx IF EXISTS;
DROP INDEX variable_tenant_id_idx IF EXISTS;
DROP INDEX sourcebinding_tenant_id_idx IF EXISTS;
DROP INDEX valuemodel_tenant_id_idx IF EXISTS;
DROP INDEX formula_tenant_id_idx IF EXISTS;
DROP INDEX formulaversion_tenant_id_idx IF EXISTS;
```
