# Phase 0: Monorepo State Assessment and Transformation Plan

> **For agentic workers:** This is a read-only Phase 0 assessment. Do not implement the roadmap here. Use this document as the spec for subsequent Phase 1+ work.

**Goal:** Describe the current state of the Fabric_4L monorepo against the target state of a flawless system, then produce a prioritized, executable transformation roadmap.

**Scope:** Assessment and planning only. No production-code changes were made during Phase 0 except to revert an artifact written by an assessment script.

**Assessment date:** 2026-06-23  
**Branch assessed:** `main` (`56d4d0938`)  
**Working tree at end of Phase 0:** clean (no tracked modifications)

---

## 1. Executive Summary

Fabric_4L is not a greenfield repo with no governance. It already has many of the mechanics of a "flawless monorepo": a contract-first pipeline, layered architecture tests, tenant-isolation hostile tests, production-readiness gates, policy-driven release profiles, hermetic-build-input checks, and comprehensive documentation. The dominant finding is not absence of controls but **control fragility and drift**.

| Area | Status | One-line summary |
|------|--------|------------------|
| Architecture boundaries | 🟡 Yellow | Enforced by ~15 CI scripts and architecture tests, but Layer 4 has a real dual-package shadowing problem and active compatibility shims. |
| Contract automation | 🟡 Yellow | OpenAPI is the source of truth and generated clients exist, but the canonical regeneration pipeline is currently broken in this environment. |
| Security / tenant isolation | 🟡 Yellow | Auth-first design and extensive hostile tests exist; two static-analysis gates fail due to allowlist/regex drift rather than verified runtime breaches. |
| Test / gate coverage | 🟡 Yellow | 4,625 tests collect cleanly once one import blocker is fixed; behavior contract is complete; readiness audit is YELLOW due to active waivers. |
| Observability | 🟡 Yellow | All services have structured logs and health checks; metrics/traces wiring has gaps for adjacent services and OTLP export. |
| Deployment determinism | 🔴 Red | Dockerfiles and compose files use version-tagged or `:latest` base/infra images; hermetic-build-input gate fails. |
| Documentation | 🟢 Green | Architecture, threat model, runbooks, API contracts, and governance docs are present and mostly current. |
| Dead code / shims / archives | 🟡 Yellow | Legacy debt is tracked and decreasing; archive directories are clean but agent-workspace sprawl creates noise. |

**Bottom line:** The repo can make a credible "Yes — with evidence" claim on architecture intent, security design, test layering, and documentation. It currently answers "No — with precise reasons" on contract-regeneration operability, hermetic image pinning, and a small set of drift-induced static-analysis failures. None of the red/yellow items appear to be catastrophic security breaches, but they are exactly the class of drift that makes "main is always releasable" fragile.

**Recommended first PR:** Phase 1A — Architecture Boundary Evidence Gate: canonicalize the Layer 4 source tree and fix the pytest-collection blocker. This is narrow, testable, and unlocks the full gate pipeline.

---

## 2. Current-State Scorecard

Scorecard uses Green (enforced / clean), Yellow (partial / fragile / waivered), Red (missing / unsafe / blocking).

| # | Target-state category | Status | Evidence location |
|---|----------------------|--------|-------------------|
| 2.1 | Clear package/service ownership | 🟡 Yellow | `services/` has L1–L6 + api + L2.5 + L7 + legacy `billing/`; `AGENTS.md` omits adjacent services. |
| 2.2 | Architecture boundaries mechanically enforced | 🟡 Yellow | `tests/arch/`, `tests/contract/test_import_topology.py`, `scripts/ci/check_layer4_boundaries.py`, `check_shared_imports.py`, `check_value_fabric_public_imports.py`. |
| 2.3 | Dependency direction explicit | 🟡 Yellow | 628 deep `value_fabric.shared` imports outside adapters; 10 facade imports are allowlisted; 0 deprecated namespace imports. |
| 2.4 | No dead shims / temporary paths | 🟡 Yellow | 30+ registered compatibility shims with removal dates; `services/billing/` is non-deployable compatibility tree. |
| 2.5 | Working tree clean | 🟢 Green | `git status --short` empty after reverting assessment artifact. |
| 2.6 | Contract-first APIs/schemas | 🟡 Yellow | `contracts/openapi/` is source of truth; `contracts/jsonschema/` manually maintained; breaking-change gate passes. |
| 2.7 | Generated clients fresh | 🟡 Yellow | `apps/web/src/api/generated/` exists; `pnpm run check:api-types` fails due to dependency/runtime error. |
| 2.8 | Contract drift impossible to miss | 🟡 Yellow | `contract_compliance_gate.py` exists but fails on L3 Prometheus export error. |
| 2.9 | Tests layered and meaningful | 🟡 Yellow | Unit/contract/security/arch/e2e/performance/chaos suites exist; behavior contract has 44 capabilities + 88 resolved tests. |
| 2.10 | Security default / fail-closed | 🟡 Yellow | Auth middleware, tenant context, hostile tests exist; `boundary_check.py --strict` fails on regex drift; L3 Cypher inventory allowlist drift. |
| 2.11 | Observability complete | 🟡 Yellow | Health checks, structured logs, alert rules present; Prometheus/OTEL wiring incomplete for adjacent services. |
| 2.12 | Deployment deterministic | 🔴 Red | Dockerfile base images version-tagged; compose uses `:latest` infrastructure images; `check_hermetic_build_inputs.py` fails. |
| 2.13 | Smooth developer experience | 🟢 Green | One-command bootstrap, command inventory, discovery map, and agent reference exist. |
| 2.14 | Documentation living | 🟢 Green | Discoverability audit is complete; `pnpm docs:check` passes. |
| 2.15 | Code quality stable / hotspots known | 🟡 Yellow | Legacy debt decreasing; large god-files exist in L3/L4/API. |

