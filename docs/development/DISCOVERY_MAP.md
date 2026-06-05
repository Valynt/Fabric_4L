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
| Backend API behavior | `services/layer*/`, `services/api/`, `contracts/openapi/`, `contracts/jsonschema/`, `docs/contract.md` | Route handler, OpenAPI, JSON Schema, generated frontend types, service callers | `pytest path/to/relevant/tests`, `make contract-tests`, `pnpm run check:api-types` when API types are affected | `make verify` |
| Frontend workflow or page | `apps/web/`, root `DESIGN.md`, `apps/web/README.md`, `apps/web/docs/` | UI route, TanStack Query hook, generated API type, mock handler, design-system component usage | `pnpm --dir apps/web run test`, `pnpm --dir apps/web run typecheck`, targeted Playwright where behavior changes | `pnpm run verify:frontend`, `make verify` |
| Agent workflow, prompt, or tool | `services/layer4-agents/`, `contracts/agent-registry/`, `services/layer4-agents/prompts/`, `services/layer4-agents/skills/` | Output schema, checkpoint/resume state, provider adapter boundary, frontend consumer, Layer 5/6 dependency | `pnpm test:agents`, targeted Layer 4 pytest, schema/contract tests for output changes | `make verify`, `make evals` when prompt behavior changes |
| Tenant isolation or auth | `packages/shared/src/value_fabric/shared/`, service auth middleware, repository methods, `docs/security/`, `tests/security/`, `tests/tenancy/` | Authenticated tenant context, repository filters, write ownership, hostile cross-tenant tests | `pnpm test:isolation`, targeted `pytest tests/security/ tests/tenancy/` subset | `make gate-security`, `make verify` |
| Supply chain, dependency, or container change | `package.json`, `pnpm-lock.yaml`, service dependency manifests, `.github/dependabot.yml`, `docs/supply-chain/SUPPLY_CHAIN_SECURITY.md`, `docs/reference/contributor-dependency-workflows.md` | Package-manager policy, lockfile churn, SBOM output, dependency audit, container image scan, license policy | `pnpm check:package-manager-policy`, `pnpm audit:ci`, `pnpm sbom`, `pnpm container:scan` when containers are affected | `.github/workflows/supply-chain.yml`, `make verify` |
| Database model or migration | Service model path, service Alembic directory, `docs/reference/layer-runtime-path-governance.md` | Model, migration, downgrade policy, tenant fields, deployed head count | `make check-migration-heads`, service migration test or targeted pytest | `make gate-database`, `make verify` |
| CI workflow or root command | `.github/workflows/`, `Makefile`, `package.json`, `scripts/ci/`, [COMMANDS.md](./COMMANDS.md) | Workflow job name, local command mapping, artifact paths, public target/script docs | `pnpm docs:check`, targeted script unit test in `scripts/ci/tests/` | `make verify` |
| Operational runbook or incident workflow | `docs/operations/`, `docs/troubleshooting/`, `ops/incident/`, `scripts/ci/check_incident_runbooks.py` | Alert/runbook link, escalation path, evidence artifact, postmortem path | `pnpm ops:runbooks:lint`, `pnpm ops:incident:check` | `make verify` |
| Architecture or governance decision | `docs/decisions/`, `docs/explanations/adr/`, `docs/governance.md`, `docs/governance/` | Decision status, affected contracts, tenant isolation, compatibility debt, implementation evidence | `pnpm docs:check` plus any affected contract/governance gate | `make verify` |
| Pack or ontology change | `packs/`, `docs/value-packs.md`, `contracts/`, affected layer tests | Pack-local configuration vs core hardcoding, ontology compatibility, formula/benchmark lineage | Pack tests plus affected layer contract tests | `make verify` |

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
| Test inventory and coverage posture | `docs/testing/`, `reports/testing/`, `reports/autonomous-test-assurance/` |
| Contract and API alignment | `docs/contracts/`, `contracts/`, `reports/api-contract-stability-audit.md` |
| Production readiness and release gates | `docs/validation/`, `reports/production-readiness-gap-analysis.md`, `reports/production-launch-readiness-audit.md` |
| Security and tenant isolation | `docs/security/`, `docs/validation/tenant-isolation-evidence-summary.md`, `reports/security/`, `tests/security/` |
| Supply chain and dependency posture | `docs/supply-chain/`, `docs/security/secure-software-supply-chain.md`, `license-reports/`, `artifacts/supply-chain/` |
| Operational runbooks and incident response | `docs/operations/`, `docs/troubleshooting/`, `ops/incident/` |
| Architecture decisions | `docs/decisions/`, `docs/explanations/adr/`, `docs/governance.md` |

If a needed source of truth is missing, add the smallest durable reference in the canonical area and wire it into this map or [COMMANDS.md](./COMMANDS.md). Do not create isolated status reports that cannot be reached from root docs, command docs, or the relevant domain README.
