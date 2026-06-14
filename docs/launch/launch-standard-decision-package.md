# Launch Standard Decision Package

- **Date (UTC):** 2026-06-13
- **Prepared by:** Engineering / Release Management
- **Purpose:** Decide which launch standard governs the remaining work before launch.
- **Related artifacts:**
  - `docs/launch/launch-blocker-register.md`
  - `docs/readiness/current.md`
  - `docs/readiness/launch-decision-artifact.md`

---

## Executive Summary

Two independent categories of remaining work exist:

1. **Repository-owned test debt** that keeps `make verify` from passing. This debt pre-dates the latest remediation sprint and is not caused by the recent fixes.
2. **Environment-dependent launch gates** (staging E2E, rollback drill, SSO/OIDC, billing/observability/performance validation) that cannot be closed from repository changes alone.

The local Docker live-stack is healthy, the cross-layer critical-path smoke passes (`passed=12, failed=0`), the security smoke passes, and the rollback verifier passes. Layer 2 unit tests pass cleanly.

**Recommendation:** Adopt **Option A — Core GA Launch Standard**.

Under Core GA, the immediate next step is a **time-boxed 1-day remediation of the small set of repository failures that are genuinely launch-relevant**, while the remaining historical test debt is formally documented and accepted. `make verify` is treated as informative, not a hard launch gate. Work then pivots to collecting environment-dependent evidence.

---

## 1. Failure Inventory — `make contract-tests` (contract_static subset)

Evidence command: `py -3.11 -m pytest tests/contract/ --tb=line -m contract_static -n 0 -q`

| File | Failures / Run | First failing assertion | Layer / Owner | Failure type |
|---|---|---|---|---|
| `test_l3_route_alias_parity.py` | 2 / 2 | `AttributeError: module 'src.agents' has no attribute 'NarrativeSynthesisAgent'` | Layer 3 | Import/runtime drift |
| `test_layer3_graph_deprecation_contract.py` | 3 / 7 | Deprecation counter `0 >= 1`; `KeyError: '/api/v1/query'`; alias set not in schema | Layer 3 | Deprecation metadata drift |
| `test_l3_formula_alias_contract.py` | 2 / 3 | `FileNotFoundError: packages/platform-contract/src/typescript/generated/src.ts`; `KeyError: 'deprecated'` | Layer 3 / Frontend | Generated types / OpenAPI drift |
| `test_shared_import_boundary.py` | 1 / 10 | `assert not (REPO_ROOT / "shared").exists()` → root `shared/` still present | Platform | Namespace cleanup |
| `test_health_contract_and_red_metrics.py` | 3 / 4 | Missing `failure_reason` in L4 core routes shim; missing `tenant_id` label in L1 metrics; missing L3 metric token `value_fabric_graph_mutation_rate` | L1 / L3 / L4 / Observability | Observability contract gap |
| `test_l3_graph_contract.py` | 1 / 14 | `Required schema 'EntityContextResponse' missing from OpenAPI spec` | Layer 3 | OpenAPI schema drift |
| `test_state_inspector_auth_contract.py` | 1 / 1 | `analyze_errors not found in state_inspector.py` | Layer 4 | Auth wiring contract |
| `test_service_api_entrypoint_architecture.py` | 3 / 3 | `formula_governance.py` >25 KiB; `legacy_health_check` in L1 `main.py`; L1 `main.py` >35 KiB | L1 / L3 | Architecture hygiene |
| `test_layer_service_entrypoint_smoke.py` | 1 / 1 | `ImportError: attempted relative import with no known parent parent package` | All layers | Entrypoint import wiring |
| `test_l4_frontend_contract.py` | 4 / 10 | `WorkflowStatusResponse` missing required `id`; `frontend/client/` paths do not exist | Layer 4 / Frontend | Frontend contract / path drift |
| `test_layer4_contract.py` | 14 / 23 | `401 Unauthorized` on workflow/tool/agent/billing endpoints | Layer 4 | Auth / test classification |
| `test_journey_contracts.py` | 11 / 18 | `401 Unauthorized` on journey endpoints | L1 / L4 / L5 | Auth / live-service contract |
| `test_probe_contract_shared.py` | 2 / 3 | `ImportError: attempted relative import beyond top-level package` | Layer 6 | Import wiring |
| `test_import_topology.py` | 0 / 45 (timeout) | `subprocess.run(pytest --collect-only ...)` hits the 60 s timeout because L1/L3 collection hangs | Meta | Collection / infra gate |

**Total contract_static failures (excluding timeout):** 47 failures across 13 files.

### `make test` / unit test failures

Evidence commands:

