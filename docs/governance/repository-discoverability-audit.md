---
title: "Repository Discoverability Completion Audit"
owner: "platform-engineering"
status: "active"
last_reviewed: "2026-06-05"
---

# Repository Discoverability Completion Audit

This audit is the source-of-truth checklist for proving that major Value Fabric
systems are discoverable, maintainable, and executable. A domain can support
goal completion only when its row is `covered`: it has a source-of-truth path,
governance or ownership reference, public validation command, evidence location,
and drift guard reachable from repo documentation.

## Coverage Matrix

| Domain | Discovery route | Source of truth | Governance / owner reference | Public validation | Evidence location | Drift guard | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Layer 1 ingestion | Layer runtime change | `services/layer1-ingestion/` | `docs/reference/layer-runtime-path-governance.md` | `make test-layer1` | `services/layer1-ingestion/tests/` | `make contract-tests` | covered |
| Layer 2 extraction | Layer runtime change | `services/layer2-extraction/` | `docs/reference/layer-runtime-path-governance.md` | `make test-layer2` | `services/layer2-extraction/tests/` | `make contract-tests` | covered |
| Layer 3 knowledge | Layer runtime change | `services/layer3-knowledge/` | `docs/reference/layer-runtime-path-governance.md` | `make test-layer3` | `services/layer3-knowledge/tests/` | `python scripts/ci/check_layer3_source_mirror.py` | covered |
| Layer 4 agents | Agent workflow, prompt, or tool | `services/layer4-agents/` | `contracts/agent-registry/README.md` | `make test-layer4` | `services/layer4-agents/tests/` | `make gate-agent` | covered |
| Layer 5 ground truth | Layer runtime change | `services/layer5-ground-truth/` | `docs/reference/layer5/source-of-truth.md` | `make test-layer5` | `services/layer5-ground-truth/tests/` | `make contract-tests` | covered |
| Layer 6 benchmarks | Layer runtime change | `services/layer6-benchmarks/` | `docs/reference/layer-runtime-path-governance.md` | `make test-layer6` | `services/layer6-benchmarks/tests/` | `make contract-tests` | covered |
| API gateway | API gateway or cross-layer API | `services/api/` | `docs/contract.md` | `make contract-tests` | `services/api/app/tests/` | `make gate-api-contracts` | covered |
| Frontend | Frontend workflow or page | `apps/web/` | `DESIGN.md` | `pnpm run verify:frontend` | `apps/web/docs/` | `make gate-frontend-readiness` | covered |
| Contracts and schemas | Contract/schema change | `contracts/` | `contracts/GOVERNANCE.md` | `make contract-tests` | `contracts/openapi/` | `make gate-api-contracts` | covered |
| Packs and ontology | Pack or ontology change | `packs/` | `docs/value-packs.md` | `make contract-tests` | `packs/` | `make verify` | covered |
| GitHub workflows | CI workflow or root command | `.github/workflows/` | `.github/workflows/workflow-registry.json` | `make check-workflow-registry` | `.github/workflows/WORKFLOW_REGISTRY.md` | `python scripts/ci/verify_workflow_registry.py` | covered |
| Test suites | Test suite or coverage inventory | `tests/` | `docs/testing/test-inventory.md` | `pnpm docs:check` | `docs/testing/` | `python -m pytest tests/docs/` | covered |
| Security and tenant isolation | Tenant isolation or auth | `tests/security/` | `docs/security/multi-tenancy.md` | `pnpm test:isolation` | `docs/validation/tenant-isolation-evidence-summary.md` | `make gate-security` | covered |
| Supply chain | Supply chain, dependency, or container change | `docs/supply-chain/` | `docs/security/secure-software-supply-chain.md` | `pnpm audit:ci` | `docs/supply-chain/SUPPLY_CHAIN_SECURITY.md` | `pnpm check:package-manager-policy` | covered |
| Migrations and database | Database model or migration | `services/` | `docs/reference/database-runtime-compatibility-matrix.md` | `make check-migration-heads` | `docs/validation/` | `make gate-database` | covered |
| Release readiness | Release/readiness gate | `.fabric/prod-gates.policy.yaml` | `docs/governance/weekly-acceptance-gates.md` | `make gate-release-policy` | `docs/validation/master_workflow_traceability_matrix.md` | `make production-readiness-gate` | covered |
| Observability and SLOs | Observability/SLO change | `monitoring/` | `docs/operations/layer6/observability.md` | `make gate-obs` | `tests/observability/` | `pnpm lint:logs` | covered |
| Operational runbooks | Operational runbook or incident workflow | `docs/operations/runbooks/` | `ops/incident/README.md` | `pnpm ops:runbooks:lint` | `docs/troubleshooting/runbooks/` | `pnpm ops:incident:check` | covered |
| Decisions and ADRs | Architecture or governance decision | `docs/decisions/` | `docs/explanations/adr/README.md` | `pnpm docs:check` | `docs/governance/` | `python -m pytest tests/docs/` | covered |
| Compliance and audit evidence | Compliance/audit evidence | `docs/governance/COMPLIANCE.md` | `docs/governance/audit-remediation-sprint-register.md` | `make gate-compliance-readiness` | `docs/validation/` | `pnpm test:audit` | covered |

## Completion Rule

The repository goal is not complete while this matrix has any `missing` row or
any `partial` row without a dated exception and owner. When adding a major
system, workflow, test suite, or operational decision surface, update this audit
in the same change as the discovery map, command docs, and drift tests.
