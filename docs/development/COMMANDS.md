---
title: "Command Inventory"
category: "reference"
audience: "contributors"
last-reviewed: "2026-06-04"
freshness: "current"
related: ["./BUILD_SYSTEM", "../../README", "../../CONTRIBUTING", "../../AGENTS"]
---

# Command Inventory

This is the canonical command map for local contributors, CI agents, and AI coding agents. Use [BUILD_SYSTEM.md](./BUILD_SYSTEM.md) for the build-system policy and this file for command lookup.

## Root pnpm Scripts

Every root `package.json` script is a stable public npm-script interface.

| Script | Command | Category |
|---|---|---|
| `generate:contracts` | `python scripts/ci/contract_compliance_gate.py --mode full --refresh-only` | Contract generation |
| `generate:api` | `pnpm --filter ./apps/web run generate:types` | Frontend API types |
| `check:contract-compliance` | `python scripts/ci/contract_compliance_gate.py --mode full` | Contract gate |
| `check:api-types` | `pnpm run generate:api && git diff --exit-code apps/web/src/api/generated` | Generated type drift |
| `sbom` | `python scripts/ci/supply_chain_gate.py sbom` | Supply chain SBOM generation |
| `audit:ci` | `python scripts/ci/supply_chain_gate.py audit` | Supply chain audit |
| `container:scan` | `python scripts/ci/supply_chain_gate.py container` | Container supply chain scan |
| `docs:check` | `python -m pytest tests/docs/` | Documentation validation |
| `ops:runbooks:lint` | `python scripts/ci/check_incident_runbooks.py --mode runbooks-lint` | Incident runbook validation |
| `ops:incident:check` | `python scripts/ci/check_incident_runbooks.py --mode incident-check` | Incident workflow validation |
| `test:observability` | `python -m pytest tests/observability/ -v --tb=short` | Observability tests |
| `test:reliability` | `python -m pytest tests/reliability/ -v --tb=short` | Reliability tests |
| `test:recovery` | `python -m pytest tests/recovery/ -v --tb=short` | Recovery tests |
| `test:release` | `python -m pytest tests/release/ -v --tb=short` | Release tests |
| `test:tenancy` | `python -m pytest tests/tenancy/ -v --tb=short` | Tenancy tests |
| `test:billing` | `python -m pytest tests/billing/ -v --tb=short` | Billing tests |
| `billing:webhooks:replay-test` | `python -m pytest tests/billing/test_webhook_idempotency.py -v --tb=short` | Billing webhook replay regression |
| `test:abuse` | `python -m pytest tests/abuse/ -v --tb=short` | Abuse prevention tests |
| `test:config` | `python -m pytest tests/config/ -v --tb=short` | Configuration tests |
| `config:validate` | `python -m pytest tests/config/ -v --tb=short` | Configuration validation |
| `flags:lint` | `python -m pytest tests/config/test_feature_flag_defaults.py -v --tb=short` | Feature flag policy |
| `test:audit` | `python -m pytest tests/audit/ -v --tb=short` | Audit tests |
| `test:data-lifecycle` | `python -m pytest tests/data_lifecycle/ -v --tb=short` | Data lifecycle tests |
| `test:production-readiness` | `python -m pytest tests/security/ tests/reliability/ tests/observability/ tests/recovery/ tests/release/ tests/tenancy/ tests/billing/ tests/abuse/ tests/config/ tests/audit/ -v --tb=short` | Production readiness pytest suite |
| `test:critical-behaviors` | `pnpm --filter ./apps/web run test:critical-behaviors && python scripts/ci/check_route_auth_dependencies.py && python -m pytest tests/security/test_tenant_boundary_fails_closed.py tests/security/test_billing_tenant_boundary.py tests/security/test_hostile_tenant_endpoint_family_contracts.py services/layer2-extraction/tests/test_sse_streaming_behavior.py services/layer2-extraction/tests/test_cross_tenant_hostile_behavioral.py services/layer3-knowledge/tests/test_cross_tenant_hostile_behavioral.py -q` | Critical behavior regression suite |
| `test:critical-behaviors:validate-skips` | `python scripts/ci/validate_critical_behavior_skips.py` | Critical behavior skip governance |
| `test:performance` | `python -m pytest tests/performance/` | Performance tests |
| `lint:logs` | `python scripts/ci/check_observability_coverage.py` | Observability coverage lint |
| `readiness:10` | `python scripts/ci/readiness_10_gate.py` | Readiness gate |
| `readiness:behavior-audit` | `python scripts/ci/behavior_readiness_audit.py --report artifacts/readiness/behavior-readiness-audit.json` | Behavior readiness audit |
| `test:security:hostile` | `python -m pytest tests/security/test_hostile_tenant_e2e_matrix.py tests/security/test_hostile_tenant_journey_contracts.py -v --tb=short` | Hostile tenant security contract suite |
| `test:isolation` | `python scripts/ci/run_root_aggregate_checks.py isolation` | Tenant isolation alias |
| `test:schema` | `python scripts/ci/run_root_aggregate_checks.py schema` | Schema/index alias |
| `test:queues` | `python -m pytest tests/integration/test_celery_queue_topology.py -m celery` | Queue topology tests |
| `loadtest:smoke` | `k6 run --summary-export artifacts/performance/loadtest-smoke-summary.json --env PERF_DURATION=30s tests/performance/k6/l2_l3_l4_critical_paths.js` | Performance smoke load test |
| `test:crawler` | `python scripts/ci/run_root_aggregate_checks.py crawler` | Layer 1 crawler alias |
| `test:router` | `python scripts/ci/run_root_aggregate_checks.py router` | Router contract alias |
| `test:agents` | `python -m pytest tests/agents services/layer4-agents/tests/test_workflows_real_execution.py services/layer4-agents/tests/unit/test_workflow_state_machine.py` | Agent regression tests |
| `db:extensions:check` | `python scripts/ci/run_root_aggregate_checks.py db-extensions-check` | Database extension policy |
| `db:migrate:status` | `python scripts/ci/run_root_aggregate_checks.py db-migrate-status` | Read-only migration status |
| `db:migrate:test` | `python scripts/ci/check_migration_drift.py --round-trip` | Migration round-trip drift test |
| `check:default-scope` | `node scripts/ci/check_default_scope.mjs` | Workspace policy |
| `preinstall` | `node scripts/enforce-package-manager.cjs` | Package-manager guard |
| `check:package-manager-policy` | `node scripts/ci/check_package_manager_policy.mjs` | Package-manager policy |
| `verify:frontend` | `pnpm --filter ./apps/web run verify:frontend` | Frontend verification |
| `verify` | `pnpm run check:default-scope && pnpm run verify:frontend` | Root pnpm verification alias |
| `check:test-skip-governance` | `python scripts/ci/check_test_skip_governance.py --register config/ci/test_skip_register.yaml` | Test governance |
| `check:type-escapes` | `make check-type-escape-ratchet` | Type-escape ratchet |
| `check:structural-fitness` | `make check-structural-fitness-ratchet` | Structural hotspot ratchet (Initiative E) |
| `dev:web` | `infisical run --env=dev --path=/shared --path=/apps/web -- pnpm --filter web dev` | Dev server |
| `dev:layer1` | `infisical run --env=dev --path=/shared --path=/infra --path=/layer1-ingestion -- uvicorn services.layer1-ingestion.src.api.main:app --reload` | Dev server |
| `dev:layer2` | `infisical run --env=dev --path=/shared --path=/infra --path=/layer2-extraction -- uvicorn services.layer2-extraction.src.api.main:app --reload` | Dev server |
| `dev:layer3` | `infisical run --env=dev --path=/shared --path=/infra --path=/layer3-knowledge -- uvicorn services.layer3-knowledge.src.api.main:app --reload` | Dev server |
| `dev:layer4` | `infisical run --env=dev --path=/shared --path=/infra --path=/layer4-agents -- uvicorn services.layer4-agents.src.api.main:app --reload` | Dev server |
| `dev:layer5` | `infisical run --env=dev --path=/shared --path=/infra --path=/layer5-ground-truth -- uvicorn services.layer5-ground-truth.src.api.main:app --reload` | Dev server |
| `dev:layer6` | `infisical run --env=dev --path=/shared --path=/infra --path=/layer6-benchmarks -- uvicorn services.layer6-benchmarks.src.api.main:app --reload` | Dev server |
| `env:dev` | `infisical export --env=dev --path=/shared --path=/infra --path=/layer1-ingestion --path=/layer2-extraction --path=/layer2-5-signal-refinery --path=/layer3-knowledge --path=/layer4-agents --path=/layer5-ground-truth --path=/layer6-benchmarks --path=/apps/web --format=dotenv --output-file=.env.generated` | Environment export |
| `compose:dev` | `pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up` | Dev stack |
| `contract:breaking` | `python scripts/ci/openapi_breaking_change_gate.py` | Contract compatibility |
| `evidence:bundle` | `python scripts/ci/generate_evidence_bundle.py` | Evidence bundle generation |
| `evidence:build` | `node --experimental-strip-types scripts/collect_evidence.ts build` | Evidence collection build |
| `evidence:validate` | `node --experimental-strip-types scripts/collect_evidence.ts validate` | Evidence collection validation |
| `release:dry-run` | `python scripts/ci/generate_release_safety_artifact.py --environment release-candidate --profile release-candidate` | Release safety artifact |
| `release:rollback:verify` | `python scripts/ci/verify_release_rollback.py` | Release rollback verification |
| `production:scorecard` | `python scripts/ci/check_production_readiness_scorecard.py --scorecard-only` | Production readiness scorecard |
| `production:check` | `python scripts/ci/check_production_readiness_scorecard.py && python scripts/ci/validate_production_readiness_plan.py` | Production readiness validation |
| `ci:workflow-registry` | `python scripts/ci/verify_workflow_registry.py` | Workflow registry validation |
| `ci:workflow-references` | `python scripts/ci/check_workflow_targets_and_artifacts.py` | Workflow command and artifact reference validation |
| `ops:backup:verify` | `python -m pytest tests/recovery/test_backup_exists.py tests/recovery/test_restore_smoke.py` | Backup recovery validation |
| `ops:restore:dry-run` | `python scripts/ops/restore_dry_run.py --output-dir artifacts/recovery` | Restore dry-run evidence |
| `ops:walg:gate` | `python scripts/ci/check_walg_enablement_gate.py` | WAL-G physical backup enablement evidence gate |
| `ops:quota:check` | `python scripts/ci/check_quota_policy.py` | Quota policy validation |
| `gate-engineering:validate` | `python scripts/ci/gate_engineering_validator.py validate` | Validate gate-engineering registry |
| `gate-engineering:test` | `python -m pytest tests/ci/test_gate_engineering.py -v --tb=short` | Run gate-engineering registry tests |