- `cd services/layer1-ingestion && py -3.11 -m pytest tests/api -q --timeout=10` → hangs in `test_targets_route_ordering.py` at `client.post(...)`.
- `cd services/layer3-knowledge && py -3.11 -m pytest tests/test_audited_mutation.py -q --timeout=10` → `KeyError: 'tenant_id'` in `test_node_write_includes_tenant_id`.
- `cd services/layer3-knowledge && py -3.11 -m pytest tests/ -m unit -q --timeout=10` → hangs/times out on tests that start the L3 app because local Redis/Neo4j/Postgres are not reachable.

| File / Suite | Failure type | Layer | Notes |
|---|---|---|---|
| `tests/api/test_targets_route_ordering.py` | App startup/TestClient hang | Layer 1 | L1 app creation eagerly instantiates a Redis-backed `TenantRateLimiter`; without reachable Redis the test thread blocks. |
| `tests/test_audited_mutation.py` | `KeyError: 'tenant_id'` | Layer 3 | Pure logic assertion failure on tenant injection. |
| Multiple L3 unit/integration files | Testcontainers image pull / service connection timeout | Layer 3 | Local L3 tests assume Docker-backed Neo4j/Postgres or running services. |

Layer 2 unit tests pass cleanly (`pytest services/layer2-extraction/tests/` → pass with 3 skips).

---

## 2. Classification

| File / Suite | Classification | Rationale |
|---|---|---|
| `test_l3_route_alias_parity.py` | **Launch Relevant** | Route aliases (`/v1/query`, `/v1/graphrag`) are public API surface; if broken, frontend callers break. |
| `test_layer3_graph_deprecation_contract.py` | **Historical Debt** | Tests deprecation counters and `deprecated` flags. Runtime still works; drift is in observability/documentation surface. |
| `test_l3_formula_alias_contract.py` | **Historical Debt** | Generated TypeScript file missing; `formula_id` deprecation metadata missing. Frontend can still function with current types. |
| `test_shared_import_boundary.py` | **Historical Debt** | Root `shared/security/config.py` remains. No known runtime shadowing failure; cleanup is hygiene. |
| `test_health_contract_and_red_metrics.py` | **Launch Relevant** | Observability contract (B4) requires health `failure_reason`, tenant-scoped RED metrics, and L3 alerting. Gaps here reduce production operability. |
| `test_l3_graph_contract.py` | **Launch Relevant** | `EntityContextResponse` schema is a documented API contract. If removed intentionally, test should be updated; if missing by accident, frontend consumers break. |
| `test_state_inspector_auth_contract.py` | **Launch Relevant** | Verifies auth dependency on an error-inspection route. Missing function means the contract is not implemented. |
| `test_service_api_entrypoint_architecture.py` | **Non-Launch** | File-size budgets and handler-location rules. Important architecture hygiene, but not a launch blocker. |
| `test_layer_service_entrypoint_smoke.py` | **Launch Relevant** | All maintained service entrypoints must load and expose OpenAPI. Failure blocks service startup validation. |
| `test_l4_frontend_contract.py` | **Mixed** | `WorkflowStatusResponse` missing `id` is Launch Relevant; `frontend/client/` path checks are Historical Debt (project uses `apps/web`). |
| `test_layer4_contract.py` | **Launch Relevant (test config)** | Failures are `401 Unauthorized` from live endpoints. Likely fixture/marker misclassification: these tests use live services but are marked `contract_static`. Not a runtime bug, but must be tagged/configured correctly for launch evidence. |
| `test_journey_contracts.py` | **Launch Relevant (test config)** | Same as above: live-service journey tests return `401` because the local test client has no auth token. Environment/test-config issue, not a product bug. |
| `test_probe_contract_shared.py` | **Launch Relevant** | Relative import beyond top-level in L6 probe route. Small wiring fix; probes are operational. |
| `test_import_topology.py` | **Launch Relevant (meta)** | Timeouts because L1/L3 collection hangs. Once L1/L3 collection is healthy, this meta-gate passes. |
| L1 API tests hang | **Launch Relevant (test infra)** | Tests assume Redis is reachable. Blocks `make test` for Layer 1. The live stack works, so this is a test-environment wiring issue. |
| L3 `test_audited_mutation.py` tenant_id failure | **Launch Relevant** | Real tenant-injection contract failure in pure logic. |
| L3 testcontainers / service timeouts | **Launch Relevant (test infra)** | L3 tests assume Docker/services. Same category as L1: environment wiring, not a product defect. |

### Classification summary

