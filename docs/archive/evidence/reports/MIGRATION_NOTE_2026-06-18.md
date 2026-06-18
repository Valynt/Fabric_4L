# Reports Archive Migration Note

**Date:** 2026-06-18
**Action:** Phase 4 of repository cleanup audit — archive historical reports from `reports/` to `docs/archive/evidence/reports/2026-06-18/`.

## Files Moved

| Original Path | New Path |
|---|---|
| `reports/advisory-production-audit-verification-2026-06-01.md` | `docs/archive/evidence/reports/2026-06-18/advisory-production-audit-verification-2026-06-01.md` |
| `reports/api-contract-stability-audit.md` | `docs/archive/evidence/reports/2026-06-18/api-contract-stability-audit.md` |
| `reports/auth-jwks-remediation-blocker-fixes.md` | `docs/archive/evidence/reports/2026-06-18/auth-jwks-remediation-blocker-fixes.md` |
| `reports/auth-jwks-remediation-security-audit.md` | `docs/archive/evidence/reports/2026-06-18/auth-jwks-remediation-security-audit.md` |
| `reports/auth-jwks-test-failure-report.md` | `docs/archive/evidence/reports/2026-06-18/auth-jwks-test-failure-report.md` |
| `reports/authentication-security-audit-2026-05-27.md` | `docs/archive/evidence/reports/2026-06-18/authentication-security-audit-2026-05-27.md` |
| `reports/autonomous-test-assurance-execution-report.md` | `docs/archive/evidence/reports/2026-06-18/autonomous-test-assurance-execution-report.md` |
| `reports/autonomous-test-assurance-report-2026-05-25.md` | `docs/archive/evidence/reports/2026-06-18/autonomous-test-assurance-report-2026-05-25.md` |
| `reports/autonomous-test-assurance-report-2026-05-30.md` | `docs/archive/evidence/reports/2026-06-18/autonomous-test-assurance-report-2026-05-30.md` |
| `reports/circuit-breaker-inventory.md` | `docs/archive/evidence/reports/2026-06-18/circuit-breaker-inventory.md` |
| `reports/comprehensive_system_audit_report.md` | `docs/archive/evidence/reports/2026-06-18/comprehensive_system_audit_report.md` |
| `reports/conflict-inventory-2026-05-19.md` | `docs/archive/evidence/reports/2026-06-18/conflict-inventory-2026-05-19.md` |
| `reports/documentation-cleanup-phase1-inventory.md` | `docs/archive/evidence/reports/2026-06-18/documentation-cleanup-phase1-inventory.md` |
| `reports/documentation-cleanup-phase2-valuation.md` | `docs/archive/evidence/reports/2026-06-18/documentation-cleanup-phase2-valuation.md` |
| `reports/documentation-cleanup-phase3-consolidation.md` | `docs/archive/evidence/reports/2026-06-18/documentation-cleanup-phase3-consolidation.md` |
| `reports/documentation-cleanup-phase4-decision.md` | `docs/archive/evidence/reports/2026-06-18/documentation-cleanup-phase4-decision.md` |
| `reports/documentation-cleanup-phase5-readme.md` | `docs/archive/evidence/reports/2026-06-18/documentation-cleanup-phase5-readme.md` |
| `reports/drills/` | `docs/archive/evidence/reports/2026-06-18/drills/` |
| `reports/elevate-to-9-migration-report.md` | `docs/archive/evidence/reports/2026-06-18/elevate-to-9-migration-report.md` |
| `reports/enterprise-release-blockers-2026-06-01.md` | `docs/archive/evidence/reports/2026-06-18/enterprise-release-blockers-2026-06-01.md` |
| `reports/infra_secret_mapping.md` | `docs/archive/evidence/reports/2026-06-18/infra_secret_mapping.md` |
| `reports/layer1-test-failure-analysis.md` | `docs/archive/evidence/reports/2026-06-18/layer1-test-failure-analysis.md` |
| `reports/layer1-test-raw-output.txt` | `docs/archive/evidence/reports/2026-06-18/layer1-test-raw-output.txt` |
| `reports/layer1-test-stabilization-2026-06-01.md` | `docs/archive/evidence/reports/2026-06-18/layer1-test-stabilization-2026-06-01.md` |
| `reports/p0-blockers-handoff-2026-05-31.md` | `docs/archive/evidence/reports/2026-06-18/p0-blockers-handoff-2026-05-31.md` |
| `reports/p0-blockers-local-evidence-2026-05-31.md` | `docs/archive/evidence/reports/2026-06-18/p0-blockers-local-evidence-2026-05-31.md` |
| `reports/p0-staging-environment-preflight-2026-05-31.md` | `docs/archive/evidence/reports/2026-06-18/p0-staging-environment-preflight-2026-05-31.md` |
| `reports/p0-validation-report.md` | `docs/archive/evidence/reports/2026-06-18/p0-validation-report.md` |
| `reports/PR-A-frontend-audit-cleanup.md` | `docs/archive/evidence/reports/2026-06-18/PR-A-frontend-audit-cleanup.md` |
| `reports/pr-bug-triage-20260523.json` | `docs/archive/evidence/reports/2026-06-18/pr-bug-triage-20260523.json` |
| `reports/pr-triage-plan-2026-06-04.md` | `docs/archive/evidence/reports/2026-06-18/pr-triage-plan-2026-06-04.md` |
| `reports/test-gap-analysis.md` | `docs/archive/evidence/reports/2026-06-18/test-gap-analysis.md` |
| `reports/test-inventory.md` | `docs/archive/evidence/reports/2026-06-18/test-inventory.md` |
| `reports/test-quality-audit.md` | `docs/archive/evidence/reports/2026-06-18/test-quality-audit.md` |
| `reports/repo-cleanup/` | `docs/archive/evidence/reports/repo-cleanup/` |