---

## 3. Evidence Table

| Finding | Severity | File / command | Exact result |
|---------|----------|----------------|--------------|
| Layer 4 source-tree shadowing | Medium | `python scripts/ci/check_duplicate_source_trees.py --layers layer1 layer2 layer3 layer4 layer5 layer6` | `ERROR: Compatibility modules must be explicit shims. [layer4-top-level] services/layer4-agents/src/services/llm_provider.py; [layer4-top-level] services/layer4-agents/src/shared/domain/context.py` |
| Layer 4 duplicated `database.py` | Medium | `services/layer4-agents/src/database.py` vs `services/layer4-agents/src/layer4_agents/database.py` | Both files exist (~38 KB each, ~1030 lines); canonical package copy is inside `layer4_agents/`. |
| Deep shared imports outside adapters | Low | `python scripts/ci/check_value_fabric_public_imports.py` | `OK: public_api imports=0; 628 non-public shared imports observed outside adapter modules` |
| Compatibility shims active | Low-Medium | `docs/governance/compatibility-debt-registry.md` | 30+ active runtime shims with target removal dates in 2026-07/08/09/10. |
| Contract regeneration blocked | Medium | `python scripts/ci/contract_compliance_gate.py --mode fast` | Fails with `ValueError: Duplicated timeseries in CollectorRegistry: {'layer3_deprecated_route_hits_created', 'layer3_deprecated_route_hits', ...}` in L3 export. |
| Generated TS client blocked | Medium | `pnpm run check:api-types` | Fails with `TypeError: Cannot read properties of undefined (reading 'merge')` in `@redocly/openapi-core` / `openapi-typescript`. |
| OpenAPI breaking changes clean | Low | `python scripts/ci/openapi_breaking_change_gate.py` | `findingCount: 0, unapprovedCount: 0, result: pass` |
| Tenant boundary regex gate fails | Low | `python scripts/ci/boundary_check.py --strict` | `FAIL: 9 files with 11 boundary violations` — manual review shows most are JWT-payload extraction or hint rejection, but the gate still fails. |
| L3 Cypher inventory allowlist drift | Medium | `python scripts/ci/check_l3_cypher_tenant_inventory.py` | 14 Unsafe, 52 Unknown; previously allowlisted schema/health Cypher paths now block due to line-number drift. |
| Auth bypass absent from manifests | Low | `python scripts/ci/check_auth_bypass.py` | `Production auth bypass check passed.` |
| Route auth coverage | Low | `python scripts/ci/check_route_auth_dependencies.py` | `Scanned routes: 433; Public: 36; Protected: 397; PASS` |
| pytest collection blocked | High | `python -m pytest --collect-only -q -ra tests` | `4625 items / 1 error / 3 skipped` — `tests/layer4/test_provider_adapter_conformance.py` fails with `ImportError: attempted relative import with no known parent package` from `services/layer4-agents/src/services/llm_provider.py`. |
| Behavior contract complete | Low | `python scripts/ci/check_behavior_contract.py --strict` | `capabilities: 44; resolved tests: 88; domains covered: 12/12; EXIT_CODE=0` |
| Behavior readiness YELLOW | Low | `python scripts/ci/behavior_readiness_audit.py` | `passed=77 failed=0 skipped=7; FINAL STATUS: YELLOW` (active waivers). |
| Skip governance passes | Low | `python scripts/ci/check_pytest_skip_governance.py` | `total skipped entries: 3; category counts: allowlisted=2, infrastructure=1; EXIT_CODE=0` |
| Test skip register has expiry cliff | Medium | `config/ci/test_skip_register.yaml` | 75 registered skips; many P0/P1 entries expire 2026-06-30. |
| Dockerfile base images unpinned | High | `python scripts/ci/check_hermetic_build_inputs.py` (with `PYTHONUTF8=1`) | `services\api\Dockerfile:2 base image must be pinned by digest: python:3.11.13-slim-bookworm` (same for all service Dockerfiles + apps/web). |
| Compose uses `:latest` infra images | High | `infra/compose/docker-compose.base.yml`, `.dev.yml`, `.full.yml`, `.ha.yml` | `minio/minio:latest`, `pgbouncer/pgbouncer:latest`, `hashicorp/vault:latest`, `wal-g/wal-g:latest`. |
| K8s service images digest-pinned | Low | `k8s/envs/prod/kustomization.yaml`, `k8s/envs/staging/kustomization.yaml` | Uses `digest: sha256:...` for all service workloads. |
| K8s infrastructure images version-tagged | Medium | `k8s/base/postgres.yml`, `k8s/base/redis.yml`, `k8s/base/neo4j.yml` | `postgres:15-alpine`, `redis:7-alpine`, `neo4j:5-community`. |
| Prometheus missing adjacent services | Medium | `monitoring/prometheus/prometheus.yml` | Scrapes only L1–L6; missing api-gateway, L2.5, L7. |
| Trace exporter not wired | Medium | `k8s/monitoring/opentelemetry-collector.yaml` | Exports traces only to `logging`; Jaeger deployment exists but is not wired as exporter. |
| Docs governance passes | Low | `pnpm docs:check` | `30 passed in 3.20s`. |
| Repository discoverability complete | Low | `docs/governance/repository-discoverability-audit.md` | All 20 audited domains marked `covered`; enforced by `tests/docs/test_command_map.py`. |
| Test inventory stale | Low | `docs/testing/test-inventory.md` | Generated 2026-04-29; reports 46.56% pass rate. |
| Legacy debt decreasing | Low | `python scripts/ci/check_legacy_debt.py ...` | `DEPRECATED: 65` (baseline 86), `OBSOLETE: 2` (baseline 18), `legacy_directories: 0`. |
| TBD placeholders in active docs | Low | `docs/contracts/layer6-audit-artifacts/milestones/2026-05-layer6-wrapper-audit/report.md` | `Owner: TBD, Reviewer: TBD, Sign-off date: TBD`. |
| Agent workspace sprawl | Low | `.devin/`, `.agent/`, `.agents/`, `.windsurf/` | Tracked agent memory/plan files create discoverability noise. |

