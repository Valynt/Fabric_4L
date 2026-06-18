# Repository Organization Cleanup Audit

**Audit Date:** 2026-06-18
**Auditor:** GitHub Copilot
**Status:** Phase 1 implementation in progress

---

## Executive Summary

This audit identifies cleanup opportunities for the Fabric_4L repository to reduce clutter, improve discoverability, and separate source code, product docs, evidence, generated outputs, scripts, tests, and launch artifacts.

**Key Findings:**
- 6,775 file paths indexed by workspace search
- 120+ directories enumerated during bounded inspection
- Existing docs archive policy is active under `docs/archive/`
- Generated/local clutter exists: caches, logs, dist, test results, Playwright reports
- `.devin/` contains historical plans and duplicate assurance files
- Launch evidence and audit artifacts are preserved in canonical locations

---

## Current Repo Structure Observations

### Canonical Layout (Per `canonical-paths.yaml` and `ARCHITECTURE.md`)

| Area | Path | Status |
|------|------|--------|
| Frontend | `apps/web/` | Active |
| API Gateway | `services/api/` | Active |
| Layer 1 | `services/layer1-ingestion/` | Active |
| Layer 2 | `services/layer2-extraction/` | Active |
| Layer 2.5 | `services/layer2-5-signal-refinery/` | Active |
| Layer 3 | `services/layer3-knowledge/` | Active |
| Layer 4 | `services/layer4-agents/` | Active |
| Layer 5 | `services/layer5-ground-truth/` | Active |
| Layer 6 | `services/layer6-benchmarks/` | Active |
| Layer 7 | `services/layer7-billing/` | Active |
| Shared Packages | `packages/shared/` | Active |
| Platform Contract | `packages/platform-contract/` | Active |
| Documentation | `docs/` | Active |
| Tests | `tests/` | Active |
| Kubernetes | `k8s/` | Active |
| Monitoring | `monitoring/` | Active |
| Packs | `packs/` | Active |

### Compatibility Shims (Per `canonical-paths.yaml`)

| Path | Status | Notes |
|------|--------|-------|
| `value_fabric/layer1/` | Shim only | Namespace facade; removal review by 2026-09-30 |
| `value_fabric/layer2/` | Shim only | Namespace facade; removal review by 2026-09-30 |
| `value_fabric/layer3/` | Shim only | Migrated 2026-05-13; removal review by 2026-09-30 |
| `value_fabric/layer4/` | Shim only | Namespace facade; removal review by 2026-09-30 |
| `value_fabric/layer5/` | Shim only | Namespace facade; removal review by 2026-09-30 |
| `value_fabric/layer6/` | Shim only | Namespace facade; removal review by 2026-09-30 |
| `value_fabric/shared/` | Canonical | Shared runtime packages |

---

## High-Confidence Cleanup Candidates

### A. KEEP (Active Source/Docs/Configs/Evidence)

| Path | Reason |
|------|--------|
| `apps/web/` | Canonical frontend |
| `services/*/src/` | Canonical service implementations |
| `packages/shared/src/value_fabric/shared/` | Shared runtime packages |
| `docs/launch/` | Launch-readiness evidence |
| `docs/evidence/` | Evidence artifacts |
| `docs/readiness/` | Readiness documentation |
| `signoff-evidence/` | Launch signoff evidence |
| `artifacts/release/` | Release evidence packet |
| `contracts/` | API contracts |
| `k8s/` | Kubernetes manifests |
| `monitoring/` | Observability configs |
| `packs/` | Domain extension packs |
| `tests/` | Test suites |
| `.github/workflows/` | CI pipelines |
| `.agent/` | Active agent brain |

### B. MOVE / REORGANIZE

| Path | Current Purpose | Recommended Target |
|------|-----------------|-------------------|
| `docs/API_REFERENCE.md` | Human API summary | Merge into `docs/reference/api-overview.md` |
| `docs/DEPRECATIONS.md` | Redirect only | Merge into `docs/governance/compatibility-debt-registry.md` |
| `docs/ValuePack_Framework_v2.0.md` | Product framework | Move to `docs/product/value-packs.md` or `packs/README.md` |
| `docs/Providers.md` | Provider catalog | Move to `docs/reference/providers.md` |
| `docs/ENVIRONMENT.md` | Env var reference | Move to `docs/reference/environment.md` |
| `docs/VERSIONING.md` | Versioning policy | Move to `docs/reference/versioning.md` |
| `apps/web/docs/ROUTE_INVENTORY.md` | Frontend route inventory | Move to `docs/frontend/routes.md` |
| `apps/web/docs/route-layer-dependency-map.md` | Frontend-backend mapping | Move to `docs/frontend/route-layer-dependency-map.md` |
| `apps/web/docs/MOCK_AUTH_IMPLEMENTATION.md` | Mock auth guide | Move to `docs/frontend/mock-auth.md` |
| `apps/web/docs/async-boundary-inventory.md` | Async boundaries | Move to `docs/frontend/async-boundary-inventory.md` |

