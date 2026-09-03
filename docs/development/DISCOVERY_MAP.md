---
title: "Development Discovery Map"
owner: "platform-engineering"
status: "active"
last_reviewed: "2026-06-04"
---

# Development Discovery Map

Use this map before changing code, tests, workflows, infrastructure, or operational docs. It routes common work from issue intake to canonical implementation paths, contract checks, validation commands, and evidence locations.

The command hierarchy remains defined by [BUILD_SYSTEM.md](./BUILD_SYSTEM.md). The complete public command inventory remains defined by [COMMANDS.md](./COMMANDS.md).

## Start Here

| Work type | Canonical source of truth | Drift checks | Minimum focused validation | Broader gate |
| --- | --- | --- | --- | --- |
| Layer runtime change | `docs/reference/layer-runtime-path-governance.md`, maintained service under `services/layer*/`, layer contracts, layer tests | Runtime source path, compatibility shim policy, OpenAPI/schema impact, tenant context propagation | `make test-layer1`, `make test-layer2`, `make test-layer3`, `make test-layer4`, `make test-layer5`, or `make test-layer6` for the affected layer | `make contract-tests`, `make verify` |
| Backend API behavior | `services/layer*/`, `services/api/`, `contracts/openapi/`, `contracts/jsonschema/`, `docs/contract.md` | Route handler, OpenAPI, JSON Schema, generated frontend types, service callers | `make contract-tests`, `pnpm run check:api-types` when API types are affected | `make verify` |
| API gateway or cross-layer API | `services/api/`, `docs/contract.md`, `contracts/openapi/fabric-4l-api.json`, `contracts/route-contracts.json` | Gateway auth/tenant context, route contract, OpenAPI shape, downstream service caller expectations | `make contract-tests` plus targeted API gateway pytest when needed | `make gate-api-contracts`, `make verify` |
| Contract/schema change | `contracts/`, `contracts/GOVERNANCE.md`, `contracts/openapi/`, `contracts/jsonschema/`, generated frontend API types | OpenAPI drift, JSON Schema compatibility, generated TypeScript types, breaking-change policy | `make contract-tests`, `pnpm run check:api-types`, `pnpm contract:breaking` | `make gate-api-contracts`, `make verify` |
| Frontend workflow or page | `apps/web/`, root `DESIGN.md`, `apps/web/README.md`, `apps/web/docs/` | UI route, TanStack Query hook, generated API type, mock handler, design-system component usage | `pnpm run verify:frontend` plus targeted frontend tests where behavior changes | `make gate-frontend-readiness`, `make verify` |
| Frontend design-system change | root `DESIGN.md`, `apps/web/`, `apps/web/docs/frontend-workflow-coverage-matrix.md`, shared UI components | Design governance, shell/tab/right-rail patterns, generated API client usage, accessibility states | `pnpm run verify:frontend` plus targeted frontend component tests | `make gate-frontend-readiness`, `make verify` |
| Agent workflow, prompt, or tool | `services/layer4-agents/`, `contracts/agent-registry/`, `services/layer4-agents/prompts/`, `services/layer4-agents/skills/` | Output schema, checkpoint/resume state, provider adapter boundary, frontend consumer, Layer 5/6 dependency | `pnpm test:agents` plus targeted Layer 4 pytest when needed | `make gate-agent`, `make evals` when prompt behavior changes |
| Tenant isolation or auth | `packages/shared/src/value_fabric/shared/`, service auth middleware, repository methods, `docs/security/`, `tests/security/`, `tests/tenancy/` | Authenticated tenant context, repository filters, write ownership, hostile cross-tenant tests | `pnpm test:isolation`, `pnpm test:security:hostile` | `make gate-security`, `make verify` |
| Supply chain, dependency, or container change | `package.json`, `pnpm-lock.yaml`, service dependency manifests, `.github/dependabot.yml`, `docs/supply-chain/SUPPLY_CHAIN_SECURITY.md`, `docs/reference/contributor-dependency-workflows.md` | Package-manager policy, lockfile churn, SBOM output, dependency audit, container image scan, license policy | `pnpm check:package-manager-policy`, `pnpm audit:ci`, `pnpm sbom`, `pnpm container:scan` when containers are affected | `make verify` |
| Database model or migration | Service model path, service Alembic directory, `docs/reference/layer-runtime-path-governance.md` | Model, migration, downgrade policy, tenant fields, deployed head count | `make check-migration-heads`, `make check-migration-rollback-policy` | `make gate-database`, `make verify` |
| CI workflow or root command | `.github/workflows/`, `Makefile`, `package.json`, `scripts/ci/`, [COMMANDS.md](./COMMANDS.md), [CI_GATES.md](./CI_GATES.md) | Workflow classification, owner, job name, local command mapping, dependencies, artifact paths, public target/script docs | `pnpm docs:check`, `make check-workflow-references`, `pnpm ci:workflow-references`, `make check-workflow-registry` | `make verify` |
| Test suite or coverage inventory | `tests/`, `docs/testing/test-inventory.md`, `docs/testing/TEST_CATALOG.md`, `pytest.ini` | Suite entrypoint, markers, source path ownership, skip governance, public command mapping | `pnpm docs:check`, `make test` | `make verify` |
| Observability/SLO change | `monitoring/`, service observability modules, `docs/operations/layer6/observability.md`, `tests/observability/` | Metrics contract, log coverage, alert/runbook linkage, SLO evidence | `pnpm lint:logs`, `pnpm test:observability` | `make gate-obs`, `make verify` |
| Release/readiness gate | `Makefile`, `.github/workflows/pr-checks.yml`, `.fabric/prod-gates.policy.yaml`, `docs/governance/weekly-acceptance-gates.md`, `docs/validation/` | Canonical production-readiness target, rollback criteria, evidence artifact, release policy profile | `make gate-release-policy`, `pnpm test:release` | `make production-readiness-gate`, `make verify` |
| Compliance/audit evidence | `docs/governance/COMPLIANCE.md`, `docs/governance/audit-remediation-sprint-register.md`, compliance workflows, `tests/audit/` | Control owner, evidence retention, audit workflow artifact, export control policy | `pnpm test:audit`, `make gate-compliance-readiness` | `make verify` |
| Operational runbook or incident workflow | `docs/operations/`, `docs/troubleshooting/`, `ops/incident/`, `scripts/ci/check_incident_runbooks.py` | Alert/runbook link, escalation path, evidence artifact, postmortem path | `pnpm ops:runbooks:lint`, `pnpm ops:incident:check` | `make verify` |
| Architecture or governance decision | `docs/explanations/adr/`, `docs/decisions/`, `docs/decisions/adr-registry.yaml`, `docs/governance.md`, `docs/governance/` | Decision status, registry related-code links, affected contracts, tenant isolation, compatibility debt, implementation evidence | `make check-adr` | `make verify` |
| Pack or ontology change | `packs/`, `docs/value-packs.md`, `contracts/`, affected layer tests | Pack-local configuration vs core hardcoding, ontology compatibility, formula/benchmark lineage | Pack tests plus affected layer contract tests | `make verify` |

