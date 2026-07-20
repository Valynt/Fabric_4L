# Layer 1 Alembic graph re-validation (2026-05-13)

## Scope
Re-validation command: `python scripts/ci/_check_alembic_graphs.py`.
Re-validation rerun date: `2026-05-13`.

## Conclusion
Layer 1 does not have a true multi-head on this branch. The earlier blocker was parser-induced: the legacy checker only matched simple `revision = "..."` assignments and skipped annotated Alembic metadata in `003` through `010`.

Layer 1 should only be considered migration-ready after this AST-based re-validation; that re-validation has now been rerun and captured below with the exact current Layer 1 graph metadata.

## Layer 1 machine-readable revision summary

```json
[
  {
    "revision": "001",
    "filename": "001_initial.py",
    "down_revision": null,
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "002",
    "filename": "002_pii_and_compliance.py",
    "down_revision": ["001"],
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "003",
    "filename": "003_spec_compliant_schema.py",
    "down_revision": ["002"],
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "004",
    "filename": "004_add_rls_policies.py",
    "down_revision": ["003"],
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "005",
    "filename": "005_add_crawl_path_and_decisions.py",
    "down_revision": ["004"],
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "006",
    "filename": "006_rename_org_to_tenant.py",
    "down_revision": ["005"],
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "007",
    "filename": "007_rename_stale_indexes.py",
    "down_revision": ["006"],
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "008",
    "filename": "008_add_gin_indexes_for_jsonb.py",
    "down_revision": ["007"],
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "009",
    "filename": "009_add_robots_txt_cache.py",
    "down_revision": ["008"],
    "branch_labels": null,
    "depends_on": null
  },
  {
    "revision": "010",
    "filename": "010_add_source_category.py",
    "down_revision": ["009"],
    "branch_labels": null,
    "depends_on": null
  }
]
```

## Evidence: before parser hardening

Legacy line-based parsing only detected unannotated revisions and incorrectly reported a Layer 1 multi-head:

```text
layer1-ingestion: 3 revisions, 2 head(s), 1 root(s)
  HEAD: 002 (002_pii_and_compliance.py)
  HEAD: 006 (006_rename_org_to_tenant.py)
  ROOT: 001 (001_initial.py)

Errors:
  - layer1-ingestion: MULTI-HEAD detected (2 heads: ['002', '006'])
```

## Evidence: after parser hardening

AST-based parsing correctly reads annotated Alembic metadata and shows a single linear Layer 1 chain:

```text
layer1-ingestion: 10 revisions, 1 head(s), 1 root(s)
  HEAD: 010 (010_add_source_category.py)
  ROOT: 001 (001_initial.py)

layer2-extraction: 3 revisions, 1 head(s), 1 root(s)
  HEAD: 20260503_0002 (20260503_0002_add_rls_policies.py)
  ROOT: 20250418_0001 (20250418_0001_add_ontology_schema_tables.py)

layer4-agents: 29 revisions, 1 head(s), 1 root(s)
  HEAD: 029 (029_add_company_knowledge_tables.py)
  ROOT: 001 (001_add_accounts_table.py)

layer5-ground-truth: 8 revisions, 1 head(s), 1 root(s)
  HEAD: 008 (008_ensure_truth_objects_tenant_id.py)
  ROOT: 001 (20240101_0000_a1b2c3d4e5f6_initial_ground_truth_schema.py)

All Alembic revision graphs are clean.
```

## Action taken

- Hardened `scripts/ci/_check_alembic_graphs.py` to parse Alembic metadata with Python AST instead of line matching.
- Re-ran the checker against the current repository state.
- Removed the stale Layer 1 merge-only migration that had been introduced from the earlier false-positive path.

## Gate note
Layer 1 must not be marked migration-ready from the earlier false-positive signal alone. The migration-ready gate is satisfied only by this parser-correct re-validation evidence once this note is committed on the branch. No Layer 1 merge migration is required for the current graph.
