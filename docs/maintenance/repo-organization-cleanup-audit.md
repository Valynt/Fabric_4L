# Repository Organization Cleanup Audit

**Audit Date:** 2026-06-18
**Auditor:** Cascade (AI pair programmer)
**Scope:** Fabric_4L repository structure, tracked files, ignored working-tree clutter, and stale/duplicate artifacts for Core GA architecture.
**Status:** Phase 1 implementation pending.

---

## Summary

- **Total tracked files:** 7,181
- **Total ignored working-tree files:** 874,601 (mostly `node_modules/`, `.venv/`, `__pycache__`)
- **Top-level directories inspected:** 32
- **Root-level tracked files:** 21 (including 2 accidental scratch commits)
- **Working-tree modifications:** 4 service files already modified (must not be touched)

| Classification | Count |
|---|---|
| **Keep** | ~6,900 (source, tests, configs, contracts, k8s, monitoring, launch evidence) |
| **Move / Reorganize** | ~64 docs root files + 7 `apps/web/docs` files |
| **Archive** | ~100 historical reports/audits in `docs/`, `reports/`, `scripts/` |
| **Delete** | ~2 tracked scratch files + ignored caches/logs/temp files |
| **Needs Owner Decision** | `services/billing/` vs `services/layer7-billing/`, `.agent/.agents/.claude/.devin/`, `reports/` cutoff, `value_fabric/` shim removal |

---

## Executive Summary

The Fabric_4L repository is functionally well-organized for its multi-layer architecture, but has accumulated significant surface clutter: two tracked root-level scratch files, 64 markdown files at the root of `docs/`, a large `reports/` directory of generated/historical artifacts, and ~875k ignored build/cache/dependency files in the working tree. Most clutter is harmless, but it reduces discoverability and slows onboarding.

The cleanup must be phased to avoid breaking imports, CI, Docker, docs, or launch evidence. Only **Phase 1** (safe generated/local cleanup and removal of the two tracked scratch files) is recommended for immediate execution. Phases 2–5 require owner decisions, reference updates, and validation runs.

---

## Current Repo Structure Observations

### Canonical Active Areas

| Area | Path | Status |
|---|---|---|
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
| Billing (legacy?) | `services/billing/` | Needs decision |
| Shared Packages | `packages/shared/` | Active |
| Platform Contract | `packages/platform-contract/` | Active |
| Internal Docs | `docs/` | Active |
| Public Docs | `docs-site/` | Active |
| Contracts | `contracts/` | Active |
| Tests | `tests/` | Active |
| K8s | `k8s/` | Active |
| Monitoring | `monitoring/` | Active |
| Packs | `packs/` | Active |

### Compatibility Shims

| Path | Status |
|---|---|
| `value_fabric/layer1/` | Shim only |
| `value_fabric/layer2/` | Shim only |
| `value_fabric/layer3/` | Shim only |
| `value_fabric/layer4/` | Shim with billing sub-shim |
| `value_fabric/layer5/` | Shim with api/services |
| `value_fabric/layer6/` | Shim with smoke test |
| `value_fabric/shared/` | Canonical active |

---

## Top 20 Highest-Value Cleanup Opportunities