### C. ARCHIVE

| Path | Reason | Archive Target |
|------|--------|----------------|
| `docs/DOCUMENTATION_AUDIT_REPORT.md` | Superseded by docs/README.md | `docs/archive/2026-06-18/` |
| `docs/BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md` | Superseded by contracts/ | `docs/archive/2026-06-18/` |
| `docs/SECURITY_FIXES_SUMMARY.md` | Superseded by security/ | `docs/archive/2026-06-18/` |
| `docs/CHANGES.md` | Historical refactor log | `docs/archive/2026-06-18/` |
| `docs/ROADMAP.md` | 4650 lines, likely outdated | `docs/archive/2026-06-18/` |
| `docs/test-audit-2026-04-28.md` | Temporal audit | `docs/archive/2026-06-18/` |
| `docs/governance/auth-tenant-todo-audit-2026-05-12.md` | Temporal audit | `docs/archive/2026-06-18/` |
| `docs/governance/production-readiness-status-2026-05-14.md` | Temporal status | `docs/archive/2026-06-18/` |
| `docs/security/THREAT_MODEL.md` | Duplicate of threat-model.md | Delete |
| `docs/security/triage-notes-2026-04-14.md` | Temporal notes | `docs/archive/2026-06-18/` |
| `docs/testing/test_pass_rate_improvements_2026-05-06.md` | Temporal report | `docs/archive/2026-06-18/` |
| `apps/web/docs/UI_UX_AUDIT.md` | Temporal audit | `docs/archive/2026-06-18/` |
| `apps/web/docs/hook-coverage-qa-notes.md` | Temporal QA notes | `docs/archive/2026-06-18/` |
| `reports/autonomous-test-*.md` | Historical test reports | `docs/archive/evidence/reports/` |
| `artifacts/testing/*.md` | Historical test artifacts | `docs/archive/evidence/testing/` |
| `.devin/plans/` | Historical Devin plans | `docs/archive/devin/plans/` |
| `.devin/testing/` | Historical Devin test artifacts | `docs/archive/devin/testing/` |
| `.devin/testing-assurance/` | Historical Devin assurance | `docs/archive/devin/testing-assurance/` |
| `.devin/testing-artifacts/` | Historical Devin artifacts | `docs/archive/devin/testing-artifacts/` |

### D. DELETE (Generated/Local/Obvious)

| Path | Reason |
|------|--------|
| `node_modules/` | Dependency output, ignored |
| `apps/web/node_modules/` | Dependency output, ignored |
| `apps/web/dist/` | Build output, ignored |
| `apps/web/test-results/` | Test output, ignored |
| `apps/web/playwright-report/` | Test output, ignored |
| `apps/web/e2e-results/` | Test output, ignored |
| `apps/web/.tmp/` | Temp directory, ignored |
| `.pytest_cache/` | Cache, ignored |
| `.ruff_cache/` | Cache, ignored |
| `.hypothesis/` | Cache, ignored |
| `__pycache__/` | Python cache, ignored |
| `apps/web/__pycache__/` | Python cache, ignored |
| `services/*/.pytest_cache/` | Cache, ignored |
| `services/*/.mypy_cache/` | Cache, ignored |
| `services/*/.ruff_cache/` | Cache, ignored |
| `services/*/.hypothesis/` | Cache, ignored |
| `services/layer1-ingestion/test_layer1.db` | Local SQLite DB, ignored |
| `services/layer1-ingestion/UsersBBBFabric_4L.tmproot-aggregate-temppytest-cache/` | Cache artifact, ignored |
| `packages/platform-contract/UsersBBBFabric_4L.tmproot-aggregate-temppytest-cache/` | Cache artifact, ignored |
| `UsersBBBFabric_4L.tmproot-aggregate-temppytest-cache/` | Cache artifact, ignored |
| `apps/web/debug.log` | Local log, ignored |
| `.codex-vite-home.err.log` | Local log, ignored |
| `.codex-vite-home.log` | Local log, ignored |
| `.tmp-vite-3017.err.log` | Local log, ignored |
| `.tmp-vite-3017.out.log` | Local log, ignored |
| `pytest_collection.log` | Local pytest output |
| `skip_debug.txt` | Scratch file, ignored |
| `nul` | Windows artifact, ignored |
| `services/layer4-agents/collect_errors.txt` | L4 collection output, ignored |
| `services/layer4-agents/collect_out*.txt` | L4 collection output, ignored |
| `services/layer2-extraction/l2-out.log` | Local log, ignored |

### E. NEEDS OWNER DECISION

