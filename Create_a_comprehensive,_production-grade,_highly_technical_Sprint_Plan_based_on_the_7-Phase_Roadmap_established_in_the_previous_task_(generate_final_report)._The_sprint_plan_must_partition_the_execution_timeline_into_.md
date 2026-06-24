# Production-Grade Sprint Plan: Fabric_4L Remediation Roadmap

**Repository:** `C:\Users\BBB\Fabric_4L`  
**Planning basis:** current checkout, root `AGENTS.md`, `docs/development/DISCOVERY_MAP.md`, `docs/development/BUILD_SYSTEM.md`, `docs/reference/layer-runtime-path-governance.md`, and `docs/governance/behavior-first-testing.md`.  
**Planning horizon:** 8 weeks, four 2-week sprints.  
**Execution model:** seven roadmap phases sequenced across four sprints with narrow validation first, then canonical gates.

This plan intentionally replaces stale `src/fabric/l*` remediation paths with the current service-owned runtime paths. Net-new backend logic must land under `services/layer*-*/src/`; Layer 4 authoritative imports are `layer4_agents.*`; the removed `value_fabric.layer4.*` namespace must not be restored.

---

## Roadmap Phase Map

| Phase | Objective | Primary Canonical Sources | Sprint Window | Exit Gate |
| --- | --- | --- | --- | --- |
| Phase 1 | Stabilize test governance and remove time-based CI risk | `tests/`, `config/ci/`, `scripts/ci/check_temporal_skips.py`, `Makefile` | Sprint 1 | `make check-temporal-skips`, `make check-pytest-skip-governance` |
| Phase 2 | Harden Layer 4 import topology and execution boundaries | `services/layer4-agents/src/layer4_agents/`, `scripts/ci/check_layer4_boundaries.py` | Sprint 1 | `make check-layer4-boundaries`, `make test-layer4` |
| Phase 3 | Restore contract and API type determinism | `contracts/`, `services/api/`, layer route modules, `apps/web/src/api/generated/` | Sprint 2 | `make contract-tests`, `pnpm run check:api-types`, `pnpm contract:breaking` |
| Phase 4 | Prove tenant isolation and repository predicate coverage | `packages/shared/src/value_fabric/shared/`, service repositories, `tests/security/`, `tests/tenancy/` | Sprint 2 | `pnpm test:isolation`, `pnpm test:security:hostile` |
| Phase 5 | Wire observability and release evidence | `monitoring/`, service telemetry modules, `tests/observability/`, `artifacts/` | Sprint 3 | `pnpm test:observability`, `make gate-obs` |
| Phase 6 | Make build and container inputs hermetic | service Dockerfiles, `infra/compose/`, `scripts/ci/check_hermetic_build_inputs.py`, K8s image gates | Sprint 3 | `make check-hermetic-build-inputs`, `make docker-build-multi` where available |
| Phase 7 | Remove documentation and legacy drift | `docs/`, `docs/testing/`, `docs/governance/`, `.gitignore`, compatibility debt registry | Sprint 4 | `pnpm docs:check`, `make check-legacy-debt`, `make verify` |

---

## Master Timeline

```text
Sprint 1, Weeks 1-2: Core Stability and Layer 4 Foundation
  Phase 1: test governance stabilization
  Phase 2: Layer 4 canonical import and boundary repair

Sprint 2, Weeks 3-4: Contract Compliance and Tenant Boundaries
  Phase 3: OpenAPI/schema/type determinism
  Phase 4: tenant isolation and hostile behavior coverage

Sprint 3, Weeks 5-6: Observability and Hermetic Release Inputs
  Phase 5: telemetry, tracing, logs, evidence
  Phase 6: Docker, K8s, dependency, and hermetic input gates

Sprint 4, Weeks 7-8: Documentation, Legacy Debt, and Production Readiness
  Phase 7: documentation drift, legacy cleanup, release readiness closure
```

