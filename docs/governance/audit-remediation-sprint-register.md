# Audit Remediation Sprint Register

Generated: 2026-06-04

This register tracks the 57 audit remediation items from the June 2026 patch
bundle review. It is the canonical closure record for this remediation wave.
Patch presence is not completion evidence.

## Closure Rule

An item may move to `verified closed` only when all of the following are true:

- The canonical repository implementation satisfies the acceptance criteria.
- A targeted validation command was run and recorded.
- Security, tenant isolation, contract, and governance assertions were not weakened.
- Any public API or schema behavior change has matching contract, type, test, and documentation updates.

## Status Values

| Status | Meaning |
|---|---|
| `covered` | Current repo or patch bundle appears to contain the implementation; targeted verification still required before closure. |
| `partial` | Some implementation exists, but acceptance criteria are incomplete. |
| `not covered` | No convincing implementation was found in the patch bundle or current repo evidence. |
| `requires implementation` | Work must be implemented directly in the current repo. |
| `verified closed` | Validation has passed and evidence is recorded. |

## Sprint Register

| ID | Item | Owner team | Patch coverage | Current status | Required validation |
|---|---|---|---|---|---|
| S0-1 | Triage all 67 findings and assign owners | Platform Governance | not covered | requires implementation | Owner matrix populated and linked to tracking board |
| S0-2 | Unblock local dev toolchain for core team | DevEx | partial | requires implementation | `node --version`, `pnpm install --frozen-lockfile`, pytest collect-only |
| S0-3 | Create sprint tracking board | Platform Governance | not covered | requires implementation | Board/project visible with S0-S6 lanes and P0 labels |
| S1-1 | Fix PostgreSQL backup CronJob secret reference | Platform Infrastructure | covered | covered | `kubectl create job --from=cronjob/postgres-backup ...` in staging |
| S1-2 | Remove `default="changeme"` from L1 JWT secret configs | Layer 1 | covered | covered | `python -m pytest tests/security/test_l1_jwt_secret_no_default.py -v` |
| S1-3 | Fix L4 `analysis.py` tenant fallback | Layer 4 | covered | covered | `python -m pytest tests/security/test_l4_analysis_no_default_tenant.py -v` |
| S1-4 | Move hardcoded seed passwords out of production code tree | API Platform | not covered | verified closed | `python -m pytest tests/security/test_seed_data_no_hardcoded_passwords.py -v --tb=short` |
| S1-5 | Add authentication to L1 `/metrics` endpoint | Layer 1 | covered | covered | `python -m pytest tests/security/test_l1_metrics_requires_auth.py -v` |
| S1-6 | Remove `ALLOW_DEV_AUTH_BYPASS` from root `conftest.py` | Security | covered | covered | `python -m pytest tests/security/test_dev_bypass_removed.py -v` |
| S1-7 | Expand SSRF blocklist to all cloud metadata endpoints | Layer 1 | partial | verified closed | `python -m pytest tests/security/test_l1_ssrf_blocklist.py -v --tb=short` |
| S1-8 | Upgrade Node.js and fix pnpm for all environments | DevEx | partial | requires implementation | Node 22, pnpm install, frontend build/test evidence |
| S1-9 | Add 10 missing security regression tests | Security | partial | requires implementation | `python -m pytest tests/security/ -v --tb=short` |
| S1-10 | Fix structural preflight critical findings | Platform Governance | not covered | requires implementation | `python scripts/ci/structural_preflight.py --strict` |
| S1-11 | Fix L4 `analytics.py` tenant fallback | Layer 4 | covered | covered | `python -m pytest services/layer4-agents/tests/ -k analytics -v` |
| S1-12 | Remove L1 `app_monolith.py` legacy header fallback | Layer 1 | not covered | verified closed | `python -m pytest tests/security/test_l1_app_monolith_no_header_fallback.py -v --tb=short` |
| S2-1 | Fix 16 tenant boundary violations across 13 files | Platform Security | not covered | requires implementation | `python scripts/ci/boundary_check.py --strict` |
| S2-2 | Fix 59 route tenant propagation violations | Platform Security | not covered | requires implementation | `python scripts/ci/check_route_tenant_propagation.py --strict` |
| S2-3 | Begin L3 contract drift remediation | Layer 3 | not covered | requires implementation | `python scripts/ci/check_l3_contract_drift.py` |
| S2-4 | Fix L4 migration safety issues | Layer 4 | covered | covered | `python scripts/ci/check_migration_safety.py --strict` |
| S2-5 | Fix L5 shim integrity | Layer 5 | partial | requires implementation | `python scripts/ci/check_layer5_shim_integrity.py --strict` |
| S2-6 | Create golden trace fixtures for missing skill evals | AI Platform | not covered | requires implementation | `python -m pytest tests/evals/skills/ -v` |
| S2-7 | Implement `AnthropicProvider` adapter | AI Platform | covered | covered | `python -m pytest ... -k "anthropic or provider"` |
| S2-8 | Integrate PromptRegistry into L2 extraction pipeline | Layer 2 | partial | requires implementation | Prompt version selection and lineage regression tests |
| S2-9 | Fix L6 benchmark repository tenant filter | Layer 6 | covered | covered | `python -m pytest ... -k "dataset or tenant"` |
| S3-1 | Extract billing routes from L4 to `layer7-billing` | Billing Platform | covered | covered | Billing route extraction tests |
| S3-2 | Complete L3 contract drift remediation | Layer 3 | not covered | requires implementation | `python scripts/ci/check_l3_contract_drift.py --strict` |
| S3-3 | Document L2.5 Signal Refinery | Architecture | covered | covered | ADR and architecture docs present |
| S3-4 | Consolidate duplicate billing services | Billing Platform | not covered | requires implementation | `docker compose config` shows only canonical billing service |
| S3-5 | Remove L4 non-canonical files | Layer 4 | not covered | requires implementation | `python scripts/ci/check_duplicate_source_trees.py --strict` |
| S3-6 | Ingest untracked OpenAPI specs into `contracts/` | Platform Contracts | partial | requires implementation | OpenAPI drift workflow tracks all specs |
| S3-7 | Add required arrays to 79 object schemas | Platform Contracts | partial | requires implementation | `python scripts/ci/python_contract_lint.py --strict` |
| S4-1 | Fix Vitest coverage exclusions | Frontend | covered | covered | `pnpm --dir apps/web run test:coverage` |
| S4-2 | Migrate hook files from raw `apiClient` to typed wrappers | Frontend | covered | covered | Raw apiClient hook assertion |
| S4-3 | Remove duplicate `StatusBadge` component | Frontend | partial | requires implementation | No imports from `blocks/StatusBadge` |
| S4-4 | Reduce Tailwind arbitrary values | Frontend | not covered | requires implementation | Count arbitrary values below target |
| S4-5 | Add Suspense skeleton fallbacks for lazy settings pages | Frontend | covered | covered | Suspense fallback tests/build |
| S4-6 | Add keyboard navigation to top interactive components | Frontend | not covered | requires implementation | `pnpm --dir apps/web run test:a11y:components` |
| S4-7 | Route console calls through telemetry logger | Frontend | covered | covered | `pnpm --dir apps/web run lint` |
| S4-8 | Add DEV hard guard to mock auth | Frontend | covered | covered | Auth context guard assertion |
| S4-9 | Fix OpenAPI export for all services | Platform Contracts | not covered | requires implementation | `python scripts/export_openapi.py` |
| S5-1 | Integrate Sentry into all Python services | Observability | partial | requires implementation | Sentry integration tests across all Python services |
| S5-2 | Install ArgoCD and validate sync | Platform Infrastructure | partial | requires implementation | Functional ArgoCD manifests and sync evidence |
| S5-3 | Fill WAL-G placeholders and execute restore drill | Platform Infrastructure | partial | requires implementation | Restore drill evidence artifact |
| S5-4 | Begin OpenTelemetry tracing migration | Observability | not covered | requires implementation | L1/L2 traces visible in tracing backend |
| S5-5 | Remove Patroni placeholder secrets from base manifest | Platform Infrastructure | covered | covered | `rg "REPLACE_IN_PRODUCTION" k8s/base/postgres-patroni.yaml` |
| S5-6 | Add log-based error alerts to Prometheus rules | Observability | covered | covered | `promtool check rules monitoring/prometheus/alerting/rules.yml` |
| S5-7 | Complete deploy smoke tests | Platform Infrastructure | covered | covered | Deploy workflow static and staging smoke evidence |
| S5-8 | Add RUM/web vitals to frontend | Frontend | not covered | requires implementation | Frontend web-vitals metrics evidence |
| S6-1 | Rewrite quickstart guide with accurate paths | Documentation | covered | covered | Quickstart accuracy test |
| S6-2 | Fix all 6 confirmed broken internal links | Documentation | covered | covered | Broken-link validation |
| S6-3 | Create ADR-027 | Architecture | covered | covered | ADR-027 structure test |
| S6-4 | Add L2.5 and L7 documentation | Documentation | covered | covered | Service documentation test |
| S6-5 | Create tutorials directory | Documentation | partial | requires implementation | At least 3 tutorials in `docs/tutorials/` |
| S6-6 | Consolidate 76 workflow files to fewer than 50 | DevEx | not covered | requires implementation | Workflow count below target without deleting required gates |
| S6-7 | Refactor `LLMIntentClassifier` to use adapter infrastructure | AI Platform | partial | requires implementation | No direct `AsyncOpenAI` in classifier |
| S6-8 | Begin provenance tracker persistence design | Layer 2 | not covered | requires implementation | Approved persistence design with migration/test plan |
| S6-9 | Release readiness checklist | Release | not covered | requires implementation | Signed release readiness matrix after prior validations |

## Validation Evidence

| Date | Items | Command | Result |
|---|---|---|---|
| 2026-06-04 | S1-4, S1-7, S1-12 | `python -m pytest tests/security/test_l1_ssrf_blocklist.py tests/security/test_l1_app_monolith_no_header_fallback.py tests/security/test_seed_data_no_hardcoded_passwords.py -v --tb=short` | Passed: 5 tests |
| 2026-06-04 | S1-4 | `rg -n "SeedAdmin\|SeedAnalyst" services/api/app` | Passed: no production-code matches |
| 2026-06-04 | S1-4 targeted service test | `python -m pytest services/api/app/tests/test_seed_data.py -v --tb=short` | Blocked in local environment: `ModuleNotFoundError: No module named 'passlib'` during collection |