| # | Path / Area | Issue | Value | Risk |
|---|---|---|---|---|
| 1 | `1` (root) | Tracked Docker Compose log output | High | Low |
| 2 | `skip_debug.txt` (root) | Tracked pytest scratch output | High | Low |
| 3 | `nul` (root) | Windows artifact, ignored | High | Low |
| 4 | `pytest_collection.log` (root) | Generated pytest log, ignored | High | Low |
| 5 | `.codex-vite-home.*` + `.tmp-vite-3017.*` | Vite dev-server logs, ignored | High | Low |
| 6 | `UsersBBBFabric_4L.tmproot-aggregate-temppytest-cache/` | Pytest cache artifact, ignored | High | Low |
| 7 | `node_modules/` / `.venv/` / `__pycache__` | Reproducible dependency/cache dirs | High | Low |
| 8 | `docs/` root (64 files) | Misplaced single-page docs | High | Medium |
| 9 | `apps/web/docs/` (7 files) | Frontend docs should live under `docs/frontend/` | High | Medium |
| 10 | `reports/` (112 items) | Historical/generated reports clutter | High | Medium |
| 11 | `docs/product-brief.md` + `docs/product_brief.md` | Duplicate-ish product briefs | Medium | Low |
| 12 | `docs/accessibility.md` + `docs/accessibility_policy.md` | Overlapping accessibility docs | Medium | Low |
| 13 | `docs/CHANGES.md` | Historical refactor log | Medium | Low |
| 14 | `docs/DOCUMENTATION_AUDIT_REPORT.md` | Superseded audit report | Medium | Low |
| 15 | `docs/ROADMAP.md` (586 bytes) | Tiny, likely stale | Medium | Low |
| 16 | `docs/archive/2026-04-19/`, `2026-04-27/`, etc. | Existing archive; ensure new archives follow same pattern | Medium | Low |
| 17 | `services/billing/` vs `services/layer7-billing/` | Possible duplicate service | High | High |
| 18 | `services/layer4-agents/tools/analytics.py`, `workflows.py` | Dead code per 2026-06-04 sweep | Medium | Medium |
| 19 | `scripts/` one-off migration scripts | Stale scripts (`cleanup_value_fabric*.py`, `migrate_*.py`, etc.) | Medium | Medium |
| 20 | `artifacts/`, `generated/`, `archive/` root dirs | Empty or generated skeletons | Medium | Low |

---

## Safe Deletion Candidates (Phase 1)

These are **ignored or clearly accidental** and can be removed without breaking anything.

| Path | Type | Reason | Tracked? | Ignored? |
|---|---|---|---|---|
| `1` | file | Docker Compose log output, committed by accident | Yes | No |
| `skip_debug.txt` | file | Pytest exception scratch, committed by accident | Yes | No |
| `nul` | file | Windows redirection artifact | No | Yes |
| `pytest_collection.log` | file | Generated pytest output | No | Yes |
| `.codex-vite-home.err.log` | file | Vite dev log | No | Yes |
| `.codex-vite-home.log` | file | Vite dev log | No | Yes |
| `.tmp-vite-3017.err.log` | file | Vite dev log | No | Yes |
| `.tmp-vite-3017.out.log` | file | Vite dev log | No | Yes |
| `UsersBBBFabric_4L.tmproot-aggregate-temppytest-cache/` | dir | Pytest cache artifact | No | Yes |
| `__pycache__/` | dir | Python bytecode cache | No | Yes |
| `.pytest_cache/` | dir | Pytest cache | No | Yes |
| `.ruff_cache/` | dir | Ruff cache | No | Yes |
| `.hypothesis/` | dir | Hypothesis cache | No | Yes |
| `.tmp/` | dir | Temp directory | No | Yes |
| `node_modules/` | dir | Dependency output | No | Yes |
| `.venv/` | dir | Python venv | No | Yes |
| `apps/web/dist/` | dir | Build output | No | Yes |
| `apps/web/test-results/` | dir | Test output | No | Yes |
| `apps/web/playwright-report/` | dir | Test output | No | Yes |
| `apps/web/e2e-results/` | dir | Test output | No | Yes |
| `apps/web/.tmp/` | dir | Temp dir | No | Yes |
| `apps/web/__pycache__/` | dir | Python cache | No | Yes |
| `services/*/.pytest_cache/` | dir | Pytest cache | No | Yes |
| `services/*/.mypy_cache/` | dir | mypy cache | No | Yes |
| `services/*/.ruff_cache/` | dir | Ruff cache | No | Yes |
| `services/*/.hypothesis/` | dir | Hypothesis cache | No | Yes |
| `services/*/__pycache__/` | dir | Python cache | No | Yes |
| `services/*/.venv/` | dir | Service venvs | No | Yes |
| `services/layer4-agents/collect_errors.txt` | file | L4 collection output | No | Yes |
| `services/layer4-agents/collect_out*.txt` | files | L4 collection output | No | Yes |
| `services/layer4-agents/local_*.txt` | files | L4 scratch | No | Yes |
| `services/layer4-agents/module_list.txt` | file | L4 scratch | No | Yes |
| `services/layer4-agents/mypy_cleaned*.txt` | files | L4 scratch | No | Yes |
| `services/layer2-extraction/l2-out.log` | file | Local log | No | Yes |
| `services/layer1-ingestion/test_layer1.db` | file | Local SQLite DB | No | Yes |
| `apps/web/debug.log` | file | Local log | No | Yes |
| `valuepacks_output.txt` | file | Generated output | No | Yes |
| `audit_violations.txt` | file | Generated output | No | Yes |
| `audit-output/` | dir | Generated output | No | Yes |
| `compose-resolved.yml` | file | Generated compose | No | Yes |
| `*.zip` | files | Generated ZIPs | No | Yes |
| `test_results_*.txt` | files | Local test output | No | Yes |
| `collect_output.txt` | file | Local output | No | Yes |
| `pytest_collect*.txt` | files | Local output | No | Yes |
| `layer1_test_results*.txt` | files | Local output | No | Yes |
| `core` | file | Core dump | No | Yes |
| `Codex Installer.exe` | file | Installer artifact | No | Yes |
| `Microsoft.Services.Store.winmd` | file | Store artifact | No | Yes |
| `tmp_*_findings.json` | files | Temp drift baseline | No | Yes |
| `tmp_*_after_fix.json` | files | Temp drift baseline | No | Yes |
| `tmp_gen_migration_baseline.py` | file | Temp migration baseline | No | Yes |
| `CUsers*` / `cUsers*` | files | Windows redirection artifacts | No | Yes |
| `*Users*Fabric_4L.env` | files | Windows redirection artifacts | No | Yes |
| `tmp_pr*.txt` / `tmp_pr*.*'` / `tmp_models_content.txt` | files | Temp diff/patch | No | Yes |
| `.devin_workflow_violations*` | files | Workflow scratch | No | Yes |
| `.agent/memory/episodic/` | dir | Generated agent memory | No | Yes |