| Path | Reason |
|------|--------|
| `.claude/` | May be legacy harness config; overlapping with `.agent/` |
| `.agents/` | May be legacy skills; overlapping with `.agent/` |
| `.devin/` | Historical plans/artifacts; may still be referenced |
| `value_fabric/` | Compatibility shim; import validation needed before removal |
| `services/layer2-5-signal-refinery/` | Active per architecture; verify before touching |
| `services/layer7-billing/` | Active per architecture; verify before touching |
| `services/billing/` | Active per architecture; verify before touching |
| `signoff-evidence/` | High-value launch evidence; preserve unless duplicate |
| `production-readiness/` | Readiness artifacts; preserve unless duplicate |
| `docs/launch/` | Launch evidence; do not move without reference audit |
| `docs/evidence/` | Evidence artifacts; do not move without reference audit |
| `artifacts/release/` | Canonical release evidence packet location |

---

## Proposed Target Structure

```text
/
  apps/
    web/
  services/
    api/
    layer1-ingestion/
    layer2-extraction/
    layer2-5-signal-refinery/
    layer3-knowledge/
    layer4-agents/
    layer5-ground-truth/
    layer6-benchmarks/
    layer7-billing/
    billing/
  packages/
    shared/
    platform-contract/
    config/
    eslint-plugin-fabric-contracts/
  docs/
    architecture/
    product/
    launch/
    evidence/
    maintenance/
    archive/
      legacy/
      evidence/
      devin/
      reports/
    frontend/
    reference/
    governance/
    security/
    operations/
    testing/
  scripts/
    dev/
    ci/
    maintenance/
    archive/
    db/
    ops/
  tests/
    e2e/
    integration/
    contract/
    security/
    arch/
    ci/
    production_readiness/
  infra/
  k8s/
  monitoring/
  examples/
  fixtures/
  packs/
  contracts/
  .github/
  .agent/
  archive/                    # eventually moved to docs/archive/legacy/root-archive/
  artifacts/                  # generated/evidence; keep canonical release outputs
  reports/                    # ideally reduced to generated diagnostics or removed
  generated/                  # ignored generated outputs
```

---

## File-by-File Recommendation Table

See tables above for detailed recommendations.

---

## Directory-by-Directory Recommendation Table

See tables above for detailed recommendations.

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Accidentally deleting launch evidence | Do not delete `docs/launch/`, `docs/evidence/`, `docs/readiness/`, `signoff-evidence/`, `artifacts/release/` without owner approval |
| Breaking imports by removing shims | Keep `value_fabric/` until import topology tests pass without it |
| Removing active service folders | Keep `services/layer2-5-signal-refinery/`, `services/layer7-billing/`, `services/billing/` until compose/import tests confirm otherwise |
| Moving docs breaks links | Run `rg` for old paths and `pytest tests/docs/` after moves |
| Deleting `.env` removes local setup | Only delete local `.env`; keep `.env.example`, `.env.dev.example`, templates |
| Deleting `.claude/` or `.agents/` breaks harness | Owner decision required before touching |
| Moving `archive/` breaks historical links | Use `git mv`, update `docs/archive/INDEX.md`, validate links |
| Removing reports loses evidence | Archive reports under `docs/archive/evidence/` with README before deleting |

---

## Validation Commands

### Before any deletion:
```bash
git status --short
git ls-files
```

### After Phase 1 cleanup:
```bash
git status --short
git diff --stat
```

### After documentation moves:
```bash
rg "<old path or old filename>" . --glob '!node_modules/**' --glob '!dist/**' --glob '!artifacts/**'
python -m pytest tests/docs/
```

### After any changes:
```bash
python scripts/ci/check_reports_evidence_policy.py
python scripts/ci/structural_preflight.py --strict
python scripts/ci/check_legacy_debt.py --baseline config/ci/legacy_debt_baseline.json --approvals config/ci/legacy_debt_approvals.json --config config/ci/legacy_debt_config.json
```

---

## Recommended Implementation Order

1. **Phase 1 — Safe generated/local cleanup** (this PR)
   - Delete obvious ignored generated/cache/temp files
   - Update `.gitignore` if needed
   - Do not touch source, docs, tests, launch evidence, or configs

2. **Phase 2 — Documentation organization**
   - Create `docs/maintenance/` and this audit report
   - Move/rename docs per reorganization table
   - Add redirects or archive notices

3. **Phase 3 — Script/tooling cleanup**
   - Archive stale one-off scripts
   - Update documentation references

4. **Phase 4 — Test/evidence cleanup**
   - Preserve canonical evidence
   - Archive duplicate/superseded evidence
   - Do not delete launch evidence unless clearly duplicated

5. **Phase 5 — Source tree cleanup**
   - Identify dead code, duplicate modules, obsolete routes
   - Do not remove source code without tests and import validation

---

## Phase 1 Implementation Log

| Timestamp | Action | Status |
|-----------|--------|--------|
| 2026-06-18T00:00:00Z | Created `docs/maintenance/` directory | ✅ Done |
| 2026-06-18T00:00:01Z | Created this audit report | ✅ Done |
| 2026-06-18T00:00:02Z | Awaiting approval for Phase 1 cleanup | ⏳ Pending |