## Public Makefile Targets

Public Makefile targets are targets with `##` help text and are exposed by `make help`.

### Setup And Workspace

| Target | Purpose |
|---|---|
| `help` | Show public Makefile targets. |
| `bootstrap` | One-command first-time setup path. |
| `setup` | Install all service dev dependencies into the pytest pipx venv. |
| `setup-layer2-5` | Install Layer 2.5 dev dependencies. |
| `setup-hooks` | Configure repository git hooks. |
| `preflight` | Check Docker, environment, and ports before starting services. |
| `harness-task` | Assemble Value Fabric harness context. |
| `harness-guard` | Run harness pre-edit boundary and contract checks. |
| `harness-check` | Run full harness preflight. |

### Verification And Governance

| Target | Purpose |
|---|---|
| `verify` | Run all checks before PR. |
| `verify-structure` | Run structural preflight and Python contract lint checks. |
| `verify-strict` | Run `verify` plus contract drift detection. |
| `check-conflict-markers` | Fail on unresolved merge conflict markers. |
| `check-no-nul-bytes` | Fail on tracked NUL bytes. |
| `check-readiness-consistency` | Check readiness percentage and archive consistency. |
| `check-workflow-matrix` | Validate workflow traceability matrices. |
| `check-workflow-registry` | Validate GitHub Actions workflow ownership and artifact registry. |
| `check-workflow-references` | Validate GitHub Actions workflow command and artifact references. |
| `check-keycloak-realm-seed-security` | Fail when Keycloak realm seeds embed secrets or default credentials. |
| `check-manifest-secret-hygiene` | Enforce secret-only references and denylisted sensitive patterns in manifests. |
| `check-path-env-hygiene` | Fail on suspicious path artifacts and unapproved tracked env files. |
| `check-pytest-skip-governance` | Enforce pytest skip governance. |
| `check-type-escape-ratchet` | Fail on net-new unapproved Python or TypeScript type escapes. |
| `check-structural-fitness-ratchet` | Fail on net-new oversized modules, high-complexity functions, or import cycles (Initiative E). |
| `check-hermetic-build-inputs` | Enforce digest-pinned Docker base images and approved CI external domains. |
| `check-production-k8s-mutable-tags` | Fail if production-facing K8s manifests use `:latest` or `:main` image tags. |
| `check-k8s-image-digests` | Fail if production K8s overlays use mutable image tags. |
| `check-temporal-skips` | Guard against net-new unregistered hard-coded temporal test skips. |
| `check-test-skip-register-uniqueness` | Enforce unique skip register keys. |
| `check-reports-evidence-policy` | Enforce reports artifact policy. |
| `check-legacy-debt` | Enforce legacy debt baseline. |
| `check-behavior-contract` | Enforce behavior contract registry coverage. |
| `check-behavior-readiness-audit` | Enforce executable behavior readiness audit. |
| `check-ui-duplicates` | Block duplicate UI component filenames. |
| `check-layer4-boundaries` | Check Layer 4 bounded-context dependencies. |
| `check-layer4-collection` | Check that all Layer 4 tests can be collected without import errors. |
| `check-layer4-canonical-paths` | Enforce Layer 4 canonical path layout via AST checks. |
| `check-layer3-legacy-tenant-dependency-imports` | Block legacy Layer 3 tenant dependency imports. |
| `check-layer3-tenant-dependency-imports` | Compatibility alias for the legacy Layer 3 tenant import gate. |
| `check-compatibility-shims` | Run the unified registry-driven compatibility shim gate. |
| `check-raw-http-exception-usage` | Enforce raw `HTTPException` usage boundaries. |
| `check-value-fabric-public-imports` | Enforce public import policy. |
| `docs-harness` | Validate harness documentation artifacts. |