---

## 4. Gap Map

### 4.1 Architecture and dependency enforcement — 🟡 Yellow

| Sub-topic | Status | Specific gap | Evidence |
|-----------|--------|--------------|----------|
| Layer boundary tests | Green | `tests/arch/`, `tests/contract/test_import_topology.py` pass (modulo Windows subprocess noise). | 75 passed, 3 failed due to `WinError 6` only. |
| Layer 4 dual-package shadowing | Red | `services/layer4-agents/src/database.py`, `src/services/`, `src/shared/` exist outside canonical `layer4_agents/` package. | `check_duplicate_source_trees.py` fails. |
| Shared import policy | Yellow | 628 deep imports; public facade not yet adopted outside adapters. | `check_value_fabric_public_imports.py` warning. |
| Compatibility shims | Yellow | 30+ active shims; `services/billing/` is non-deployable compatibility tree. | `compatibility-debt-registry.md`, no Dockerfile for `services/billing/`. |
| Documentation of ownership | Yellow | `AGENTS.md` omits L2.5, L7, value-studio. | Compare `AGENTS.md` vs `ARCHITECTURE.md`. |

### 4.2 Contract automation — 🟡 Yellow

| Sub-topic | Status | Specific gap | Evidence |
|-----------|--------|--------------|----------|
| OpenAPI source of truth | Green | `contracts/openapi/` exists, breaking-change gate clean. | 11 specs; breaking-change report `findingCount: 0`. |
| OpenAPI regeneration | Red | `contract_compliance_gate.py --mode fast` fails on L3 Prometheus export. | `ValueError: Duplicated timeseries in CollectorRegistry`. |
| Generated TS client | Red | `pnpm run check:api-types` fails on `@redocly/openapi-core` runtime error. | `TypeError: Cannot read properties of undefined (reading 'merge')`. |
| JSON Schema drift | Yellow | `contracts/jsonschema/` manually maintained; no automated drift gate. | `workflows/*.json` schemas lack `$id`/`title`. |
| L7 billing spec coverage | Yellow | `layer7-billing.json` exists but is not in contract gate config. | Not in `SPEC_CONFIG` / `GENERATED_SPECS`. |

### 4.3 Security and tenant isolation — 🟡 Yellow

