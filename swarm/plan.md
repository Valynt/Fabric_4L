# Fabric_4L — Agentic Swarm "Last 20%" Execution Plan

Repo: Valynt/Fabric_4L | Scope: full pipeline (implement, test, review, PRs) | Outputs: branch + PR via fork valyntxyz/Fabric_4L

## Stage 1 — Architectural Baseline & Constraint Freezing (DONE)
- Canonical invariant spec already frozen in-repo: `release/v1/launch-contract.yaml` (status: frozen), `release/v1/architecture-invariants.yaml`, `production-readiness/risk_register.yaml`. Swarm adopts these as the immutable contract anchor — no parallel gate system (INV-FACTORY-001).
- Baseline findings: canonical readiness docs (docs/readiness/current.md, launch-decision-artifact.md) are June snapshots superseded by later audits; active development continues on main (Value Studio, L4 Agent Runtime).

## Stage 2 — DAG Task Decomposition (DONE)
Canonical task DAG from `release/v1/tasks/`:
- Root: V1-CARTO-001 (P0, read-only cartography)
- P0 parallel code lanes: V1-TENANCY-010 (queue/worker isolation), V1-TENANCY-011 (object storage/signed URLs), V1-TENANCY-012 (graph/vector/AI context)
- Dependents: V1-GOLDEN-001 <- CARTO; V1-MIGRATE-001 <- CARTO; V1-CI-001 <- CARTO; V1-EVALS-001 <- CARTO; V1-GOLDEN-002 <- GOLDEN-001; V1-OPS-001 <- GOLDEN-001
- Single-writer surfaces respected: tenant-resolution-middleware (TENANCY-010), database-schema-and-migrations (MIGRATE-001), ci-required-check-definitions (CI-001).

## Stage 3 — Test-Driven Implementation (Red-Green)
- Workers clone upstream read-only, write hostile/negative tests FIRST per task negative_cases, then minimal implementation fixes; complexity-pruning pass after green. Workers never commit/push (publication_rule).

## Stage 4 — Cross-Model Multi-Tier Verification
- Auditor agent: AST-level review vs invariants (interface drift, anti-patterns).
- Security agent: adversarial review (tenant bypass, injection, secret leakage).
- Binary gate; failures redelegated.

## Stage 5 — Integration & Convergence
- Publisher (orchestrator) pushes verified files to fork branch swarm/production-finish, opens PR to Valynt/Fabric_4L main with digest (test matrix, diff summary, resolved issues) for human signoff. No merges by agents.