### Lint And Typecheck

| Target | Purpose |
|---|---|
| `lint` | Lint all Python layers. |
| `lint-layer1` | Lint Layer 1. |
| `lint-layer2` | Lint Layer 2. |
| `lint-layer2-5` | Lint Layer 2.5. |
| `lint-layer3` | Lint Layer 3. |
| `lint-layer4` | Lint Layer 4. |
| `lint-layer5` | Lint Layer 5. |
| `lint-layer6` | Lint Layer 6. |
| `typecheck` | Type-check all Python layers. |
| `typecheck-layer1` | Type-check Layer 1 typed core + enforce mypy baseline ratchet. |
| `mypy-changed-layer1` | Type-check changed Layer 1 source files (PR gate). |
| `typecheck-layer2` | Type-check Layer 2. |
| `typecheck-layer2-5` | Type-check Layer 2.5. |
| `typecheck-layer3` | Type-check Layer 3. |
| `typecheck-layer4` | Type-check Layer 4. |
| `typecheck-layer4-strict` | Type-check the unified Layer 4 namespace with strict settings. |
| `typecheck-layer5` | Type-check Layer 5. |
| `typecheck-layer6` | Type-check Layer 6. |
| `gate-lint` | Release-readiness lint gate for all layers. |
| `lint-release` | Compatibility alias for `gate-lint`. |