| Sub-topic | Status | Specific gap | Evidence |
|-----------|--------|--------------|----------|
| Auth middleware / fail-closed | Green | GovernanceMiddleware, FabricAuthMiddleware, route auth deps all present. | `check_auth_bypass.py` pass; 397 protected routes. |
| Hostile tenant tests | Green | Extensive cross-layer matrix and hostile tests. | `tests/security/test_cross_layer_tenant_isolation_matrix.py`, etc. |
| Tenant context propagation | Green | ContextVar + FastAPI dependencies extract tenant from auth. | `identity/context.py`, `identity/middleware.py`. |
| Static tenant boundary gate | Red | `boundary_check.py --strict` fails; regex too coarse. | 9 files flagged, many are JWT-payload extraction. |
| L3 Cypher tenant inventory | Red | Allowlist line numbers drifted; schema/health Cypher now blocks. | `check_l3_cypher_tenant_inventory.py` fails. |

### 4.4 Test and gate coverage — 🟡 Yellow

| Sub-topic | Status | Specific gap | Evidence |
|-----------|--------|--------------|----------|
| Behavior contract | Green | 44 capabilities, 88 resolved tests, 12 domains. | `check_behavior_contract.py` pass. |
| Skip governance | Green | Within baseline, classified, no duplicates. | `check_pytest_skip_governance.py`, `check_test_skip_register_uniqueness.py` pass. |
| pytest collection | Red | One import error blocks full collection. | `tests/layer4/test_provider_adapter_conformance.py` ImportError. |
| Readiness audit | Yellow | YELLOW due to active L2/L3 import waivers. | `behavior_readiness_audit.py` output. |
| Skip expiry cliff | Yellow | Many P0/P1 skips expire 2026-06-30. | `config/ci/test_skip_register.yaml`. |

### 4.5 Observability — 🟡 Yellow

| Sub-topic | Status | Specific gap | Evidence |
|-----------|--------|--------------|----------|
| Structured logs / health checks | Green | All services configured. | `check_observability_coverage.py` passes 36/36. |
| Metrics coverage | Yellow | L2.5 and L7 not covered by observability check; Prometheus missing them. | `monitoring/prometheus/prometheus.yml` only L1–L6. |
| Trace export | Yellow | OTEL instrumented but OTLP endpoint not wired in compose/K8s. | `opentelemetry-collector.yaml` exports only to `logging`. |

### 4.6 Deployment determinism — 🔴 Red

| Sub-topic | Status | Specific gap | Evidence |
|-----------|--------|--------------|----------|
| Dockerfile base image pinning | Red | All service Dockerfiles use version-tagged base images. | `check_hermetic_build_inputs.py` failure list. |
| Compose infrastructure pinning | Red | `:latest` tags for MinIO, pgbouncer, Vault, WAL-G. | `infra/compose/*.yml`. |
| K8s service pinning | Green | Digest-pinned in prod/staging overlays. | `k8s/envs/prod/kustomization.yaml`. |
| K8s infrastructure pinning | Yellow | Version tags only for Postgres, Redis, Neo4j, Prometheus, Alertmanager, Jaeger. | `k8s/base/*.yml`. |
| Hermetic build inputs | Red | Script fails on unpinned images + unapproved external URLs. | `check_hermetic_build_inputs.py`. |
| Single aligned compose | Yellow | Multiple compose files; dev stack partial; mutable tags inherited. | `infra/compose/` has 15+ files. |

### 4.7 Documentation — 🟢 Green

| Sub-topic | Status | Specific gap | Evidence |
|-----------|--------|--------------|----------|
| Architecture / threat model / contracts | Green | Source-of-truth docs exist and are discoverable. | `docs/architecture/`, `docs/security/threat-model.md`, `docs/contract.md`. |
| Runbooks / incident procedures | Green | Runbooks present; alert rules link to runbooks. | `docs/operations/`, `docs/troubleshooting/runbooks/`. |
| Discoverability audit | Green | All 20 domains covered; enforced by tests. | `repository-discoverability-audit.md`, `tests/docs/test_command_map.py`. |
| Test inventory | Yellow | Stale pass-rate from April 2026. | `docs/testing/test-inventory.md`. |
| Active TBD placeholders | Yellow | Layer 6 audit milestone report has TBD owner/reviewer/sign-off. | `docs/contracts/layer6-audit-artifacts/.../report.md`. |

### 4.8 Dead code / shims / archives — 🟡 Yellow

| Sub-topic | Status | Specific gap | Evidence |
|-----------|--------|--------------|----------|
| Archive separation | Green | `archive/`, `docs/archive/` cleanly separated. | Directory structure. |
| Legacy debt tracked | Green | Counts within baseline and decreasing. | `check_legacy_debt.py` report. |
| Agent workspace sprawl | Yellow | `.devin/`, `.agent/`, `.agents/`, `.windsurf/` tracked and noisy. | Directory sizes. |
| Non-deployable billing tree | Yellow | `services/billing/` has src/tests but no Dockerfile; could be mistaken for active service. | No Dockerfile; registry labels it compatibility-only. |