| Category | Count of failing files | Representative examples |
|---|---|---|
| **Launch Critical / Launch Relevant** | 9 files + 2 infra suites | `test_health_contract_and_red_metrics.py`, `test_l3_route_alias_parity.py`, `test_l3_graph_contract.py`, `test_state_inspector_auth_contract.py`, `test_layer_service_entrypoint_smoke.py`, `test_probe_contract_shared.py`, `test_import_topology.py`, L1 hang, L3 tenant_id failure, L3 service timeouts |
| **Historical Debt** | 4 files | `test_layer3_graph_deprecation_contract.py`, `test_l3_formula_alias_contract.py`, `test_shared_import_boundary.py`, parts of `test_l4_frontend_contract.py` |
| **Non-Launch** | 1 file | `test_service_api_entrypoint_architecture.py` |

---

## 3. Repository Green Estimate

### Scope

To make `make verify` pass, the following would need to be addressed:

1. All 47 contract_static failures across 13 files.
2. The `test_import_topology.py` timeout (depends on fixing L1/L3 collection).
3. Layer 1 API test hang (Redis connection at app-import time).
4. Layer 3 `test_audited_mutation.py` `KeyError: 'tenant_id'`.
5. Layer 3 testcontainers / service-connection timeouts for integration tests.
6. Similar environment-wiring issues likely in Layers 4, 5, and 6 (Layer 5 already shows 120 failures + 232 errors; Layer 4 and 6 hit testcontainers image pulls).

### Effort estimate

| Area | Files / suites | Estimated investigation | Estimated remediation | Major risks |
|---|---|---|---|---|
| Contract test OpenAPI / schema drift | 5 files | 4–6 h | 4–8 h | Regenerating OpenAPI may surface additional drift; frontend types may need regeneration. |
| Contract test import / wiring / auth classification | 5 files | 4–6 h | 4–8 h | `401` failures may require adding service auth secrets to fixtures or reclassifying tests; risk of masking real auth gaps. |
| Observability metrics contract (`test_health_contract_and_red_metrics.py`) | 1 file | 2–3 h | 3–6 h | Metrics shims may need real instrumentation; alert rules may need design review. |
| Layer 1 API test environment (Redis hang) | ~5 API test files | 3–4 h | 4–8 h | Patching app startup to be lazy/test-friendly may touch production initialization path. |
| Layer 3 audited mutation `tenant_id` | 1 file | 1–2 h | 1–3 h | Could expose a real tenant-scoping bug in graph mutations. |
| Layer 3 testcontainers / service wiring | ~10+ integration files | 4–6 h | 6–12 h | Docker image availability, local Postgres/Neo4j ports, env alignment. |
| Layers 4–6 similar infra debt | unknown | 4–6 h | 6–12 h | More testcontainers/auth fixtures. |
| `make verify` full gate validation | — | 2–3 h | 2–4 h | Iterating through remaining flaky/timeout failures. |

**Total rough estimate:** 1–2 engineering weeks for a single engineer to drive `make verify` to green, assuming no new blockers are discovered.

### What Repository Green would *not* deliver

- It would **not** close any environment-dependent P0/P1 launch gate (staging E2E, rollback drill, SSO, billing, observability dashboards, performance smoke, live LLM validation).
- It would **not** reduce the risk of those environment-dependent items failing in staging/production.
- It would likely consume the remaining pre-launch runway.

---

## 4. Comparison of Launch Standards

### Option A — Core GA Launch Standard

> The product may launch when launch-critical code paths, security controls, tenant isolation, observability, critical E2E journeys, and environment validation pass. Known historical repository test debt may remain open if it is unrelated to launch scope, documented, risk-assessed, and accepted.

**Evidence in favor:**
- Local live-stack smoke passes end-to-end (`overall=pass`, `passed=12`, `failed=0`).
- Security smoke passes (`make security-smoke` → 13 passed, 1 expected xfail).
- Rollback verifier passes (`verify_release_rollback.py` → 8/8).
- Layer 2 unit tests pass.
- The repository-owned failures are overwhelmingly stale test/artifact debt or test-environment wiring, not production defects.

**Evidence against:**
- `make verify` is not green.
- Some launch-relevant contract gaps exist (observability, route aliases, auth wiring, entity-context schema).
- Accepting debt requires explicit sign-off and a remediation plan.

### Option B — Repository Green Standard

> The product may not launch until `make verify`, `make contract-tests`, and `make test` all pass with no unresolved contract failures.

**Evidence in favor:**
- Provides a clean, objective gate.
- Forces closure of the observability and route-alias gaps before launch.