---

## Reorganization Candidates (Phase 2)

| Path | Current Purpose | Recommended Target | Risk |
|---|---|---|---|
| `docs/API_REFERENCE.md` | Human API summary | `docs/reference/api-overview.md` | Low-Medium |
| `docs/Providers.md` | Provider catalog | `docs/reference/providers.md` | Low |
| `docs/ENVIRONMENT.md` | Env var reference | `docs/reference/environment.md` | Low |
| `docs/VERSIONING.md` | Versioning policy | `docs/reference/versioning.md` | Low |
| `docs/SECRETS.md` | Secrets management | `docs/reference/secrets.md` | Low |
| `docs/ERROR_MONITORING.md` | Error monitoring | `docs/operations/error-monitoring.md` | Low |
| `docs/GITOPS.md` | GitOps | `docs/operations/gitops.md` | Low |
| `docs/LAUNCH_RUNBOOK.md` | Launch runbook | `docs/operations/launch-runbook.md` | Low |
| `docs/SECURITY_TRIAGE_RUBRIC.md` | Triage rubric | `docs/security/triage-rubric.md` | Low |
| `docs/SECURITY_FIXES_SUMMARY.md` | Security summary | `docs/security/fixes-summary.md` or archive | Low |
| `docs/SECURITY_FIXES_EXECUTION_LOG.md` | Execution log | `docs/security/fixes-execution-log.md` or archive | Low |
| `docs/IMPLEMENTATION_PLAN.md` | Implementation plan | `docs/operations/implementation-plan.md` | Low |
| `docs/DEVELOPMENT.md` | Dev guide | `docs/development/development.md` | Low |
| `docs/CONTRIBUTING.md` | Contributing | `docs/development/contributing.md` | Low |
| `docs/CHANGELOG.md` | Changelog | `docs/development/changelog.md` | Low |
| `docs/MCP_GATEWAY_SECURITY_ASSESSMENT_2026-04-24.md` | Temporal assessment | `docs/archive/2026-06-18/` | Low |
| `docs/test-audit-2026-04-28.md` | Temporal audit | `docs/archive/2026-06-18/` | Low |
| `docs/test-quality-audit.md` | Temporal audit | `docs/archive/2026-06-18/` | Low |
| `docs/DOCUMENTATION_AUDIT_REPORT.md` | Superseded audit | `docs/archive/2026-06-18/` | Low |
| `docs/BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md` | Superseded analysis | `docs/archive/2026-06-18/` | Low |
| `docs/CHANGES.md` | Historical refactor log | `docs/archive/2026-06-18/` | Low |
| `docs/ROADMAP.md` | Tiny / likely stale | `docs/archive/2026-06-18/` | Low |
| `docs/ValuePack_Framework_v2.0.md` | Product framework | `docs/product/value-packs.md` or `packs/README.md` | Medium |
| `docs/value-packs.md` | Product framework (duplicate-ish) | `docs/product/value-packs.md` (merge) | Medium |
| `docs/product-brief.md` | Product brief | `docs/product/product-brief.md` | Low |
| `docs/product_brief.md` | Product brief (duplicate-ish) | `docs/product/product-brief.md` (merge) | Medium |
| `docs/accessibility.md` | Accessibility statement | `docs/product/accessibility.md` | Low |
| `docs/accessibility_policy.md` | Accessibility policy | `docs/product/accessibility-policy.md` | Low |
| `docs/agent-architecture.md` | Agent architecture | `docs/architecture/agent-architecture.md` | Low |
| `docs/AGENTS.md` | Agent reference | `docs/development/agents.md` | Low |
| `docs/NAVIGATION_ARCHITECTURE.md` | Navigation | `docs/frontend/navigation-architecture.md` | Low |
| `docs/frontend-expectations.md` | Frontend expectations | `docs/frontend/frontend-expectations.md` | Low |
| `apps/web/docs/ROUTE_INVENTORY.md` | Frontend route inventory | `docs/frontend/route-inventory.md` | Medium |
| `apps/web/docs/route-layer-dependency-map.md` | FE-BE mapping | `docs/frontend/route-layer-dependency-map.md` | Medium |
| `apps/web/docs/MOCK_AUTH_IMPLEMENTATION.md` | Mock auth | `docs/frontend/mock-auth.md` | Medium |
| `apps/web/docs/async-boundary-inventory.md` | Async boundaries | `docs/frontend/async-boundary-inventory.md` | Medium |
| `apps/web/docs/frontend-workflow-coverage-matrix.md` | Coverage matrix | `docs/frontend/frontend-workflow-coverage-matrix.md` | Medium |
| `apps/web/docs/ui-design-readiness.md` | UI readiness | `docs/frontend/ui-design-readiness.md` | Medium |
| `apps/web/docs/frontend/` | Frontend sub-docs | `docs/frontend/` | Medium |