## Files Deleted

| Path | Reason |
|---|---|
| `reports/layer1-test-run-2026-06-01.txt` | Empty file (0 bytes) |

## Files Intentionally Left in `reports/`

These files/directories are still referenced by active docs, CI, scripts, or tests, and were not moved:

| Path | Reason |
|---|---|
| `reports/archive/` | Already archived under `reports/`. The `scripts/ci/check_reports_evidence_policy.py` gate continues to allow this location. |
| `reports/autonomous-test-assurance/` | Active directory; referenced by `docs/archive/2026-05-28/autonomous-test-assurance-pr-ready.md` and assurance workflows. |
| `reports/coverage/` | Coverage output directory; referenced by archived test coverage audit. |
| `reports/current-readiness-p0-remediation-2026-06-01.md` | Referenced by `docs/readiness/blockers.md`. |
| `reports/database-comparison-matrix.md` | Referenced by `docs/database-standardization-and-error-handling-summary.md`. |
| `reports/deferred-issues-technical-blockers.md` | Active blocker register. |
| `reports/httpexception-inventory.md` | Referenced by `docs/database-standardization-and-error-handling-summary.md`. |
| `reports/postgresql-helper-extraction-analysis.md` | Referenced by `docs/database-standardization-and-error-handling-summary.md`. |
| `reports/pr-triage-plan.md` | Referenced by `docs/launch/stabilization-gate-0-intake-2026-06-03.md`. |
| `reports/production-invariants.md` | Referenced by `reports/autonomous-test-assurance-execution-report.md` (archived) and active assurance context. |
| `reports/production-launch-readiness-audit.md` | Referenced by `docs/development/DISCOVERY_MAP.md`, `scripts/reports/generate_repo_maturity_scorecard.py`, and `tests/ci/test_repo_maturity_scorecard.py`. |
| `reports/production-readiness-gap-analysis.md` | Referenced by `docs/development/DISCOVERY_MAP.md` and `docs/database-standardization-and-error-handling-summary.md`. |
| `reports/scorecards/` | Active directory; generated by `scripts/reports/generate_repo_maturity_scorecard.py` and validated by `tests/ci/test_repo_maturity_scorecard.py`. |
| `reports/security/` | Active directory; referenced by `docs/development/DISCOVERY_MAP.md`. |
| `reports/testing/` | Active directory; referenced by assurance evidence and test documentation. |
| `reports/value-fabric-facade-inventory.md` | Referenced by `scripts/ci/check_value_fabric_facade_imports.py` and archived advisory audit. |

## References Updated