| Sprint | Story Points | Primary Outcome | Release Claim Allowed |
| --- | ---: | --- | --- |
| Sprint 1 | 13 | CI collection and L4 architecture gates are stable | No production-ready claim; structural stability only |
| Sprint 2 | 13 | Contracts and tenant boundaries are executable and hostile-tested | Behavior tests executed for changed domains |
| Sprint 3 | 16 | Observability and release inputs are deterministic | Gate-level evidence available for release review |
| Sprint 4 | 11 | Docs, legacy drift, and readiness gates are aligned | Production-ready only if `make production-readiness-gate` passes |

---

## Sprint 1: Core Stability and Layer 4 Foundation

### S1-T1-CI-SKIP-GOVERNANCE: Eliminate Temporal Skip Risk

**Estimate:** 3 SP  
**Priority:** Highest  
**Phase:** 1  
**Target paths:** `tests/`, `config/ci/temporal_skip_baseline.json`, `config/ci/pytest_skip_allowlist.yaml`, `scripts/ci/check_temporal_skips.py`, `scripts/ci/check_pytest_skip_governance.py`

**Goal:** Replace any ungoverned or date-expiring skip behavior with explicit, tracked skip governance. The existing repo already has canonical guards; do not invent a parallel `pytest.track_issue` mechanism unless the current scripts prove insufficient.

**Implementation steps:**

1. Run `rg "2026-06-30|skipif\(|datetime\(" tests config scripts` and classify each hit as active test debt, fixture behavior, or historical documentation.
2. For active test debt, add or update entries in the canonical skip register or allowlist with owner, reason, and removal criteria.
3. Add regression tests for the skip-governance script if a new temporal pattern is discovered.
4. Keep skip behavior visible in CI; do not convert failing tests into silent unconditional skips.

**Validation:**

```bash
make check-temporal-skips
make check-pytest-skip-governance
python -m pytest tests/ci/test_temporal_skip_guard.py -v --tb=short
```

**Done when:** no unregistered temporal skips remain, skip governance artifacts are regenerated under `artifacts/`, and collection failures are not hidden by the skip gate.

### S1-T2-L4-CANONICAL-IMPORTS: Repair Layer 4 Import Topology

**Estimate:** 5 SP  
**Priority:** Highest  
**Phase:** 2  
**Target paths:** `services/layer4-agents/src/layer4_agents/`, `services/layer4-agents/tests/`, `scripts/ci/check_layer4_canonical_imports.py`, `scripts/ci/check_layer4_boundaries.py`

**Goal:** Remove current drift from ad hoc `fabric` or root `src/` namespaces and keep Layer 4 execution code behind the service-owned `layer4_agents.*` namespace.

**Implementation steps:**

1. Inspect dirty paths before editing: `git status --short` and `git diff --name-only`.
2. Map all imports referencing `fabric.*`, `src.fabric.*`, or `value_fabric.layer4.*`.
3. Move or rewrite only the minimum affected modules into `services/layer4-agents/src/layer4_agents/`.
4. Preserve provider-agnostic boundaries: execution orchestration must depend on ports/adapters, not vendor-specific SDK objects.
5. Add tests under `services/layer4-agents/tests/` or `tests/ci/` that prove the forbidden imports fail the canonical import gate.

**Validation:**

```bash
make check-layer4-boundaries
python scripts/ci/check_layer4_canonical_imports.py
make test-layer4
pnpm test:agents
```

**Done when:** Layer 4 tests collect without circular import failures, canonical import checks pass, and no compatibility namespace is restored.

### S1-T3-L4-EXECUTION-CONTRACTS: Stabilize Scheduler and Executor Boundaries

**Estimate:** 5 SP  
**Priority:** High  
**Phase:** 2  
**Target paths:** `services/layer4-agents/src/layer4_agents/engine/`, `services/layer4-agents/src/layer4_agents/adapters/`, `services/layer4-agents/tests/`

**Goal:** Make scheduler, executor, and task execution behavior testable through ports and service-local contracts while preserving checkpoint/resume semantics.

**Implementation steps:**