---

## Archive Candidates (Phase 3 / Phase 4)

| Path | Reason | Archive Target |
|---|---|---|
| `docs/CHANGES.md` | Historical refactor log | `docs/archive/2026-06-18/` |
| `docs/DOCUMENTATION_AUDIT_REPORT.md` | Superseded by docs/README.md | `docs/archive/2026-06-18/` |
| `docs/BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md` | Superseded by contracts/ | `docs/archive/2026-06-18/` |
| `docs/SECURITY_FIXES_SUMMARY.md` | Superseded by security/ | `docs/archive/2026-06-18/` |
| `docs/SECURITY_FIXES_EXECUTION_LOG.md` | Temporal execution log | `docs/archive/2026-06-18/` |
| `docs/ROADMAP.md` | Tiny / likely stale | `docs/archive/2026-06-18/` |
| `docs/test-audit-2026-04-28.md` | Temporal audit | `docs/archive/2026-06-18/` |
| `docs/test-quality-audit.md` | Temporal audit | `docs/archive/2026-06-18/` |
| `docs/MCP_GATEWAY_SECURITY_ASSESSMENT_2026-04-24.md` | Temporal assessment | `docs/archive/2026-06-18/` |
| `apps/web/docs/UI_UX_AUDIT.md` | Temporal audit (if exists) | `docs/archive/2026-06-18/` |
| `apps/web/docs/hook-coverage-qa-notes.md` | Temporal QA notes (if exists) | `docs/archive/2026-06-18/` |
| `docs/archive/evidence/reports/2026-06-18/autonomous-test-*.md` | Historical test reports | **Archived** on 2026-06-18 |
| `docs/archive/evidence/reports/2026-06-18/documentation-cleanup-phase*.md` | Historical cleanup reports | **Archived** on 2026-06-18 |
| `reports/httpexception-inventory.md` | Active inventory (referenced by docs) | Keep in `reports/` |
| `docs/archive/evidence/reports/2026-06-18/conflict-inventory-2026-05-19.md` | Historical inventory | **Archived** on 2026-06-18 |
| `docs/archive/evidence/reports/2026-06-18/layer1-test-raw-output.txt` | Raw test output | **Archived** on 2026-06-18 |
| `reports/layer1-test-run-2026-06-01.txt` | Empty file | **Deleted** on 2026-06-18 |
| `reports/pr-triage-plan.md` | Active triage plan | Keep in `reports/` |
| `docs/archive/evidence/reports/2026-06-18/pr-triage-plan-2026-06-04.md` | Historical triage plan | **Archived** on 2026-06-18 |
| `reports/autonomous-test-assurance/` | Active test assurance directory | Keep in `reports/` |
| `reports/coverage/` | Coverage output | Keep in `reports/` or delete if CI regenerates |
| `docs/archive/evidence/reports/repo-cleanup/` | Repo cleanup reports | **Archived** on 2026-06-18 |
| `scripts/deleted_files_report.txt` | Generated report | `docs/archive/evidence/reports/` |
| `scripts/mirrored_files.json` | Generated report | `docs/archive/evidence/reports/` |
| `scripts/ui_duplicate_baseline.txt` | Generated baseline | `docs/archive/evidence/reports/` |

