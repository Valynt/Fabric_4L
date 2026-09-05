# Task DAG — Topological Order (from release/v1/tasks/)

```
V1-CARTO-001 (P0, read-only)
├── V1-TENANCY-010 (P0) queue/worker tenant scope   [wave 1, parallel]
├── V1-TENANCY-011 (P0) object storage/signed URLs  [wave 1, parallel]
├── V1-TENANCY-012 (P0) graph/vector/AI context     [wave 1, parallel]
├── V1-GOLDEN-001 (P0) backend golden-path cert     [wave 2]
├── V1-MIGRATE-001 (P0) expand-contract migration   [wave 2]
├── V1-EVALS-001  (P1) eval manifest-first          [wave 2]
└── V1-CI-001     (P1) aggregate PR checks          [wave 2]
V1-GOLDEN-002 (P0) <- GOLDEN-001                    [wave 3]
V1-OPS-001    (P1) <- GOLDEN-001                    [wave 3]
```

## Collision-free ownership
- TENANCY-010: services/layer1-ingestion, services/layer2-extraction, packages/shared, tests/tenancy
- TENANCY-011: services/layer1-ingestion, services/api, packages/shared, tests/tenancy, tests/data_lifecycle
- TENANCY-012: services/layer3-knowledge, services/layer4-agents, packages/shared, tests/tenancy, tests/security
- packages/shared is shared: sequenced — TENANCY-010 first if it touches shared; others must rebase.

## Wave 1 scope (this branch)
CARTO-001 evidence + test-first hostile tests for TENANCY-010/011/012 (Red phase), minimal fixes where tests expose real defects (Green phase), auditor+security review, PR.