1. Identify top-level side effects in `engine/__init__.py`, `execution_dispatch.py`, `executor.py`, `scheduler.py`, and adapter modules.
2. Extract shared protocols only where the same interface is used by more than one concrete adapter.
3. Keep provider-specific behavior in adapters and avoid hard-coded model/provider assumptions in core execution.
4. Add behavior tests for successful dispatch, denied invalid dispatch, and expected failure mode.
5. Confirm frontend or downstream consumers still receive the same structured output shape.

**Validation:**

```bash
python -m pytest services/layer4-agents/tests/ -v --tb=short
make test-layer4
make check-behavior-contract
```

**Done when:** execution behavior is covered by allowed and denied tests, and no public response shape changed without contract updates.

---

## Sprint 2: API Compliance and Tenant Boundaries

### S2-T1-CONTRACT-DRIFT: Restore OpenAPI and Generated Type Determinism

**Estimate:** 5 SP  
**Priority:** Highest  
**Phase:** 3  
**Target paths:** `contracts/openapi/`, `contracts/jsonschema/`, `services/api/`, layer route modules, `apps/web/src/api/generated/`

**Goal:** Ensure route handlers, OpenAPI specs, JSON Schema contracts, generated TypeScript clients, and frontend consumers agree.

**Implementation steps:**

1. Run contract checks and capture exact drift.
2. For each mismatch, choose the source of truth before editing implementation or schema.
3. Update route handler, OpenAPI, JSON Schema, generated frontend types, and tests in the same change when response shape changes.
4. Use pnpm through Corepack; do not use `npm`, `npx`, or yarn.
5. Add contract tests for both success and failure envelopes where missing.

**Validation:**

```bash
make contract-tests
pnpm run check:contract-compliance
pnpm run check:api-types
pnpm contract:breaking
```

**Done when:** generated API type diff is intentional and committed, or `pnpm run check:api-types` reports no drift.

### S2-T2-TENANT-PREDICATES: Prove Repository Tenant Filters

**Estimate:** 5 SP  
**Priority:** Highest  
**Phase:** 4  
**Target paths:** service repository modules, `tests/security/`, `tests/tenancy/`, `tests/ci/test_layer6_repository_tenant_predicates.py`

**Goal:** Every production data read/write touched in the sprint must derive tenant scope from authenticated context and fail closed for cross-tenant access.

**Implementation steps:**

1. Inventory repository methods changed by current work and identify their tenant predicate paths.
2. Reject request-body tenant IDs unless explicitly validated against authenticated context.
3. Add hostile tests for same-tenant allowed behavior, cross-tenant denied behavior, and missing-tenant failure mode.
4. For Layer 6 repositories, preserve benchmark lineage while enforcing tenant-specific usage boundaries.
5. Keep test names behavior-oriented, not method-oriented.

**Validation:**

```bash
pnpm test:isolation
pnpm test:security:hostile
python -m pytest tests/ci/test_layer6_repository_tenant_predicates.py -v --tb=short
```

**Done when:** tenant predicate checks pass and every changed repository path has allowed and denied coverage.

### S2-T3-BEHAVIOR-READINESS: Wire Critical Behavior Proofs Into Gates

**Estimate:** 3 SP  
**Priority:** High  
**Phase:** 4  
**Target paths:** `contracts/behavior-contract.yaml`, `config/ci/behavior_contract_baseline.json`, `config/ci/behavior_readiness_waivers.yaml`, `scripts/ci/behavior_readiness_audit.py`

**Goal:** Move changed critical workflows through the behavior readiness ladder instead of relying on static resolution.

**Implementation steps:**

1. Add allowed and denied tests to `contracts/behavior-contract.yaml` for changed critical behavior.
2. Update the ratchet baseline only when new capability coverage is intentionally added.
3. Remove expired or unnecessary waivers; do not hide route-not-found or import-error skips.
4. Run the readiness audit and inspect `artifacts/readiness/behavior-readiness-audit.json`.

**Validation:**

```bash
make check-behavior-contract
pnpm run test:critical-behaviors
make check-behavior-readiness-audit
```

