# Code-Health Remediation — 4-Sprint Design

**Date:** 2026-06-22  
**Source:** Repowise codebase intelligence analysis (`.windsurf/REMEDIATION_PLAN.md`)  
**Scope:** Reduce critical health hotspots, remove safe dead code, stabilize Layer 4 churn, assign ownership, and complete canonical runtime-path migration.

---

## Context & Findings

Repowise analysis identified the following risks in `C:/Users/BBB/Fabric_4L`:

| Metric | Value |
|---|---|
| Files with health score 1.0 | 30 |
| 100% duplicated files | 6 |
| Safe-to-delete dead exports | 850 (~15,009 lines) |
| High-confidence dead exports (Repowise JSON) | 718 (~10,692 lines) |
| Layer 4 90-day relative churn | up to 33,940% |
| Unowned critical files | 16+ (per Repowise; partially debunked by `docs/superpowers/codeowners-coverage-report.md`) |
| Average bus factor | 1.3 |
| Files dependent on single contributor | 2,988 |

Existing related work already in flight:

- `remediation/code-health-2026-06-22` branch: root namespace shims removed, telemetry file removed, docs refreshed.
- `cleanup/dead-code-repowise` merged: added `CLEANUP_PLAN_DEAD_CODE.md` and `artifacts/repowise_deadcode_high.json`.
- `docs/superpowers/specs/2026-06-22-production-readiness-top5-design.md`: approved design to unblock CI/build first.
- `docs/superpowers/plans/2026-06-22-fix-usePersistFn-typescript-build.md`: implementation plan for Task 1 of production-readiness design.
- `CLEANUP_PLAN_DEAD_CODE.md`: batch-ordered dead-code removal plan.

The current working tree on `main` has significant uncommitted drift (docker-compose relocations, CI script rewrites, s2s-auth work). This drift must be committed or reverted before reliable remediation gates can be run.

---

## Approaches Considered

### Approach A — Execute the 4-sprint plan exactly as written
Start with Sprint 1 (100% duplication files, dead code, ownership, Playwright nesting) and proceed sequentially through Sprint 4.

- **Pros:** Directly maps to the provided plan; clear metrics; no re-planning overhead.
- **Cons:** Does not account for the already-approved production-readiness design that unblocks CI first; may hit build failures while refactoring.

### Approach B — CI stabilization first, then health remediation (Recommended)
Execute the already-approved production-readiness top-5 tasks first (fix `usePersistFn.ts`, Layer 3 Prometheus counters, Node version, structural preflight, behavior-readiness waivers), then run the 4-sprint remediation plan on a green baseline.

- **Pros:** Prevents refactoring on a broken build; gates are meaningful from day one; aligns with existing approved work.
- **Cons:** Adds ~1 week before health-score work begins; requires reconciling two plans.

### Approach C — Fully parallel tracks
Run P0 health fixes, dead-code removal, ownership assignment, Layer 4 decomposition, and canonical-path migration in parallel workstreams.

- **Pros:** Fastest calendar time if team capacity exists.
- **Cons:** High integration risk; merge conflicts likely; difficult to attribute metric improvements; contradicts the repo's current moving-tree state.

**Recommendation:** Approach B. The repository currently cannot pass `make verify` or frontend verification, so health-remediation work would be ungated. Stabilize the build first, then execute the 4-sprint remediation plan.

---

## Design

### Phase 0 — Stabilize the Working Tree (prerequisite)

Before any remediation:

1. Resolve the uncommitted drift on `main`:
   - Commit the docker-compose relocations to `infra/compose/`.
   - Commit or revert CI script changes.
   - Commit s2s-auth work in `services/layer2-extraction/`.
2. Execute the approved production-readiness design (`2026-06-22-production-readiness-top5-design.md`).
3. Ensure `make verify`, `pnpm run verify:frontend`, and `python scripts/ci/gate_engineering_validator.py validate` pass.

### Phase 1 — Sprint 1: Critical Duplication + Dead Code Quick Wins

**Goal:** Remove the highest-risk duplication and the safest dead code; assign CODEOWNERS for unowned auth/routing files.

| Track | Work |
|---|---|
| P0 duplication | Consolidate the 6 100%-duplication files into shared utilities or delete the redundant copies. Files: `services/layer1-ingestion/src/adapters/sec_edgar.py`, `xbrl_parser.py`, `robots_checker.py`, `services/layer3-knowledge/src/cache/redis_cache.py`, `services/layer4-agents/src/database.py`, and the canonical duplicate under `services/layer4-agents/src/layer4_agents/database.py`. |
| P1 dead code (frontend) | Remove verified safe re-export wrappers under `src/features/intelligence-workspace/tabs/`. Do **not** delete `apps/web/src/pages/studio/NarrativeTab.tsx`, `InteractiveBusinessCase.tsx`, `ROITab.tsx`, `ValueCasePage.tsx`, or `RealizationPage.tsx` — they are loaded via dynamic imports and were previously restored after breaking the build. |
| P1 dead code (backend) | Remove `services/layer1-ingestion/src/layer1_ingestion/crawler/telemetry.py::ExecutionMetrics` (already verified and removed on remediation branch). Verify other high-confidence candidates with import search and tests. |
| P3 ownership | Update `.github/CODEOWNERS` for auth/routing files. Note: Repowise "unowned" claim was partially debunked; only add entries for genuinely missing coverage. |
| P4 nesting | Reduce nesting in `apps/web/scripts/playwright-route-audit-fast.ts::main` from 8 to ≤4 using early returns and helper functions. |

**Success metrics for Sprint 1:**