## Audited Domain Coverage

The completion audit in [repository-discoverability-audit.md](../governance/repository-discoverability-audit.md) is the governing checklist. Each audited domain must route to one of the work types above.

| Audited domain | Discovery route |
| --- | --- |
| Layer 1 ingestion | Layer runtime change |
| Layer 2 extraction | Layer runtime change |
| Layer 3 knowledge | Layer runtime change |
| Layer 4 agents | Agent workflow, prompt, or tool |
| Layer 5 ground truth | Layer runtime change |
| Layer 6 benchmarks | Layer runtime change |
| API gateway | API gateway or cross-layer API |
| Frontend | Frontend workflow or page |
| Contracts and schemas | Contract/schema change |
| Packs and ontology | Pack or ontology change |
| GitHub workflows | CI workflow or root command |
| Test suites | Test suite or coverage inventory |
| Security and tenant isolation | Tenant isolation or auth |
| Supply chain | Supply chain, dependency, or container change |
| Migrations and database | Database model or migration |
| Release readiness | Release/readiness gate |
| Observability and SLOs | Observability/SLO change |
| Operational runbooks | Operational runbook or incident workflow |
| Decisions and ADRs | Architecture or governance decision |
| Compliance and audit evidence | Compliance/audit evidence |

## Issue To Validation Loop

1. Identify the affected layer, package, workflow, or operational domain.
2. Open the source-of-truth paths in the table above before editing.
3. Check contracts and drift points before deciding whether the change is code, contract, test, or documentation work.
4. Make the smallest change that preserves tenant isolation, source-of-truth paths, and public command interfaces.
5. Update every affected consumer: contracts, generated types, tests, docs, workflows, runbooks, or release evidence.
6. Run the narrowest validation that proves the changed behavior, then broaden to the relevant gate when feasible.
7. Report only validations that actually ran, and include residual risks for anything not covered.

## Evidence Locations

| Evidence need | Preferred location |
| --- | --- |
| Test inventory and coverage posture | `docs/testing/`, `tests/`, `artifacts/` |
| Contract and API alignment | `docs/contracts/`, `contracts/`, `contracts/openapi/`, `contracts/jsonschema/` |
| Production readiness and release gates | `docs/validation/`, `docs/launch/`, `.fabric/prod-gates.policy.yaml`, `artifacts/release/` |
| Repository discoverability completion | `docs/governance/repository-discoverability-audit.md`, `docs/development/DISCOVERY_MAP.md`, `docs/development/COMMANDS.md` |
| Security and tenant isolation | `docs/security/`, `docs/validation/tenant-isolation-evidence-summary.md`, `tests/security/` |
| Supply chain and dependency posture | `docs/supply-chain/`, `docs/security/secure-software-supply-chain.md`, `license-reports/`, `artifacts/supply-chain/` |
| Operational runbooks and incident response | `docs/operations/`, `docs/troubleshooting/`, `ops/incident/` |
| Architecture decisions | `docs/decisions/`, `docs/explanations/adr/`, `docs/governance.md` |

If a needed source of truth is missing, add the smallest durable reference in the canonical area and wire it into this map or [COMMANDS.md](./COMMANDS.md). Do not create isolated status reports that cannot be reached from root docs, command docs, or the relevant domain README.