---

## 5. Transformation Roadmap

The roadmap is divided into 7 phases. Each phase produces a working, testable improvement and does not require broad rewrites.

### Phase 1: Architecture and Dependency Enforcement

**Goal:** Prove and enforce import/dependency boundaries without changing business logic.

**Scope:**
- Canonicalize the Layer 4 source tree (`services/layer4-agents/src/`).
- Add an architecture test that asserts only `layer4_agents/` and explicit shims live under `src/`.
- Reconcile `AGENTS.md` maintained-service list with `ARCHITECTURE.md` and `layer-runtime-path-governance.md`.
- Flatten or deduplicate nested `archive/` paths (`archive/specs/specs/`, etc.).

**Non-goals:**
- Do not refactor large business modules.
- Do not delete compatibility shims with active consumers.
- Do not rewrite import statements across the entire repo.

**Files likely affected:**
- `services/layer4-agents/src/database.py`
- `services/layer4-agents/src/services/llm_provider.py`
- `services/layer4-agents/src/shared/domain/context.py`
- `tests/arch/test_layer4_source_tree_canonical.py` (new)
- `AGENTS.md`
- `archive/` nested duplicate directories

**Risks:**
- `src/services/llm_provider.py` may have importers outside tests; characterization test first.
- Windows subprocess handle errors may cause local test failures unrelated to code.

**Validation commands:**
```bash
python scripts/ci/check_duplicate_source_trees.py --layers layer4
pytest tests/arch/test_layer4_source_tree_canonical.py -v
python -m pytest --collect-only -q tests
```

**Acceptance criteria:**
- `check_duplicate_source_trees.py --layers layer4` passes.
- New architecture test passes.
- Full pytest collection succeeds (`0 errors`).
- `AGENTS.md` accurately lists maintained and adjacent services.

---

### Phase 2: Contract Automation and Generated-Client Freshness

**Goal:** Make the canonical contract-regeneration pipeline operational and drift detection reliable.

**Scope:**
- Fix the Layer 3 Prometheus `CollectorRegistry` duplicate-timeseries error in `scripts/export_openapi.py` / `services/layer3-knowledge/src/services/compat_metrics.py`.
- Fix the `@redocly/openapi-core` / `openapi-typescript` runtime error blocking `pnpm run check:api-types`.
- Add `layer7-billing.json` to the contract gate config or document its exclusion.
- Add `$id`/`title` to `contracts/jsonschema/workflows/*.json` and consider a JSON Schema drift gate.

**Non-goals:**
- Do not rewrite OpenAPI specs by hand.
- Do not change API behavior unless required to fix export.

**Files likely affected:**
- `services/layer3-knowledge/src/services/compat_metrics.py`
- `scripts/export_openapi.py`
- `scripts/ci/contract_compliance_gate.py`
- `package.json` / `pnpm-lock.yaml` (dependency fix)
- `contracts/jsonschema/workflows/*.json`

**Risks:**
- Dependency fix may require lockfile churn; verify with `pnpm install --frozen-lockfile`.
- Prometheus metric duplication may be a symptom of import-time side effects.

**Validation commands:**
```bash
python scripts/ci/contract_compliance_gate.py --mode fast
pnpm run check:api-types
python scripts/ci/openapi_breaking_change_gate.py
```

**Acceptance criteria:**
- `contract_compliance_gate.py --mode fast` passes without modifying tracked specs.
- `pnpm run check:api-types` passes (generated types match committed output).
- Breaking-change gate still passes.

---

### Phase 3: Security, Tenant Isolation, and Fail-Closed Hardening

**Goal:** Eliminate false-positive static-analysis failures and refresh tenant-scoping evidence.

**Scope:**
- Refine `scripts/ci/boundary_check.py` to distinguish trusted JWT-payload extraction / hint-rejection from untrusted tenant reads, or update the allowlist.
- Refresh `config/production-readiness/l3-cypher-tenant-inventory-allowlist.json` to match current line numbers; add stable function+file keys to avoid line-drift.
- Run and verify the live security suites once infrastructure is available.
- Ensure `check_route_tenant_propagation.py` is executed in CI and passing.

**Non-goals:**
- Do not weaken regex to silence violations.
- Do not remove tenant-scoping checks.

**Files likely affected:**
- `scripts/ci/boundary_check.py`
- `config/production-readiness/l3-cypher-tenant-inventory-allowlist.json`
- `.github/workflows/pr-checks.yml` (add `check_route_tenant_propagation.py` if missing)

**Risks:**
- Allowlist refresh may hide real violations; pair with hostile test execution.