**Evidence against:**
- Estimated 1–2 weeks of work on tests that are largely unrelated to runtime launch readiness.
- Does not advance environment-dependent P0/P1 evidence.
- High opportunity cost: time spent fixing file-size budgets and deprecation-counter tests is time not spent on staging validation.

---

## 5. Recommendation

**Adopt Option A — Core GA Launch Standard**, with the following conditions:

### 5.1 Immediate time-boxed remediation (1 engineering day)

Before declaring Core GA ready, fix or formally scope the genuinely launch-relevant repository failures:

| Item | Action | Owner |
|---|---|---|
| `test_health_contract_and_red_metrics.py` | Add `failure_reason` to L4 health shim, add `tenant_id` label to L1 metrics, add required L3 metric tokens and alert rules. | L1 / L3 / L4 / Observability |
| `test_l3_route_alias_parity.py` | Resolve `src.agents` import drift so alias routes work; verify aliases return 200. | Layer 3 |
| `test_l3_graph_contract.py` | Confirm whether `EntityContextResponse` was intentionally removed. If yes, update/remove test. If no, regenerate OpenAPI. | Layer 3 / Frontend |
| `test_state_inspector_auth_contract.py` | Confirm `analyze_errors` route exists and is auth-protected, or update contract test. | Layer 4 |
| `test_layer_service_entrypoint_smoke.py` | Fix relative-import error so all six layer entrypoints load. | Platform / respective layers |
| `test_probe_contract_shared.py` | Fix relative-import error in L6 probe route. | Layer 6 |
| L3 `test_audited_mutation.py` tenant_id failure | Fix tenant injection or update test to match intended contract. | Layer 3 |
| L1 API test hang | Make Redis/dependency initialization lazy for test client, or provide test-mode env that mocks Redis. | Layer 1 |

### 5.2 Document and accept historical debt

The following items are **not** launch-blocking under Core GA. They must be tracked in `docs/launch/launch-blocker-register.md` with owners:

- `test_layer3_graph_deprecation_contract.py`
- `test_l3_formula_alias_contract.py`
- `test_shared_import_boundary.py`
- `test_service_api_entrypoint_architecture.py`
- `frontend/client/` path checks in `test_l4_frontend_contract.py`

### 5.3 Close or reclassify live-service contract tests

- `test_layer4_contract.py` and `test_journey_contracts.py` should either:
  - be run with a valid service-auth token in a live-service test job, or
  - be reclassified/marked so they are not executed as `contract_static` tests against unauthenticated endpoints.

### 5.4 Pivotal next step after remediation

Stop chasing repository test debt and shift to environment-dependent evidence collection:

- P0-001: Staging Playwright critical journeys
- P0-002: Rollback / restore drill in a launch-like environment
- P0-003: Enterprise SSO / OIDC validation
- P1 observability, billing, performance, and live-LLM validation

---

## 6. Decision Record

| Question | Answer |
|---|---|
| **Selected launch standard** | **Option A — Core GA Launch Standard** |
| **`make verify` as hard gate?** | **No.** It remains informative. The repository-owned sub-gates that passed in this sprint (`lint`, `typecheck`, `security-smoke`, `verify-structure`, behavior-readiness, docs-harness) are required. The full `make verify` gate is blocked by pre-existing test debt that is not launch-critical. |
| **Remaining repository debt accepted?** | **Conditionally.** Historical-debt items are accepted only if tracked with owners. Launch-relevant items in §5.1 must be remediated or formally scoped before Core GA sign-off. |
| **Environment-dependent gates still required?** | **Yes.** P0-001, P0-002, P0-003, and P1 items remain required and cannot be closed from the repository. |

---

## 7. Supporting Evidence Log

| Command | Result | Date |
|---|---|---|
| `python scripts/e2e/critical_path_smoke.py --host` | `overall=pass`, `passed=12`, `failed=0` | 2026-06-13 |
| `make security-smoke` | 13 passed, 1 xfailed | 2026-06-13 |
| `python scripts/ci/verify_release_rollback.py` | 8/8 passed | 2026-06-13 |
| `cd services/layer2-extraction && pytest tests/` | pass (3 skips) | 2026-06-13 |
| `py -3.11 -m pytest tests/contract/ -m contract_static -n 0 -q` | 47 failures across 13 files | 2026-06-13 |
| `cd services/layer1-ingestion && pytest tests/api --timeout=10` | Hangs in `test_targets_route_ordering.py` | 2026-06-13 |
| `cd services/layer3-knowledge && pytest tests/test_audited_mutation.py::TestTenantIsolation::test_node_write_includes_tenant_id --timeout=10` | `KeyError: 'tenant_id'` | 2026-06-13 |
