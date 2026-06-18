# Documentation Cleanup - Phase 4: Archive vs Update Decision Matrix

**Audit Date:** 2026-05-28
**Auditor:** Documentation Archaeologist

---

## Decision Matrix

For every file, apply this without sentiment:

| Condition | Action |
|-----------|--------|
| Last meaningful update >18 months ago AND not linked from README | **Archive** |
| Contains known-broken commands, dead links, or deprecated service names | **Update or Archive** |
| Duplicates content from a more recent, more complete file | **Archive, redirect to canonical** |
| High density, well-linked, accurate as of recent commits | **Keep, elevate in README** |
| Low density but covers unique topic no other doc touches | **Merge/rewrite, don't leave as-is** |

---

## Archive List

### Root-Level Files

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| ROADMAP.md | 4650 lines, audit date 2026-04-09, likely outdated | **Archive** | docs/archive/2026-05-28/ROADMAP.md |

### docs/ Root-Level Files

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| DOCUMENTATION_AUDIT_REPORT.md | ARCHIVED banner, superseded by docs/README.md | **Already Archived** | docs/archive/INDEX.md |
| BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md | ARCHIVED banner, superseded by contracts/ | **Already Archived** | docs/archive/INDEX.md |
| SECURITY_FIXES_SUMMARY.md | ARCHIVED banner, superseded by security/ | **Already Archived** | docs/archive/INDEX.md |
| CHANGES.md | ARCHIVED banner, historical refactor log | **Already Archived** | docs/archive/INDEX.md |
| DEPRECATIONS.md | Redirect only, points to governance/ | **Archive** | docs/archive/2026-05-28/DEPRECATIONS.md |