**Validation commands:**
```bash
python scripts/ci/boundary_check.py --strict
python scripts/ci/check_l3_cypher_tenant_inventory.py
python scripts/ci/check_route_tenant_propagation.py
pytest tests/security/test_cross_layer_tenant_isolation_matrix.py -v
pytest tests/tenancy/ -v
```

**Acceptance criteria:**
- All tenant static-analysis gates pass.
- Hostile tenant suites pass (or have infrastructure-gated skips with waivers).
- No net reduction in tenant-scoping coverage.

---

### Phase 4: Test and Gate Stabilization

**Goal:** Make the full test-collection and readiness pipeline green.

**Scope:**
- Fix the Layer 4 provider adapter import blocker (`tests/layer4/test_provider_adapter_conformance.py` / `src/services/llm_provider.py`).
- Review and extend/renew P0/P1 test skips expiring 2026-06-30.
- Resolve behavior-readiness YELLOW by addressing or renewing active L2/L3 import waivers.
- Add a collection regression gate to CI if not present.

**Non-goals:**
- Do not delete tests to pass gates.
- Do not mark failing tests as flaky without root cause.

**Files likely affected:**
- `services/layer4-agents/src/services/llm_provider.py`
- `tests/layer4/test_provider_adapter_conformance.py`
- `config/ci/test_skip_register.yaml`
- `config/ci/behavior_readiness_waivers.yaml`
- `.github/workflows/pr-checks.yml`

**Risks:**
- Skip expiry cliff is one week away; may require urgent triage.

**Validation commands:**
```bash
python -m pytest --collect-only -q -ra tests
python scripts/ci/behavior_readiness_audit.py --report artifacts/readiness/behavior-readiness-audit.json
python scripts/ci/check_pytest_skip_governance.py artifacts/pytest-collection.txt --allowlist config/ci/pytest_skip_allowlist.yaml --baseline config/ci/pytest_skip_baseline.json --write-report artifacts/pytest-skip-governance.json
```

**Acceptance criteria:**
- Full pytest collection exits 0 with 0 errors.
- Behavior readiness audit is GREEN or YELLOW only with documented, time-boxed waivers.
- No unclassified or code-health skip regressions.

---

### Phase 5: Observability and Operational Readiness

**Goal:** Close observability wiring gaps for all deployable services.

**Scope:**
- Add `api-gateway`, `layer2-5-signal-refinery`, and `layer7-billing` to `monitoring/prometheus/prometheus.yml` scrape config.
- Implement real `/metrics` endpoints for L2.5 and L7 if absent.
- Wire `OTEL_EXPORTER_OTLP_ENDPOINT` in compose and K8s manifests; add Jaeger/OTLP exporter to `k8s/monitoring/opentelemetry-collector.yaml`.
- Update `scripts/ci/check_observability_coverage.py` to include adjacent services.

**Non-goals:**
- Do not change observability semantics for L1–L6.
- Do not add new telemetry backends.

**Files likely affected:**
- `monitoring/prometheus/prometheus.yml`
- `services/layer2-5-signal-refinery/src/l2_5_signal_refinery/api/main.py`
- `services/layer7-billing/src/layer7_billing/api/main.py`
- `infra/compose/docker-compose*.yml`
- `k8s/monitoring/opentelemetry-collector.yaml`
- `scripts/ci/check_observability_coverage.py`

**Validation commands:**
```bash
python scripts/ci/check_observability_coverage.py
pnpm test:observability
pnpm lint:logs
```

**Acceptance criteria:**
- Observability coverage check passes for all deployable services.
- Prometheus scrape config includes all services.
- Trace collector exports to a real backend in non-local environments.

---

### Phase 6: Deployment Determinism and Release Evidence

**Goal:** Make local, CI, staging, and production use reproducible, pinned, scanned images.

**Scope:**
- Digest-pin all `FROM` images in service Dockerfiles and `apps/web/Dockerfile`.
- Replace `:latest` infrastructure tags in compose files with pinned versions or digests.
- Decide whether K8s infrastructure images (Postgres, Redis, Neo4j, etc.) must be digest-pinned or are exempted by policy; update Kyverno policy or manifests accordingly.
- Fix `check_hermetic_build_inputs.py` external-URL violations or add approved-domain allowlist.
- Consolidate compose files or document which file is canonical for each environment.

**Non-goals:**
- Do not change runtime behavior of services.
- Do not delete dev convenience (partial compose is acceptable if documented).

**Files likely affected:**
- `services/*/Dockerfile`
- `apps/web/Dockerfile`
- `infra/compose/*.yml`
- `k8s/base/*.yml`
- `k8s/policy/kyverno-require-image-digests.yaml`
- `scripts/ci/check_hermetic_build_inputs.py` or its config