**Done when:** audit status is GREEN, or YELLOW only with active, owned, time-boxed waivers.

---

## Sprint 3: Observability and Hermetic Release Inputs

### S3-T1-OBS-METRICS: Stabilize Metrics Registration and Scrape Coverage

**Estimate:** 5 SP  
**Priority:** High  
**Phase:** 5  
**Target paths:** service observability modules, `monitoring/`, `tests/observability/`, `docs/operations/`

**Goal:** Prevent duplicate metrics registration and prove scrape coverage for release-significant services.

**Implementation steps:**

1. Locate metric registration modules in the affected services; do not add duplicate global collectors.
2. Make registration idempotent using service-local helpers or existing observability primitives.
3. Preserve label cardinality and tenant-safe metric boundaries.
4. Add or update observability tests for duplicate initialization and expected scrape names.
5. Link alerts to runbooks where production-impacting.

**Validation:**

```bash
pnpm test:observability
pnpm lint:logs
make gate-obs
```

**Done when:** duplicate registration tests pass and scrape/alert/runbook links are documented for changed metrics.

### S3-T2-TRACE-EVIDENCE: Add Trace and Release Evidence Coverage

**Estimate:** 3 SP  
**Priority:** Medium  
**Phase:** 5  
**Target paths:** tracing modules, `monitoring/`, `scripts/ci/generate_evidence_bundle.py`, `artifacts/release/`

**Goal:** Make critical cross-layer operations observable with request IDs, trace propagation, and release evidence artifacts.

**Implementation steps:**

1. Identify critical L2-L4 or L4-L5 operations lacking trace propagation.
2. Add instrumentation through existing telemetry adapters, not route-local one-offs.
3. Ensure logs do not expose secrets, raw provider responses, or cross-tenant data.
4. Add evidence bundle generation checks where the artifact is release-significant.

**Validation:**

```bash
pnpm evidence:bundle
pnpm evidence:validate
make gate-release-policy
```

**Done when:** evidence artifacts are generated in canonical locations and release policy gates can consume them.

### S3-T3-CONTAINER-HERMETICITY: Enforce Digest-Pinned Multi-Arch Images

**Estimate:** 5 SP  
**Priority:** High  
**Phase:** 6  
**Target paths:** service Dockerfiles, `apps/web/Dockerfile*`, `infra/compose/`, `.github/workflows/`, `docs/development/BUILD_SYSTEM.md`

**Goal:** Keep container base images digest-pinned, multi-arch capable, and aligned with the runtime version matrix.

**Implementation steps:**

1. Compare service Dockerfiles against the Python and Node digest pins in `BUILD_SYSTEM.md`.
2. Update all service Dockerfiles together when refreshing base image digests.
3. Preserve local ARM64 compose override behavior under `infra/compose/docker-compose.arm64.yml`.
4. Avoid `latest`, `main`, or mutable production image tags.
5. Record any runtime exception in the version matrix before merging.

**Validation:**

```bash
make check-production-k8s-mutable-tags
make check-k8s-image-digests
make docker-build-multi
```

**Done when:** mutable tag gates pass and multi-arch build behavior is reproducible or explicitly documented if local Docker is unavailable.

### S3-T4-HERMETIC-INPUTS: Reduce Build Input False Positives Without Weakening Security

**Estimate:** 3 SP  
**Priority:** Medium  
**Phase:** 6  
**Target paths:** `scripts/ci/check_hermetic_build_inputs.py`, `Makefile`, `config/ci/`, service dependency manifests

**Goal:** Keep hermetic build checks strict for production inputs while excluding local caches and generated development artifacts.

**Implementation steps:**

1. Reproduce current failures with the canonical Makefile target.
2. Add exclusions only for non-production generated/cache paths already ignored by git or explicitly documented.
3. Add regression tests for both accepted exclusions and rejected dynamic network inputs.
4. Avoid inline allowlist comments unless the URL is documented as pinned and release-owned.

**Validation:**

```bash
make check-hermetic-build-inputs
python -m pytest tests/ci/ -k hermetic -v --tb=short
```