### Tests

| Target | Purpose |
|---|---|
| `test` | Run all backend unit tests. |
| `test-unit` | Run unit tests only. |
| `test-integration` | Run integration tests. |
| `test-fast` | Run fast tests excluding slow and e2e. |
| `test-layer1` | Run Layer 1 unit tests (no external services). |
| `test-layer1-integration` | Run Layer 1 integration tests (requires PostgreSQL). |
| `test-layer1-crawler` | Run focused Layer 1 crawler tests. |
| `test-layer1-router-cache` | Run focused Layer 1 router/cache tests. |
| `test-layer1-benchmarks` | Run Layer 1 benchmark and performance tests. |
| `test-layer1-router-benchmarks` | Run quarantined Layer 1 router benchmarks with explicit opt-in. |
| `test-layer1-security-postgres` | Run Layer 1 PostgreSQL-backed security tests. |
| `test-layer2` | Run Layer 2 tests. |
| `test-layer2-5` | Run Layer 2.5 tests. |
| `test-layer3` | Run Layer 3 tests. |
| `test-layer3-live` | Run Layer 3 live Neo4j/vector integration tests. |
| `test-layer4` | Run Layer 4 tests. |
| `test-layer4-live` | Run Layer 4 live Docker/PostgreSQL/integration tests. |
| `test-layer5` | Run Layer 5 tests. |
| `test-layer6` | Run Layer 6 tests. |
| `test-shared` | Run the shared-package suite (`packages/shared/tests`) with identity/governance/rate-limiting coverage. Changes here fan out to every layer plus the gateway. |
| `test-frontend` | Run frontend unit tests. |
| `test-e2e` | Run Playwright E2E tests. |
| `test-e2e-contracts` | Run isolated Playwright contract tests. |
| `test-e2e-behaviors` | Run strict behavior-first allowed/denied path tests. |
| `test-e2e-journeys` | Run chained Playwright journeys. |
| `test-e2e-docker` | Run E2E tests with Docker containers. |
| `seed-e2e` | Seed deterministic E2E fixture data. |
| `reset-e2e` | Remove E2E tenant data. |
| `test-e2e-full` | Seed, run E2E contracts and journeys, then reset. |
| `test-backend-contracts` | Run backend contract/integration assertions. |
| `test-backend-integrated-validation` | Run backend integrated validation. |
| `test-backend-integrated-release-smoke` | Boot full release stack and smoke test. |
| `test-backup-drills` | Run backup/DR drill tests. |
| `pact-tests` | Run Pact consumer tests and provider verification. |