**Risks:**
- Pinning base images shifts patch-management responsibility to Dependabot/renovate; ensure update process is documented.
- Digest pinning may break local dev if base image is pulled from a registry not reachable in all environments.

**Validation commands:**
```bash
PYTHONUTF8=1 python scripts/ci/check_hermetic_build_inputs.py
python scripts/ci/check_production_k8s_mutable_tags.py
python scripts/ci/check_deployable_service_images.py
make docker-build
```

**Acceptance criteria:**
- `check_hermetic_build_inputs.py` passes.
- No `:latest` or `:main` tags in production-facing manifests.
- `make docker-build` succeeds locally.

---

### Phase 7: Documentation and Cleanup

**Goal:** Keep docs accurate, archives clean, and discoverability high.

**Scope:**
- Refresh `docs/testing/test-inventory.md` to reflect current pass/skip/fail posture.
- Resolve TBD owner/reviewer/sign-off in `docs/contracts/layer6-audit-artifacts/milestones/2026-05-layer6-wrapper-audit/report.md`.
- Document the purpose and boundaries of tracked agent workspaces (`.devin/`, `.agent/`, `.agents/`, `.windsurf/`).
- Flatten nested `archive/` duplicates.
- Decide fate of `services/billing/` — delete, move to archive, or clearly mark as non-deployable with CI enforcement.

**Non-goals:**
- Do not delete active agent workspaces without owner agreement.
- Do not remove historical audit archives.

**Files likely affected:**
- `docs/testing/test-inventory.md`
- `docs/contracts/layer6-audit-artifacts/milestones/2026-05-layer6-wrapper-audit/report.md`
- `docs/development/AGENTS.md` or `docs/governance/agent-workspaces.md` (new)
- `archive/` nested duplicate directories
- `services/billing/`

**Validation commands:**
```bash
pnpm docs:check
python scripts/ci/check_legacy_debt.py --baseline config/ci/legacy_debt_baseline.json --approvals config/ci/legacy_debt_approvals.json --config config/ci/legacy_debt_config.json --write-report artifacts/legacy-debt-report.json
```

**Acceptance criteria:**
- `pnpm docs:check` passes.
- No unresolved TBD placeholders in active docs.
- Legacy debt counts remain within baseline.

---

## 6. Recommended First PR

### Phase 1A — Architecture Boundary Evidence Gate: Canonicalize Layer 4 Source Tree

**Why this first:**
- It is narrow (one service, one directory).
- It fixes the highest-impact collection blocker (`tests/layer4/test_provider_adapter_conformance.py`).
- It produces a mechanical architecture test that prevents regression.
- It does not require business-logic rewrites.

**Goal:** Ensure `services/layer4-agents/src/` contains only the canonical `layer4_agents/` package root and explicit shim re-exports.

**Scope (single PR):**
1. Add `tests/arch/test_layer4_source_tree_canonical.py` with assertions:
   - Only `layer4_agents/` directory and `__init__.py` are allowed under `services/layer4-agents/src/`.
   - Any top-level `.py` file outside `layer4_agents/` must be listed in an explicit shim allowlist or absent.
2. For each file flagged by `check_duplicate_source_trees.py`:
   - `services/layer4-agents/src/services/llm_provider.py`
   - `services/layer4-agents/src/shared/domain/context.py`
   Either convert it to a shim re-exporting the canonical implementation, or move it into `layer4_agents/` and update importers.
3. Fix the relative-import failure in `tests/layer4/test_provider_adapter_conformance.py` by pointing it at the canonical module path.
4. Optionally add `services/layer4-agents/src/database.py` to the same canonicalization if it is confirmed to be a duplicate of `layer4_agents/database.py`.

**Non-goals:**
- Do not refactor `layer4_agents/` internals.
- Do not change LLM provider business logic.
- Do not touch compatibility shims in other layers.

**Files likely affected:**
- `tests/arch/test_layer4_source_tree_canonical.py` (new)
- `services/layer4-agents/src/services/llm_provider.py`
- `services/layer4-agents/src/shared/domain/context.py`
- `services/layer4-agents/src/database.py` (if duplicated)
- `tests/layer4/test_provider_adapter_conformance.py`

**Validation commands (must all pass before merge):**
```bash
# 1. New architecture test
pytest tests/arch/test_layer4_source_tree_canonical.py -v

# 2. Existing duplicate-source-tree gate
python scripts/ci/check_duplicate_source_trees.py --layers layer4

# 3. Full pytest collection (regression check for the import blocker)
python -m pytest --collect-only -q tests

# 4. Layer 4 unit tests (fast, no external deps)
make test-layer4

# 5. Structural verification (if local environment supports it)
make verify-structure
```