**Done when:** false positives are removed and malicious dynamic input fixtures still fail the gate.

---

## Sprint 4: Documentation, Legacy Drift, and Readiness Closure

### S4-T1-TEST-INVENTORY: Regenerate Test Inventory From Canonical Sources

**Estimate:** 3 SP  
**Priority:** Medium  
**Phase:** 7  
**Target paths:** `docs/testing/`, `tests/`, `scripts/ci/`, `docs/development/DISCOVERY_MAP.md`

**Goal:** Replace stale manual test inventory with a discoverable, generated or gate-checked inventory that matches current test ownership.

**Implementation steps:**

1. Use `docs/testing/test-inventory.md` and `docs/testing/TEST_CATALOG.md` as canonical docs targets, not a new root-level doc.
2. Generate inventory from integration, contract, security, tenant, and behavior tests; omit low-value unit-test noise unless already required by docs.
3. Enforce missing metadata through docs or CI tests rather than manual review.
4. Link inventory routes back to `DISCOVERY_MAP.md`.

**Validation:**

```bash
pnpm docs:check
python -m pytest tests/docs/ -v --tb=short
```

**Done when:** docs tests pass and inventory is reachable from canonical docs.

### S4-T2-DOC-PLACEHOLDERS: Remove Active Documentation Placeholders

**Estimate:** 2 SP  
**Priority:** Medium  
**Phase:** 7  
**Target paths:** `docs/`, `README.md`, `AGENTS.md`, docs lint tests

**Goal:** Remove unresolved placeholder language from active docs without rewriting archived snapshots.

**Implementation steps:**

1. Search active docs only: `rg "\b(TBD|TODO_RELEASE|FIXME|XXXX)\b" docs README.md AGENTS.md`.
2. Classify matches as active docs, code examples, archived references, or intentional policy text.
3. Replace active placeholders with verified values sourced from code, contracts, or runbooks.
4. Add or update docs tests for public placeholder regressions.

**Validation:**

```bash
pnpm docs:check
python -m pytest tests/docs/ -v --tb=short
```

**Done when:** active public docs have no unresolved release placeholders and archived exceptions are documented by tests or ignore rules.

### S4-T3-LEGACY-DEBT: Decommission Only Approved Legacy Paths

**Estimate:** 3 SP  
**Priority:** Medium  
**Phase:** 7  
**Target paths:** `docs/governance/compatibility-debt-registry.md`, `config/ci/legacy_debt_baseline.json`, `services/layer7-billing/`, legacy `services/billing/` if present

**Goal:** Remove or quarantine legacy code only after proving no production, test, migration, or docs route depends on it.

**Implementation steps:**

1. Confirm ownership in `docs/reference/layer-runtime-path-governance.md`; billing canonical path is `services/layer7-billing/src/layer7_billing/`.
2. Use `rg` and `git ls-files` to find tracked references to any candidate legacy path.
3. Update compatibility debt registry and legacy debt baseline in the same change.
4. Do not delete migrations or historical artifacts unless repository policy explicitly permits it.
5. Prefer archive or baseline reduction over broad deletion when deploy history is uncertain.

**Validation:**

```bash
make check-legacy-debt
make check-compatibility-shims
make verify-structure
```

**Done when:** legacy debt gates pass and no source-of-truth path is removed accidentally.

### S4-T4-GITIGNORE-AGENT-STATE: Harden Local Agent Workspace Ignore Rules

**Estimate:** 3 SP  
**Priority:** High  
**Phase:** 7  
**Target paths:** `.gitignore`, `scripts/ci/check_path_and_env_hygiene.py`, `config/ci/`

**Goal:** Prevent local agent state, downloaded prompts, and path artifacts from entering version control without hiding legitimate source files.

**Implementation steps:**

1. Inspect existing `.gitignore`; it already ignores `.agent/memory/episodic/` and Windows path artifacts.
2. Add only missing local-agent directories that are generated and non-reproducible.
3. If a path is already tracked, remove it from the index only with explicit approval and after reviewing content.
4. Add path-hygiene regression coverage if new patterns are security-relevant.