### Security

| Target | Purpose |
|---|---|
| `security-smoke` | Run fast security smoke tests. |
| `security-test-gating` | Compatibility alias for `security-smoke`. |
| `security-test` | Run full security suite. |
| `security-test-isolation` | Run tenant isolation tests only. |
| `security-test-rbac` | Run RBAC tests only. |
| `security-test-owasp` | Run OWASP Top 10 tests. |
| `security-test-injection` | Run injection prevention tests. |
| `security-coverage` | Run security tests with coverage. |
| `gate-mandatory-security-regression` | Mandatory launch security regression gate. |
| `gate-tenant-isolation` | Dedicated tenant isolation readiness gate. |
| `gate-security` | Canonical security readiness gate. |
| `security-readiness-gate` | Compatibility alias for `gate-security`. |
| `gate-security-broad` | Advisory broad security coverage gate. |
| `gate-auth-readiness` | Route auth and auth-bypass readiness gate. |
| `gate-secrets-readiness` | Secret hygiene readiness gate. |

### Contracts And Schemas

| Target | Purpose |
|---|---|
| `contract-tests` | Run cross-layer contract and architecture tests. |
| `contracts` | Export OpenAPI specs. |
| `validate-openapi-contracts` | Validate tracked OpenAPI specs. |
| `contract-drift` | Export and validate OpenAPI drift. |
| `contract-freshness` | Regenerate OpenAPI and frontend DTOs and fail on drift. |
| `contract-freshness-fast` | Fast contract-freshness lane: validates committed specs and shapes, no live services. |
| `contract-lint` | Run ESLint contract rules. |
| `platform-contract-lint` | Run platform contract lint. |
| `check-tool-contracts` | Validate tool error structure. |
| `check-deprecated-tracer-imports` | Block deprecated tracer imports. |
| `check-deprecations` | Check overdue deprecations. |
| `check-compatibility-shims` | Run registry inventory compatibility checks across shim/deprecated guardrails. |
| `gate-api-contracts` | API/platform contract readiness gate. |

### Migrations And Database