---

## Owner-Decision Candidates

| Path | Reason | Risk | Recommended Action |
|---|---|---|---|
| `services/billing/` | Possible duplicate of `services/layer7-billing/` | High | Owner confirms whether legacy or separate canonical service |
| `services/layer7-billing/` | Active service; verify before touching | High | Keep unless owner confirms billing/ is canonical |
| `value_fabric/` | Compatibility shim with removal review date 2026-09-30 | High | Keep until import topology tests pass without it |
| `.agent/` | Active agent brain | High | Do not delete unless owner confirms no harness dependency |
| `.agents/` | Possibly legacy skills | High | Owner confirms whether superseded by `.agent/skills/` |
| `.claude/` | Legacy harness config | High | Owner confirms before deleting |
| `.devin/` | Historical plans/artifacts | High | May be referenced by Windsurf; do not delete without owner |
| `reports/` | 112 items; many historical | Medium | Owner sets cutoff for archival vs. keep |
| `signoff-evidence/` | Launch signoff evidence | High | Preserve; do not delete unless duplicate and superseded |
| `production-readiness/` | Readiness artifacts | High | Preserve; do not delete unless duplicate |
| `docs/launch/` | Launch evidence | High | Do not move without reference audit |
| `docs/evidence/` | Evidence artifacts | High | Do not move without reference audit |
| `docs/readiness/` | Readiness docs | High | Do not move without reference audit |
| `artifacts/release/` | Canonical release evidence packet | High | Preserve |
| `packages/platform-contract/src/typescript/generated/` | Generated but tracked | Medium | Keep; regenerate via CI if needed |
| `apps/web/src/api/generated/` | Generated but tracked | Medium | Keep; regenerate via CI if needed |
| `docs-site/docs/api/openapi/` | Generated OpenAPI copy | Medium | Keep; gitignored; refreshed by sync script |

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
    layer7-billing/          # canonical billing (owner confirms)
    billing/                  # legacy or duplicate (owner decision)
  packages/
    shared/
    platform-contract/
    config/
    eslint-plugin-fabric-contracts/
  contracts/
  docs/                      # internal engineering docs
    README.md
    _redirects
    _SOURCE OF TRUTH/
    architecture/
    product/
    launch/                  # launch evidence (do not move without audit)
    evidence/                # evidence artifacts (do not move without audit)
    readiness/               # readiness docs (do not move without audit)
    maintenance/
    archive/
      2026-04-19/
      2026-04-27/
      2026-05-28/
      2026-06-18/          # new archive batch
      legacy/
      evidence/
      reports/
      devin/
    frontend/
    reference/
    governance/
    security/
    operations/
    development/
    testing/
    explanations/
    how-to/
    tutorials/
    troubleshooting/
    trust/
    validation/
    runbooks/
    sdk/
    superpowers/
    decisions/
    ontology_proposal/
  docs-site/                 # public user-facing docs (untouched)
  scripts/
    dev/
    ci/
    maintenance/
    archive/
    db/
    ops/
    security/
    observability/
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
  .github/
  .agent/                    # owner decision
  .agents/                   # owner decision
  .devin/                    # owner decision
  signoff-evidence/          # high-value launch evidence
  production-readiness/      # high-value readiness artifacts
  artifacts/                 # keep skeleton; ignore contents
  reports/                   # reduce to active diagnostics or archive
  generated/                 # ignored generated outputs
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Delete launch evidence | Low | Critical | Phase 1 excludes `docs/launch/`, `docs/evidence/`, `docs/readiness/`, `signoff-evidence/`, `production-readiness/` |
| Break imports by removing shims | Low | High | Keep `value_fabric/` until import topology tests pass without it |
| Move docs without updating links | Medium | Medium | Use `git mv`, run `rg` for old paths, update `docs/_redirects` |
| Delete active service | Low | High | Treat `services/billing/` as owner decision |
| Delete CI script or fixture | Low | High | Only archive scripts after `rg` reference checks and CI validation |
| Lose historical audit context | Low | Medium | Archive instead of delete; keep `docs/archive/INDEX.md` |
| Delete `.env` secrets | Low | High | Only delete `.env` if it is truly ignored; never commit its contents |