**Validation:**

```bash
git status --short --ignored
make check-path-env-hygiene
make check-manifest-secret-hygiene
```

**Done when:** generated agent memory is ignored, path hygiene passes, and no tracked source path is masked by an overbroad ignore rule.

---

## Cross-Sprint Governance Rules

1. **Dirty worktree isolation:** before each task, run `git status --short --branch`; preserve unrelated changes.
2. **Contract-first edits:** API behavior changes require contract, schema, generated type, consumer, and test alignment.
3. **Tenant-safe defaults:** repository reads/writes must use authenticated context tenant IDs and include hostile tests where security-sensitive.
4. **Provider-agnostic Layer 4:** provider-specific code belongs in adapters; core orchestration must depend on ports and versioned output contracts.
5. **Frontend governance:** any `apps/web/` edit requires reading root `DESIGN.md` and using existing shell, tab, right-rail, TanStack Query, and shared component patterns.
6. **No broad rewrites:** refactor only the named module or boundary needed for the task.
7. **No weakened gates:** update tests and baselines only when behavior is intentionally governed and evidence-backed.

---

## Verification Matrix

| Domain | Narrow Validation | Broader Gate | Evidence |
| --- | --- | --- | --- |
| Temporal skips | `make check-temporal-skips` | `make verify-structure` | `artifacts/temporal-skip-guard.*` |
| Pytest skip governance | `make check-pytest-skip-governance` | `make verify` | `artifacts/pytest-skip-governance.json` |
| Layer 4 imports | `python scripts/ci/check_layer4_canonical_imports.py` | `make check-layer4-boundaries` | command output plus tests |
| Layer 4 execution | `python -m pytest services/layer4-agents/tests/ -v --tb=short` | `make test-layer4`, `pnpm test:agents` | pytest output |
| Contracts | `make contract-tests` | `make gate-api-contracts`, `make verify` | contract drift reports |
| API generated types | `pnpm run check:api-types` | `make verify` | clean generated type diff |
| Tenant isolation | `pnpm test:isolation` | `make gate-security` | isolation artifacts |
| Hostile security | `pnpm test:security:hostile` | `make gate-security` | pytest output |
| Behavior readiness | `make check-behavior-contract` | `make check-behavior-readiness-audit`, `make production-readiness-gate` | `artifacts/readiness/behavior-readiness-audit.json` |
| Observability | `pnpm test:observability` | `make gate-obs` | observability test reports |
| Hermetic inputs | `make check-hermetic-build-inputs` | `make verify` | CI gate output |
| K8s image policy | `make check-production-k8s-mutable-tags`, `make check-k8s-image-digests` | `make production-readiness-gate` | gate output |
| Docs | `pnpm docs:check` | `make verify` | docs pytest output |
| Legacy debt | `make check-legacy-debt` | `make verify` | `artifacts/legacy-debt-report.json` |

---

## Production Readiness Acceptance Criteria

A final readiness claim is allowed only after all of the following are true:

1. `make check-behavior-contract` passes.
2. `pnpm run test:critical-behaviors` executes and passes.
3. `make check-behavior-readiness-audit` reports GREEN, or YELLOW with active, owned, time-boxed waivers.
4. `make production-readiness-gate` passes for the intended release profile.
5. Any API or schema change has matching OpenAPI, JSON Schema, generated TypeScript types, consumer updates, and regression tests.
6. Any tenant-sensitive change has hostile cross-tenant tests.
7. Any frontend change has followed `DESIGN.md` and passed focused frontend validation.
8. Any residual risk is recorded in the sprint acceptance notes with owner and date.

---

## Sprint Closeout Format

Use this exact closeout shape for each sprint:

```markdown
## Summary

- What changed
- Why it changed
- Files touched

## Validation

- Commands run
- Tests passed
- Tests not run and why

## Risk / Follow-up

- Residual risk
- Contract or migration concern
- Manual verification needed
```

Do not claim tests, gates, or production readiness passed unless the commands actually ran in the current checkout.