- 100% duplication files reduced from 6 to 0.
- ≥1,000 lines of verified dead code removed.
- `pnpm run verify:frontend` and targeted backend tests pass.

### Phase 2 — Sprint 2: Identity Middleware + Layer 1 Main API

**Goal:** Reduce complexity in the two largest hotspots.

| Track | Work |
|---|---|
| Identity middleware | Refactor `packages/shared/src/value_fabric/shared/identity/middleware.py`. Extract `_resolve_identity` (250 NLOC, CCN 46) into smaller, single-purpose helpers: token parsing, tenant resolution, status enforcement, and context assembly. Reduce max nesting from 6 to ≤4. Add dedicated tenant-isolation unit tests. |
| Layer 1 main API | Split `services/layer1-ingestion/src/layer1_ingestion/api/main.py` (2,844 NLOC) into route modules by domain: sources, crawlers, tasks, health. Extract shared dependencies and middleware. |

**Success metrics for Sprint 2:**

- Identity middleware CCN reduced from 46 to ≤20 (target ≤15).
- Layer 1 main API NLOC reduced by ≥30%.
- New tests cover refactored paths.

### Phase 3 — Sprint 3: Layer 1 Tasks + Layer 2 API + Layer 3 Graph Viz

**Goal:** Continue complexity reduction and begin Layer 4 stabilization.

| Track | Work |
|---|---|
| Layer 1 tasks | Decompose `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` (1,925 NLOC, CCN 34) into per-stage modules (storage, validation, post-processing). Reduce nesting from 7 to ≤4. |
| Layer 2 API | Split `services/layer2-extraction/src/layer2_extraction/api/main.py` (1,901 NLOC) into extraction routes and orchestration modules. |
| Layer 3 graph viz | Refactor `services/layer3-knowledge/src/api/routes/graph_viz.py` (CCN 46) using strategy classes for layout/render modes. Target CCN ≤15. |
| Layer 4 churn | Continue ADR-022 decomposition. Stabilize integration client contracts and add contract tests. |

**Success metrics for Sprint 3:**

- All three hotspot files show CCN ≤20 and nesting ≤4.
- Layer 4 integration client churn drops to ≤50% relative.

### Phase 4 — Sprint 4: Bus Factor + Canonical Paths + Final Validation

**Goal:** Improve ownership resilience and complete path migration.

| Track | Work |
|---|---|
| Bus factor | Implement secondary reviewer rotation for critical paths (auth, tenant isolation, middleware). Document tribal knowledge in architecture docs. |
| Canonical paths | Complete Layer 1 migration and migrate Layers 2 and 6 per ADR-021. Remove remaining `value_fabric/layerX/` shims. |
| Validation | Run full regression suite: `make verify`, contract tests, behavior-readiness audit, tenant-boundary security tests. |

**Success metrics for Sprint 4:**

- Average bus factor ≥2.0 for critical paths.
- All canonical runtime path CI gates pass.
- `make verify` is green.

---

## Overall Success Metrics

| Metric | Baseline | Target |
|---|---|---|
| Files with health score 1.0 | 30 | ≤5 |
| Safe dead code removed | 0 | ≥10,000 lines |
| Identity middleware CCN | 46 | ≤15 |
| Max nesting depth | 6–7 | ≤4 |
| Layer 4 90-day churn | 33,940% | ≤50% |
| Average bus factor | 1.3 | ≥2.0 |
| Refactored critical file test coverage | low/none | ≥80% |

---

## Testing & Verification

Per sprint:

1. Run the narrowest relevant tests first (unit → integration → contract).
2. Run `make verify` before merging the sprint branch.
3. Run behavior-readiness audit after any auth/tenant isolation change.
4. Run frontend verification after any dead-code removal in `apps/web/`.

Key commands:

```bash
# Frontend
pnpm --dir apps/web run test
pnpm --dir apps/web run typecheck
pnpm run verify:frontend

# Backend
pytest services/layer1-ingestion/tests/ -v
pytest services/layer2-extraction/tests/ -v
pytest services/layer3-knowledge/tests/ -v
pytest services/layer4-agents/tests/ -v

# Platform gates
make verify
pnpm run check:contract-compliance
python scripts/ci/gate_engineering_validator.py validate
make check-behavior-readiness-audit
```

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Working-tree drift invalidates gates | Commit/revert drift before Phase 0. |
| Dead-code false positives break build | Verify each candidate with import search; never delete default-export files referenced by dynamic import paths. |
| Refactoring auth/tenant middleware introduces isolation regressions | Add hostile tenant-isolation tests before and after; run behavior-readiness audit. |
| Layer 4 decomposition destabilizes agent workflows | Use feature flags; keep existing routes as thin proxies until new modules are tested. |
| Node version mismatch masks other failures | Pin `.nvmrc` and `package.json` engines to the chosen version. |
| Scope creep across 4 sprints | Use sprint branches; merge only when sprint metrics and gates pass. |

---

## Dependencies

- `docs/superpowers/specs/2026-06-22-production-readiness-top5-design.md` must be completed first.
- `docs/explanations/adr/ADR-021-layer-3-canonical-runtime-path.md`
- `docs/explanations/adr/ADR-022-layer4-internal-decomposition.md`
- `CLEANUP_PLAN_DEAD_CODE.md`
- `.github/CODEOWNERS`

---

## Decisions Already Made

- Approach B (CI stabilization first, then 4-sprint remediation) is recommended.
- The 6 100%-duplication files will be consolidated or removed.
- The 5 large frontend pages flagged by Repowise will **not** be deleted because they are loaded via dynamic imports.
- Dead-code removal will proceed batch-by-batch per `CLEANUP_PLAN_DEAD_CODE.md` with verification after each batch.