### docs/reference/ Files

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| deprecated-namespace-migration-tracker.md | Temporal migration tracker | **Archive** | docs/archive/2026-05-28/ |
| deprecated-namespace-support-policy.md | Temporal policy | **Archive** | docs/archive/2026-05-28/ |
| layer1-compatibility-deprecation.md | Temporal deprecation | **Archive** | docs/archive/2026-05-28/ |
| layer1-fixes-enhancements-roadmap.md | Temporal roadmap | **Archive** | docs/archive/2026-05-28/ |
| layer3-cypher-security-inventory.md | Temporal inventory | **Archive** | docs/archive/2026-05-28/ |
| layer3-graph-field-cutover.md | Temporal migration | **Archive** | docs/archive/2026-05-28/ |
| layer3-layer6-wrapper-policy.md | Temporal policy | **Archive** | docs/archive/2026-05-28/ |
| layer3-tenant-isolation-audit.md | Temporal audit | **Archive** | docs/archive/2026-05-28/ |
| layer4-deterministic-replay-spec.md | Temporal spec | **Archive** | docs/archive/2026-05-28/ |
| layer4-frontend-contract-regeneration.md | Temporal migration | **Archive** | docs/archive/2026-05-28/ |
| layer5-api-compatibility-policy.md | Temporal policy | **Archive** | docs/archive/2026-05-28/ |
| layer5-observability-schema.md | Temporal schema | **Archive** | docs/archive/2026-05-28/ |
| layer6-drift-audit-artifact-index.md | Temporal audit | **Archive** | docs/archive/2026-05-28/ |
| migration-safety-baseline.json | JSON baseline (config, not doc) | **Move to config/baselines/** | config/baselines/ |
| readiness-language-baseline.json | JSON baseline (config, not doc) | **Move to config/baselines/** | config/baselines/ |
| deprecation-drift-baseline.json | JSON baseline (config, not doc) | **Move to config/baselines/** | config/baselines/ |

### docs/governance/ Files

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| auth-tenant-todo-audit-2026-05-12.md | Temporal audit | **Archive** | docs/archive/2026-05-28/ |
| contract-remediation-queue-by-layer.md | Temporal queue | **Archive** | docs/archive/2026-05-28/ |
| layer-quality-scorecard.json | JSON baseline (config, not doc) | **Move to config/baselines/** | config/baselines/ |
| layer-quality-threshold-policy.json | JSON baseline (config, not doc) | **Move to config/baselines/** | config/baselines/ |
| production-readiness-status-2026-05-14.md | Temporal status | **Archive** | docs/archive/2026-05-28/ |
| repo-hygiene-report-governance-check.md | Temporal report | **Archive** | docs/archive/2026-05-28/ |
| repo-hygiene-work-items-2026-05-12.md | Temporal work items | **Archive** | docs/archive/2026-05-28/ |

### docs/security/ Files

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| THREAT_MODEL.md | Duplicate of threat-model.md | **Delete** | N/A |
| triage-notes-2026-04-14.md | Temporal notes | **Archive** | docs/archive/2026-05-28/ |

### docs/operations/ Files

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| tenant-management-phase-1-rls-hardening-rescoped.md | Temporal phase doc | **Archive** | docs/archive/2026-05-28/ |
| tenant-management-phase-1-rls-hardening.md | Temporal phase doc | **Archive** | docs/archive/2026-05-28/ |
| tenant-management-phase-2-provisioning.md | Temporal phase doc | **Archive** | docs/archive/2026-05-28/ |
| tenant-management-phase-3-control-plane.md | Temporal phase doc | **Archive** | docs/archive/2026-05-28/ |
| tenant-management-remediation-plan.md | Temporal plan | **Archive** | docs/archive/2026-05-28/ |
| tenant-management-remediation-verification.md | Temporal verification | **Archive** | docs/archive/2026-05-28/ |
| tenant-management-security-audit.json | Temporal audit | **Archive** | docs/archive/2026-05-28/ |

### docs/testing/ Files

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| TEST_FIXES_APPLIED.md | Temporal fixes log | **Archive** | docs/archive/2026-05-28/ |
| assurance-remediation-report.md | Temporal report | **Archive** | docs/archive/2026-05-28/ |
| pre-existing-failures.md | Temporal baseline | **Archive** | docs/archive/2026-05-28/ |
| rewrite-queue.md | Temporal queue | **Archive** | docs/archive/2026-05-28/ |
| test_pass_rate_improvements_2026-05-06.md | Temporal report | **Archive** | docs/archive/2026-05-28/ |

### apps/web/docs/ Files

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| UI_UX_AUDIT.md | Temporal audit | **Archive** | docs/archive/2026-05-28/ |
| hook-coverage-qa-notes.md | Temporal QA notes | **Archive** | docs/archive/2026-05-28/ |
| calculator-route-migration.md | Historical migration | **Archive** | docs/archive/2026-05-28/ |

### reports/ Directory

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| autonomous-test-inventory.md | Temporal report | **Archive** | docs/archive/2026-05-28/ |
| autonomous-production-invariants.md | Temporal report | **Archive** | docs/archive/2026-05-28/ |
| autonomous-test-gap-analysis.md | Temporal report | **Archive** | docs/archive/2026-05-28/ |
| autonomous-test-validation.md | Temporal report | **Archive** | docs/archive/2026-05-28/ |
| autonomous-test-assurance-pr-ready.md | Temporal report | **Archive** | docs/archive/2026-05-28/ |

### artifacts/testing/ Directory

| File | Condition | Action | Destination |
|------|-----------|--------|-------------|
| All 21 test quality reports | Temporal reports | **Archive** | docs/archive/2026-05-28/ |

---

## Update Queue

### Files Requiring Updates

| File | Issue | Required Update | Priority |
|------|-------|-----------------|----------|
| docs/README.md | Links to archived docs | Update links to point to canonical replacements | High |
| README.md | Links to ARCHITECTURE.md | Update to link to docs/core-concepts/architecture.md | High |
| docs/security/ | Duplicate THREAT_MODEL.md | Delete THREAT_MODEL.md | Medium |
| docs/reference/layer4-route-contract-matrix.md | 49756 bytes, too large | Split into smaller files or move to contracts/ | Medium |
| docs/ValuePack_Framework_v2.0.md | 1437 lines, wrong location | Move to packs/ or docs/packs/ | Low |
| docs/VERSIONING.md | May be outdated | Review against CHANGELOG.md | Low |

---

## Keep List

### High-Density, Well-Linked, Accurate Files

**Root-Level:**
- README.md ⭐⭐⭐⭐⭐
- AGENTS.md ⭐⭐⭐⭐⭐
- CONTRIBUTING.md ⭐⭐⭐⭐
- DESIGN.md ⭐⭐⭐⭐⭐
- canonical-paths-policy.md ⭐⭐⭐

**docs/ Root-Level:**
- README.md ⭐⭐⭐⭐⭐
- contract.md ⭐⭐⭐⭐⭐
- ENVIRONMENT.md ⭐⭐⭐
- API_REFERENCE.md ⭐⭐⭐ (to be merged into api-overview.md)
- ValuePack_Framework_v2.0.md ⭐⭐⭐⭐ (to be moved)
- api-contract-stability.md ⭐⭐⭐⭐
- VERSIONING.md ⭐⭐⭐ (review needed)
- Providers.md ⭐⭐⭐ (to be expanded)

**docs/getting-started/:**
- quickstart.md ⭐⭐⭐⭐⭐
- environment.md ⭐⭐⭐⭐

**docs/core-concepts/:**
- architecture.md ⭐⭐⭐⭐⭐
- security-model.md ⭐⭐⭐⭐⭐
- ontology-system.md ⭐⭐⭐⭐

**docs/reference/:**
- api-overview.md ⭐⭐⭐⭐
- testing-strategy.md ⭐⭐⭐⭐
- layer-runtime-path-governance.md ⭐⭐⭐⭐⭐
- service-routing-and-api-version-matrix.md ⭐⭐⭐
- frontend-query-patterns.md ⭐⭐⭐⭐
- layer1-ingestion-api.md ⭐⭐⭐
- layer2-extraction-api.md ⭐⭐⭐
- layer3-knowledge-api.md ⭐⭐⭐
- layer4-agents-api.md ⭐⭐⭐
- layer5-ground-truth-api.md ⭐⭐⭐

**docs/how-to-guides/:**
- setup-local-dev.md ⭐⭐⭐⭐
- configure-sso.md ⭐⭐⭐⭐
- drift-detection.md ⭐⭐⭐⭐
- operators.md ⭐⭐⭐⭐
- role-onboarding.md ⭐⭐⭐

**docs/troubleshooting/:**
- index.md ⭐⭐⭐⭐
- runbooks/ subdirectory ⭐⭐⭐

**docs/explanations/adr/:**
- ADR-002-six-layer-architecture.md ⭐⭐⭐⭐⭐
- All other ADRs ⭐⭐⭐⭐

**docs/governance/:**
- compatibility-debt-registry.md ⭐⭐⭐⭐⭐
- deprecations.json ⭐⭐⭐⭐ (machine-readable)
- launch-drift-prevention-sop.md ⭐⭐⭐⭐
- COMPLIANCE.md ⭐⭐⭐
- contract-exception-policy.md ⭐⭐⭐

**docs/security/:**
- multi-tenancy.md ⭐⭐⭐⭐
- secrets-management.md ⭐⭐⭐⭐
- secure-software-supply-chain.md ⭐⭐⭐⭐
- token-contract.md ⭐⭐⭐⭐
- threat-model.md ⭐⭐⭐⭐
- key-rotation-guide.md ⭐⭐⭐
- key-rotation-quickref.md ⭐⭐⭐
- key-rotation-checklist.md ⭐⭐⭐

**docs/operations/:**
- RELEASE_RUNBOOK.md ⭐⭐⭐⭐
- keycloak-integration.md ⭐⭐⭐⭐
- tenant-management-master-plan.md ⭐⭐⭐⭐
- runbooks/ subdirectory ⭐⭐⭐

**docs/testing/:**
- TEST_CATALOG.md ⭐⭐⭐⭐
- production-invariants.md ⭐⭐⭐⭐
- test-gap-matrix.md ⭐⭐⭐
- test-inventory.md ⭐⭐⭐

**apps/web/docs/:**
- ROUTE_INVENTORY.md ⭐⭐⭐
- route-layer-dependency-map.md ⭐⭐⭐⭐
- MOCK_AUTH_IMPLEMENTATION.md ⭐⭐⭐
- async-boundary-inventory.md ⭐⭐⭐

---

## Merge/Rewrite List

### Low Density but Unique Topic

| File | Issue | Action | Target |
|------|-------|--------|--------|
| docs/ARCHITECTURE.md | Redirect stub, 42 lines | **Merge** | docs/core-concepts/architecture.md |
| docs/API_REFERENCE.md | Redundant with api-overview.md | **Merge** | docs/reference/api-overview.md |
| docs/DEPRECATIONS.md | Redirect only | **Merge** | docs/governance/compatibility-debt-registry.md |
| docs/Providers.md | Small but important | **Expand** | Comprehensive provider catalog |
| docs/getting-started/ | Scattered setup guides | **Merge** | Unified onboarding guide |
| docs/testing/ | Scattered test docs | **Merge** | Testing handbook |
| docs/security/ | Scattered security docs | **Merge** | docs/core-concepts/security-model.md |

---

## Summary

**Archive:** ~60 files
**Move to config/baselines/:** ~7 files
**Delete:** 1 file (THREAT_MODEL.md duplicate)
**Update:** ~5 files
**Keep:** ~80 files
**Merge/Rewrite:** ~10 file groups

**Total Files Affected:** ~163 files

---

## Next Steps

**Phase 5: README as Navigation Layer** - Propose new README structure