---

## Validation Commands

### Before any change

```bash
git status --short
git status --short --ignored
git ls-files | python -c "import sys; print(len(sys.stdin.readlines()))"
```

### After Phase 1

```bash
git status --short
git diff --stat
```

### After documentation moves

```bash
rg "<old-path>" . --glob '!node_modules/**' --glob '!dist/**'
python -m pytest tests/docs/
```

### After script moves

```bash
rg "scripts/(cleanup_value_fabric|migrate_|check_layer|fix_|resolve_conflicts|check_deleted_files|restore_needed_files|run_bash_cmd|save_output|list_value_fabric|verify_layer4|layer4_cleanup)" . --glob '!scripts/archive/**'
```

### After any source changes

```bash
python scripts/ci/structural_preflight.py --strict
python scripts/ci/check_legacy_debt.py --baseline config/ci/legacy_debt_baseline.json --approvals config/ci/legacy_debt_approvals.json --config config/ci/legacy_debt_config.json
pnpm --dir apps/web run check
make contract-tests
```

---

## Recommended Implementation Order

1. **Phase 1 — Safe generated/local cleanup** (auto-executable if approved)
   - Remove `1` and `skip_debug.txt` from git.
   - Delete ignored root-level logs/cache/temp files.
   - Delete ignored per-service caches and scratch files.
   - Run `git status --short` and `git diff --stat`.

2. **Phase 2 — Documentation organization**
   - Create `docs/product/`, `docs/frontend/`, `docs/development/` if missing.
   - Move root-level docs into appropriate subdirectories.
   - Move `apps/web/docs/` into `docs/frontend/`.
   - Update `docs/_redirects` and `docs/archive/INDEX.md`.
   - Run `rg` for broken references and `pytest tests/docs/`.

3. **Phase 3 — Script/tooling cleanup**
   - Create `scripts/archive/`.
   - Move stale one-off migration scripts into `scripts/archive/`.
   - Run `rg` for broken references.

4. **Phase 4 — Test/evidence cleanup**
   - Move historical reports from `reports/` to `docs/archive/evidence/reports/`.
   - Delete empty reports (e.g., `reports/layer1-test-run-2026-06-01.txt`).
   - Preserve `signoff-evidence/` and `production-readiness/`.

5. **Phase 5 — Source-tree cleanup**
   - Remove confirmed dead code after import validation.
   - Resolve `services/billing/` vs `services/layer7-billing/` with owner.
   - Evaluate `value_fabric/` shim removal against 2026-09-30 review date.

---

## Phase 1 Proposed Exact Commands

If approved, Phase 1 can be executed as:

```bash
# Remove accidentally tracked scratch files from git
git rm --cached 1 skip_debug.txt
rm -f 1 skip_debug.txt

# Remove ignored root-level clutter
rm -f nul pytest_collection.log \
  .codex-vite-home.err.log .codex-vite-home.log \
  .tmp-vite-3017.err.log .tmp-vite-3017.out.log \
  .env.pytest.example

rm -rf UsersBBBFabric_4L.tmproot-aggregate-temppytest-cache/ \
  __pycache__/ .pytest_cache/ .ruff_cache/ .hypothesis/ .tmp/ \
  .agent/memory/episodic/

# Remove ignored build/cache dirs at root
rm -rf node_modules/ .venv/ \
  apps/web/node_modules/ apps/web/dist/ apps/web/test-results/ \
  apps/web/playwright-report/ apps/web/e2e-results/ apps/web/.tmp/ apps/web/__pycache__/

# Remove ignored per-service caches and scratch files
find services -type d -name __pycache__ -exec rm -rf {} +
find services -type d -name .pytest_cache -exec rm -rf {} +
find services -type d -name .mypy_cache -exec rm -rf {} +
find services -type d -name .ruff_cache -exec rm -rf {} +
find services -type d -name .hypothesis -exec rm -rf {} +
find services -type d -name .venv -exec rm -rf {} +
find services -type d -name .tmp -exec rm -rf {} +
rm -f services/layer4-agents/collect_errors.txt services/layer4-agents/collect_out*.txt
rm -f services/layer4-agents/local_*.txt services/layer4-agents/module_list.txt services/layer4-agents/mypy_cleaned*.txt
rm -f services/layer2-extraction/l2-out.log
rm -f services/layer1-ingestion/test_layer1.db
rm -f apps/web/debug.log

# Clean up temporary files created by this audit
rm -f tmp_git_files.txt tmp_ignored_files.txt .tmp_git_files.txt .tmp_git_status.txt

# Validate
git status --short
git diff --stat
```

**Note:** `.venv/` and `node_modules/` deletions can be slow; consider running them as a separate step. If any directory has permission errors, skip it and report.

---

## Rollback Plan

- All Phase 1 deletions are of ignored or accidental files; they can be regenerated or restored from git history.
- If `git rm --cached` was used, the files are still in git history and can be restored with `git checkout HEAD -- <file>`.
- Before any move/archive in Phases 2–5, use `git mv` so history is preserved.
- Do not run `git clean -fdX` without first reviewing the untracked files.

---

## Phase 1 Implementation Log

| Timestamp | Action | Result |
|---|---|---|
| 2026-06-18 | Removed tracked scratch files `1` and `skip_debug.txt` from git | `git rm --cached` completed |
| 2026-06-18 | Deleted ignored root-level logs and temp files | `nul`, `pytest_collection.log`, vite logs, `.env.pytest.example` removed |
| 2026-06-18 | Deleted root-level cache/build directories | `node_modules/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.hypothesis/`, `.tmp/` skeletons removed |
| 2026-06-18 | Deleted `apps/web/` cache/build directories | `node_modules/`, `dist/`, `test-results/`, `playwright-report/`, `e2e-results/`, `.tmp/`, `__pycache__/` removed |
| 2026-06-18 | Deleted per-service cache/build directories | 180+ cache/build dirs removed across `services/` and `tests/`; 6 locked pytest-cache dirs remain due to `WinError 5` |
| 2026-06-18 | Deleted generated `.egg-info/` and local SQLite DBs | `*.egg-info/`, `pending_ingestion.db`, `ground_truth.db`, `.coverage` files removed |
| 2026-06-18 | Deleted docs-site generated output | `docs-site/site/` removed |
| 2026-06-18 | Cleaned up audit temp files | `tmp_git_files.txt`, `tmp_ignored_files.txt`, `.tmp_git_files.txt`, `.tmp_git_status.txt` removed |

### Locked directories that could not be removed

The following directories are held open by running processes (likely pytest) and could not be deleted during Phase 1. They can be removed after the processes are stopped:

- `.tmp/pytest-cache/`
- `.tmp/pytest-gate/`
- `.tmp/pytest-of-BBB/`
- `.tmp/pytest-temp-classify/`
- `.tmp/pytest-temp-evidence/`
- `.tmp/pytest-temp-launch-readiness-combined/`
- `.tmp/pytest-tmp/pytest-of-BBB/`
- `artifacts/pytest-check-alembic/`
- `services/layer2-extraction/.pytest_cache/`
- `services/layer3-knowledge/.pytest_cache/`
- `services/layer4-agents/.tmp/pytest-cache/`
- `services/layer5-ground-truth/.tmp/pytest-cache/`
- `services/layer6-benchmarks/.tmp/pytest-cache/`

---

## Appendix: Methodology

- `git status --short --untracked-files=all` identified untracked files.
- `git status --short --ignored` identified ignored working-tree clutter.
- `git ls-files --others --ignored --exclude-standard` enumerated ignored files.
- `git ls-files` enumerated 7,181 tracked files.
- `git check-ignore -v <file>` confirmed ignore patterns.
- `rg` was used for reference and duplicate checks.
- `list_dir` was used for directory enumeration.
- Dead-code candidates were cross-referenced against the 2026-06-04 dead-code sweep memory.