**Acceptance criteria:**
- `python -m pytest --collect-only -q tests` exits 0 with 0 import errors.
- `python scripts/ci/check_duplicate_source_trees.py --layers layer4` exits 0.
- `pytest tests/arch/test_layer4_source_tree_canonical.py -v` passes.
- `make test-layer4` passes (or failures are pre-existing and unrelated to the PR).
- PR touches only architecture tests, config/docs if needed, and the scoped Layer 4 import paths.

---

## 7. Exact Validation Commands

Use these commands to reproduce the Phase 0 findings and to validate Phase 1+ progress.

### 7.1 Architecture / dependency boundaries
```bash
python scripts/ci/check_layer4_boundaries.py
python scripts/ci/check_shared_imports.py --strict --scope runtime
python scripts/ci/check_value_fabric_public_imports.py
python scripts/ci/check_value_fabric_facade_imports.py --fail
python scripts/ci/check_deprecated_namespace_imports.py --json
python scripts/ci/check_duplicate_source_trees.py --layers layer1 layer2 layer3 layer4 layer5 layer6
python scripts/ci/check_legacy_debt.py --baseline config/ci/legacy_debt_baseline.json --approvals config/ci/legacy_debt_approvals.json --config config/ci/legacy_debt_config.json --write-report artifacts/legacy-debt-report.json
pytest tests/arch tests/contract/test_import_topology.py tests/contract/test_shared_import_boundary.py -q --tb=short
```

### 7.2 Contract / generated clients
```bash
python scripts/ci/openapi_breaking_change_gate.py
python scripts/ci/contract_compliance_gate.py --mode fast
pnpm run check:api-types
```

### 7.3 Security / tenant isolation
```bash
python scripts/ci/check_auth_bypass.py
python scripts/ci/check_route_auth_dependencies.py
python scripts/ci/boundary_check.py --strict
python scripts/ci/check_tenant_context_singleton.py
python scripts/ci/check_l3_cypher_tenant_inventory.py
```

### 7.4 Test / gate coverage
```bash
python -m pytest --collect-only -q -ra tests > artifacts/pytest-collection.txt 2>&1
python scripts/ci/check_pytest_skip_governance.py artifacts/pytest-collection.txt --allowlist config/ci/pytest_skip_allowlist.yaml --baseline config/ci/pytest_skip_baseline.json --write-report artifacts/pytest-skip-governance.json
python scripts/ci/check_test_skip_register_uniqueness.py --register config/ci/test_skip_register.yaml
python scripts/ci/check_behavior_contract.py --strict --write-report artifacts/behavior-contract.json
python scripts/ci/behavior_readiness_audit.py --report artifacts/readiness/behavior-readiness-audit.json
```

### 7.5 Observability / deployment
```bash
PYTHONUTF8=1 python scripts/ci/check_hermetic_build_inputs.py
python scripts/ci/check_observability_coverage.py
python scripts/ci/check_deployable_service_images.py
python scripts/ci/check_production_k8s_mutable_tags.py
python scripts/ci/validate_deploy_profile_controls.py --policy-file .fabric/prod-gates.policy.yaml --profile production-core
```

### 7.6 Documentation / cleanup
```bash
pnpm docs:check
python -m pytest tests/docs/
```

---

## 8. Risks and Assumptions

### Risks
1. **Environment-induced failures:** Some tests and scripts fail on Windows/Git Bash due to subprocess handle encoding issues (`WinError 6`, `UnicodeEncodeError`). These are not code defects but must be reproduced on Linux/CI before claiming a fix.
2. **Skip expiry cliff:** Many P0/P1 test skips expire on 2026-06-30. If not renewed or resolved, CI will flip from green to red without code changes.
3. **Lockfile churn:** Fixing the generated-client pipeline may require updating `@redocly/openapi-core` / `openapi-typescript` and validating the entire frontend build.
4. **Image digest pinning:** Pinning Dockerfile base images shifts responsibility for security patches to the platform team; without an automated update process, images can become stale.
5. **Agent workspace ownership:** `.devin/`, `.agent/`, `.agents/`, and `.windsurf/` may be owned by different agent tools; consolidating or documenting them requires coordination.

### Assumptions
1. The target state is aspirational and will be pursued incrementally; no single PR will make the repo "flawless."
2. `main` is treated as releasable unless evidence proves otherwise; the Phase 0 findings are drift/fragility, not proof of an unshippable main.
3. Characterization tests will be added before changing high-risk files (e.g., Layer 4 provider adapter imports).
4. Each Phase 1+ PR will be scoped to one phase and will not combine unrelated cleanup, refactors, generated files, and security changes.
5. Live-service validation (PostgreSQL, Redis, Neo4j, Docker) will be performed in CI or a properly provisioned local environment, not in this assessment environment.

---

## 9. Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-23 | Initial Phase 0 assessment and roadmap | Kimi Code CLI |