| Target | Purpose |
|---|---|
| `migrate` | Run all Alembic-managed migrations. |
| `migrate-layer1` | Run Layer 1 migrations. |
| `migrate-layer2` | Run Layer 2 migrations. |
| `migrate-layer2-5` | Run Layer 2.5 migrations. |
| `migrate-layer4` | Run Layer 4 migrations. |
| `migrate-layer5` | Run Layer 5 migrations. |
| `migrate-api` | Run API gateway migrations. |
| `check-migration-entrypoints` | Validate migration entrypoints. |
| `check-migration-heads` | Validate exactly one Alembic head per service. |
| `check-migration-rollback-policy` | Enforce migration rollback policy. |
| `check-migration-postgres-roundtrip` | Run live PostgreSQL migration round-trip. |
| `check-migration-runtime-consistency` | Validate migration/runtime URL consistency. |
| `db-migrate-status` | Emit read-only migration status artifacts. |
| `db-migrate-check` | Fail on read-only migration drift. |
| `check-migration-status-artifacts` | Ensure migration status artifacts exist. |
| `check-database-governance-docs` | Validate database governance docs. |
| `gate-database` | Canonical local database readiness gate. |
| `db-production-readiness-gate` | PostgreSQL database production-readiness gate. |
| `gate-database-live` | Live database readiness checks. |
| `gate-migration-readiness` | Migration readiness gate. |
| `gate-database-readiness` | Database production readiness split checks. |
| `gate-backup-restore-readiness` | PostgreSQL backup/restore drill. |

### Environment And Runtime

| Target | Purpose |
|---|---|
| `check-env` | Validate backend and frontend environment variables. |
| `check-env-backend` | Validate backend environment variables. |
| `check-env-frontend` | Validate frontend environment variables. |
| `validate-env-contract` | Validate environment contract and schema. |
| `up` | Start all services with Docker Compose. |
| `down` | Stop all services. |
| `logs` | Tail service logs. |
| `build` | Build frontend production bundle. |
| `docker-build` | Build deployable Docker images locally. |
| `docker-build-multi` | Build deployable images for `linux/amd64` and `linux/arm64` with `docker buildx`. |
| `sdk` | Generate the Python SDK. |
| `evals` | Run agent golden-trace evaluations. |
| `evals-full` | Run full eval suite. |
| `perf-test` | Run critical-path k6 load suite. |
| `perf-test-journeys` | Run journey-aligned k6 tests. |
| `perf-eval` | Evaluate k6 results against SLO thresholds. |

### Release And Readiness Gates

| Target | Purpose |
|---|---|
| `gate-policy` | Validate release policy schema/profile/artifact dirs. |
| `gates-validate-policy` | Compatibility alias for `gate-policy`. |
| `gate-state` | Frontend/backend state alignment gate. |
| `gate-arch` | Architecture conformance gate. |
| `architecture-readiness-gate` | Compatibility alias for `gate-arch`. |
| `gate-config` | Startup configuration gate. |
| `gate-local` | Minimal local security gate; not production readiness. |
| `gate-local-production-subset` | Local-only production-readiness subset. |
| `gate-all` | Compatibility alias for `gate-local-production-subset`. |
| `production-readiness-gate` | Canonical production-readiness gate required by CI. Writes and validates per-suite JUnit/summary artifacts plus `artifacts/production-readiness/manifest.json`. |
| `gate-production` | Compatibility alias for `production-readiness-gate`. |
| `gate-production-core` | Policy-driven production-core gate profile. |
| `gate-behavior-readiness` | Executable, skip-controlled behavior readiness audit. |
| `tier0-production-safety-gate` | Tier 0 safety gate profile. |
| `tier1-beta-readiness-gate` | Tier 1 beta readiness profile. |
| `tier2-enterprise-readiness-gate` | Tier 2 enterprise readiness profile. |
| `release-gate` | Run the policy-driven production readiness sequence. |
| `release-evidence-packet` | Generate release evidence packet. |
| `promote-staging` | Verify local gates and evidence, then trigger staging promotion. |
| `collect-95-plus-evidence-focused` | Compatibility alias for `release-evidence-packet`. |
| `collect-95-plus-evidence` | Compatibility alias for `release-evidence-packet`. |
| `gate-deployment-readiness` | Deployment image/profile readiness. |
| `gate-launch-blockers` | Launch governance and blocker gate. |
| `gate-frontend-readiness` | Frontend beta readiness gate. |
| `gate-reliability-readiness` | Reliability gate using chaos and smoke. |
| `gate-rollback-readiness` | Rollback readiness gate. |
| `gate-performance-readiness` | Performance readiness gate. |
| `gate-data-governance-readiness` | Data governance readiness gate. |
| `gate-compliance-readiness` | Compliance evidence readiness gate. |
| `gate-incident-response-readiness` | Incident response readiness gate. |
| `gate-chaos` | Dependency chaos and failure-injection gate. |
| `gate-smoke` | Cross-domain smoke gate. |
| `gate-agent` | Agent provenance and regression gate. |
| `gate-obs` | Observability, metrics, and SLO gate. |
| `gate-release-policy` | Release policy compliance gate. |
| `gate-sign-manifest` | Sign release artifact manifest. |
| `gates-sign-manifest` | Compatibility alias for `gate-sign-manifest`. |
| `gate-summary` | Render release summary. |
| `gates-render-summary` | Compatibility alias for `gate-summary`. |