| File | Change |
|---|---|
| `docs/development/DISCOVERY_MAP.md` | `reports/api-contract-stability-audit.md` → `docs/archive/evidence/reports/2026-06-18/api-contract-stability-audit.md` |
| `docs/validation/production_readiness_execution_status.md` | `reports/p0-blockers-local-evidence-2026-05-31.md` → `docs/archive/evidence/reports/2026-06-18/p0-blockers-local-evidence-2026-05-31.md` |
| `docs/archive/evidence/reports/2026-06-18/p0-blockers-handoff-2026-05-31.md` | Internal references updated to sibling archived files. |
| `docs/archive/evidence/reports/2026-06-18/elevate-to-9-migration-report.md` | `reports/infra_secret_mapping.md` → `infra_secret_mapping.md` |
| `docs/archive/evidence/reports/2026-06-18/autonomous-test-assurance-execution-report.md` | `reports/test-inventory.md` → `test-inventory.md`; `reports/test-gap-analysis.md` → `test-gap-analysis.md`; `reports/production-invariants.md` → `../production-invariants.md` |
| `docs/archive/evidence/reports/2026-06-18/advisory-production-audit-verification-2026-06-01.md` | `reports/value-fabric-facade-inventory.md` → `../../../../../reports/value-fabric-facade-inventory.md` |
| `docs/archive/evidence/reports/2026-06-18/conflict-inventory-2026-05-19.md` | `reports/RELEASE_READINESS_AUDIT_2026-05-12.md` → `docs/archive/quality-reports/2026-05-22/RELEASE_READINESS_AUDIT_2026-05-12.md`; `reports/TEST_COVERAGE_RUBRIC_AUDIT_2026-05-12.md` → `docs/archive/quality-reports/2026-05-22/TEST_COVERAGE_RUBRIC_AUDIT_2026-05-12.md` |
| `docs/maintenance/repo-organization-cleanup-audit.md` | Archive candidate table updated to reflect actual moves and keep decisions. |
| `scripts/ci/check_reports_evidence_policy.py` | Archive allowlist updated to include both `reports/archive/` and `docs/archive/evidence/reports/`. |
| `config/baselines/readiness-language-baseline.json` | Paths updated from `reports/repo-cleanup/` to `docs/archive/evidence/reports/repo-cleanup/`. |
| `config/ci/legacy_debt_config.json` | Excluded prefix updated from `reports/repo-cleanup/` to `docs/archive/evidence/reports/repo-cleanup/`. |
| `reports/archive/2026-05-02-repo-cleanup-collection-errors/README.md` | Source task family reference updated. |
| `docs/archive/quality-reports/2026-05-22/anti-drift-hardening-deliverable.md` | Baselined repo-cleanup references updated to archive paths. |
| `docs/archive/evidence/reports/repo-cleanup/high_risk_moves.md` | `reports/repo-cleanup/ROLLBACK-YYYY-MM-DD.md` → `ROLLBACK-YYYY-MM-DD.md` |
| `docs/archive/evidence/reports/repo-cleanup/phase1_checkpoint_report.md` | `reports/repo-cleanup/` → `this archive directory` |
| `docs/archive/evidence/reports/repo-cleanup/NAVIGATION_MIGRATION_FINAL_REPORT_2026-05-02.md` | `reports/repo-cleanup/NAVIGATION_MIGRATION_*` → `NAVIGATION_MIGRATION_*` |
| `docs/archive/evidence/reports/repo-cleanup/POST_COLLECTION_VALIDATION_REPORT_2026-05-02.md` | `reports/repo-cleanup/PYTEST_IMPORTLIB_MODE_DUPLICATES_2026-05-02.md` → `PYTEST_IMPORTLIB_MODE_DUPLICATES_2026-05-02.md` |
| `docs/archive/evidence/reports/repo-cleanup/PYTEST_COLLECTION_REMEDIATION_REPORT_2026-05-02.md` | `reports/repo-cleanup/PYTEST_*` → `PYTEST_*` (sibling references) |
| `docs/archive/evidence/reports/repo-cleanup/PHASE_5_FRONTEND_MOVE_2026-05-02.md` | `reports/repo-cleanup/PHASE_5_FRONTEND_MOVE_2026-05-02.md` → `PHASE_5_FRONTEND_MOVE_2026-05-02.md` |

## Validation Commands

```bash
git status --short
git diff --stat
python scripts/ci/check_reports_evidence_policy.py
python scripts/ci/check_legacy_debt.py --baseline config/ci/legacy_debt_baseline.json --approvals config/ci/legacy_debt_approvals.json --config config/ci/legacy_debt_config.json
rg "reports/(advisory-production-audit-verification|api-contract-stability-audit|auth-jwks|authentication-security-audit-2026-05-27|autonomous-test-assurance-(execution-report|report-2026-05-25|report-2026-05-30)|circuit-breaker-inventory|comprehensive_system_audit_report|conflict-inventory-2026-05-19|documentation-cleanup-phase|drills|elevate-to-9-migration-report|enterprise-release-blockers-2026-06-01|infra_secret_mapping|layer1-test-(failure-analysis|raw-output|stabilization-2026-06-01)|p0-(blockers|staging|validation)|PR-A-frontend-audit-cleanup|pr-bug-triage-20260523|pr-triage-plan-2026-06-04|test-(gap-analysis|inventory|quality-audit)|repo-cleanup)" . --glob "!docs/archive/evidence/**"
```

## Risky Candidates for Later Cleanup

- `reports/coverage/` contains generated coverage logs; consider moving to CI artifacts or deleting if CI regenerates them.
- `reports/deferred-issues-technical-blockers.md` may need to be integrated into `docs/readiness/` or archived once blockers are resolved.
- `reports/PR-A-frontend-audit-cleanup.md` is archived, but if the PR-A initiative is re-opened, it may need to be moved back.