### Cleanup

| Target | Purpose |
|---|---|
| `clean` | Remove build artifacts and caches. |
| `clean-root-debris` | Remove root-level temp artifacts and generated debris. |

## Python CI Runner

The supported direct runner is:

```bash
python scripts/ci/run_root_aggregate_checks.py --list
python scripts/ci/run_root_aggregate_checks.py --json
python scripts/ci/run_root_aggregate_checks.py <gate>
```

Supported gates are `typecheck`, `lint`, `test`, `security`, `schema`, `isolation`, `crawler`, `router`, `db-migrate-status`, and `all`. Use these commands only for CI parity debugging or when a workflow maps to the Python runner directly.

## CI To Local Mapping

| CI workflow/job | Local command | Notes |
|---|---|---|
| `.github/workflows/pr-checks.yml` / `make verify` | `make verify` | Canonical broad local PR gate after workflow consolidation. |
| `.github/workflows/pr-checks.yml` / schema index coverage | `pnpm test:schema` | Root alias for `run_root_aggregate_checks.py schema`. |
| `.github/workflows/pr-checks.yml` / tenant isolation gate | `pnpm test:isolation` | Root alias for tenant isolation aggregate runner. |
| `.github/workflows/contract-compliance.yml` / contract compliance | `pnpm run check:contract-compliance` | Full contract compliance gate. |
| Generated API freshness and frontend type drift | `pnpm run generate:api` then `pnpm run check:api-types` | Detects generated client drift. |
| Frontend PR checks | `pnpm run verify:frontend` or `pnpm --dir apps/web run <script>` | Use package-level scripts for focused frontend checks. |
| Migration status/drift checks | `pnpm db:migrate:status`, `make db-migrate-check`, or `make gate-database` | Read-only migration status and drift checks. |
| Database readiness | `make gate-database` | Local static/read-only gate; live checks require explicit DB environment. |
| Production readiness gate | `make production-readiness-gate` | Canonical CI-required production-readiness gate. `make gate-production` is a compatibility alias. Evidence includes validated per-suite JUnit/summary files and `artifacts/production-readiness/manifest.json`. |
| Release evidence | `make release-evidence-packet` | Generates canonical release evidence. |
| Workflow registry and command/artifact references | `make check-workflow-registry`, `make check-workflow-references`, `pnpm ci:workflow-registry`, or `pnpm ci:workflow-references` | Public command-map interfaces for workflow ownership metadata and workflow command/artifact checks. |
| Incident response docs | `pnpm ops:runbooks:lint` and `pnpm ops:incident:check` | Validates `ops/incident/` runbooks, severity, escalation, communications, postmortem, and workflow links. |
| Docs command-map validation | `pnpm docs:check` | Runs `python -m pytest tests/docs/`. |

## Related Documentation

- [Canonical Build System](./BUILD_SYSTEM.md) - Command hierarchy and public interface policy.
- [Development Discovery Map](./DISCOVERY_MAP.md) - Route issue types to canonical files, drift checks, validation commands, and evidence.
- [Contributing](../../CONTRIBUTING.md) - Contributor setup and PR process.
- [Agent Reference](../../AGENTS.md) - AI agent command and governance reference.
