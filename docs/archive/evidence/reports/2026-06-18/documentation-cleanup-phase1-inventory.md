# Documentation Cleanup - Phase 1: Inventory & Classification

**Audit Date:** 2026-05-28
**Auditor:** Documentation Archaeologist
**Scope:** All markdown documentation in Fabric_4L monorepo

---

## Inventory Summary

**Total Documentation Files:** ~200+ markdown files
**High-Value (Density 4-5):** ~35 files
**Medium-Value (Density 2-3):** ~45 files
**Low-Value (Density 1):** ~120+ files
**Already Archived:** ~139 files in docs/archive/

---

## Root-Level Documentation

| File | Last Modified | Type | Density | Duplication | Orphan | Notes |
|------|--------------|------|---------|-------------|--------|-------|
| README.md | Recent | Onboarding | 5 | No | No | **Primary entry point** - excellent density |
| AGENTS.md | Recent | Runbook/Operational | 5 | No | No | **Critical for AI agents** - commands, directory map |
| ARCHITECTURE.md | Recent | Architecture | 3 | Partial | No | Links to other docs, could be consolidated |
| canonical-paths-policy.md | Recent | Governance | 3 | No | No | CI enforcement policy, important |
| CONTRIBUTING.md | Recent | Onboarding | 4 | No | No | Setup instructions, good density |
| DESIGN.md | Recent | Architecture/Decision | 5 | No | No | **Frontend governance contract** - critical |
| ROADMAP.md | 2026-04-09 | Architecture/Decision | 2 | No | No | **4650 lines** - likely outdated, needs archival |
| SECURITY.md | Not read | Security | ? | ? | ? | Needs review |
| CHANGELOG.md | Not read | Meta | ? | ? | ? | Needs review |

---

## docs/ Root-Level Files

| File | Last Modified | Type | Density | Duplication | Orphan | Notes |
|------|--------------|------|---------|-------------|--------|-------|
| README.md | 2026-05-04 | Meta/Navigation | 5 | No | No | **Diátaxis hub** - excellent organization |
| DOCUMENTATION_AUDIT_REPORT.md | 2026-05-03 | Audit Report | 1 | No | No | **ARCHIVED banner** - already superseded |
| BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md | 2026-05-02 | Audit Report | 1 | No | No | **ARCHIVED banner** - superseded by contracts/ |
| SECURITY_FIXES_SUMMARY.md | 2026-04-27 | Audit Report | 1 | No | No | **ARCHIVED banner** - superseded by security/ |
| ENVIRONMENT.md | Recent | Reference | 3 | No | No | Environment variable classification |
| API_REFERENCE.md | Recent | API/Reference | 3 | Partial | No | Human-readable API summary |
| ValuePack_Framework_v2.0.md | 2026-05-06 | Reference | 4 | No | No | **1437 lines** - product framework |
| api-contract-stability.md | Recent | Reference | 4 | No | No | API contract stability guidelines |
| DEPRECATIONS.md | 2026-04-28 | Reference | 2 | No | No | **Redirect only** - points to governance/ |
| CHANGES.md | 2026-04-21 | Audit Report | 1 | No | No | **ARCHIVED banner** - historical refactor log |
| VERSIONING.md | 2026-04-15 | Reference | 3 | No | No | Semantic versioning policy |
| Providers.md | Recent | Reference | 3 | No | No | External provider catalog |
| contract.md | Recent | Architecture/Decision | 5 | No | No | **Canonical platform contract** - critical |

---

## docs/getting-started/ (3 files)

| File | Type | Density | Duplication | Orphan | Notes |
|------|------|---------|-------------|--------|-------|
| quickstart.md | Tutorial | 5 | No | No | **15-minute setup** - excellent |
| environment.md | Guide | 4 | No | No | Environment configuration |
| Fabric_4L.code-workspace | Config | 1 | No | No | VS Code workspace file |

---

## docs/core-concepts/ (3 files)

| File | Type | Density | Duplication | Orphan | Notes |
|------|------|---------|-------------|--------|-------|
| architecture.md | Explanation | 5 | No | No | **6-layer architecture** - critical |
| security-model.md | Explanation | 5 | No | No | Authentication, RBAC, tenant isolation |
| ontology-system.md | Explanation | 4 | No | No | Entity taxonomy and extraction |

---

## docs/reference/ (49 files)

**High-Value Files:**
- api-overview.md (4) - API structure overview
- testing-strategy.md (4) - Test pyramid and strategy
- layer-runtime-path-governance.md (5) - **Critical** - where code must live
- service-routing-and-api-version-matrix.md (3) - Service ports and versions
- frontend-query-patterns.md (4) - TanStack Query patterns

**Medium-Value Files:**
- layer1-ingestion-api.md (3)
- layer2-extraction-api.md (3)
- layer3-knowledge-api.md (3)
- layer4-agents-api.md (3)
- layer5-ground-truth-api.md (3)
- compliance.md (3)
- performance-characteristics.md (3)

**Low-Value/Duplicate Files:**
- deprecated-namespace-migration-tracker.md (2)
- deprecated-namespace-support-policy.md (2)
- layer1-compatibility-deprecation.md (2)
- layer1-fixes-enhancements-roadmap.md (2)
- layer3-cypher-security-inventory.md (2)
- layer3-graph-field-cutover.md (2)
- layer3-layer6-wrapper-policy.md (2)
- layer3-tenant-isolation-audit.md (2)
- layer4-deterministic-replay-spec.md (2)
- layer4-frontend-contract-regeneration.md (2)
- layer4-route-contract-matrix.md (2) - **49756 bytes** - very large
- layer5-api-compatibility-policy.md (2)
- layer5-observability-schema.md (2)
- layer6-drift-audit-artifact-index.md (2)
- Many JSON baselines (migration-safety-baseline.json, readiness-language-baseline.json, etc.)

---

## docs/how-to-guides/ (5 files)

| File | Type | Density | Duplication | Orphan | Notes |
|------|------|---------|-------------|--------|-------|
| setup-local-dev.md | Guide | 4 | No | No | Local development setup |
| configure-sso.md | Guide | 4 | No | No | OIDC/SAML SSO setup |
| drift-detection.md | Guide | 4 | No | No | API contract drift detection |
| operators.md | Guide | 4 | No | No | Operator-facing runbook index |
| role-onboarding.md | Guide | 3 | No | No | Role-based onboarding |

---

## docs/troubleshooting/ (41 files)

**High-Value:**
- index.md (4) - Decision tree navigation
- runbooks/ subdirectory with operational procedures

**Medium-Value:**
- Symptom-based troubleshooting guides

**Low-Value:**
- Many runbooks may be outdated or superseded

---

## docs/explanations/ (21 files)

**High-Value:**
- adr/ subdirectory (21 ADRs) - Architecture Decision Records
- ADR-002-six-layer-architecture.md (5) - Critical ADR

**Medium-Value:**
- Various explanation documents

---

## docs/archive/ (139 files)

**Status:** Already properly archived with INDEX.md registry

**Subdirectories:**
- 2026-04-19/ (10 items)
- 2026-04-27/ (18 items)
- frontend-root-2026-05-02/ (47 items)
- legacy-value-fabric/ (12 items)
- quality-reports/ (46 items)

**Note:** Archive policy is working well. No action needed here.

---

## docs/governance/ (33 files)

**High-Value:**
- compatibility-debt-registry.md (5) - **Critical** - canonical deprecation registry
- deprecations.json (4) - Machine-readable mirror
- launch-drift-prevention-sop.md (4) - Launch governance
- production-readiness-status-2026-05-14.md (4) - Current readiness

**Medium-Value:**
- Various governance policies and checklists

**Low-Value:**
- Many temporal audit reports (auth-tenant-todo-audit-2026-05-12.md, etc.)
- JSON scorecards and thresholds

---

## docs/security/ (18 files)

**High-Value:**
- multi-tenancy.md (4) - Multi-tenant security
- secrets-management.md (4) - Secret management
- secure-software-supply-chain.md (4) - Supply chain security
- token-contract.md (4) - Token contract

**Medium-Value:**
- key-rotation-guide.md (3)
- key-rotation-quickref.md (3)
- key-rotation-checklist.md (3)

**Low-Value:**
- THREAT_MODEL.md (1) - Duplicate of threat-model.md
- legacy-value-fabric-security-architecture.md (1) - Historical
- Various temporal reports (triage-notes-2026-04-14.md, etc.)

---

## docs/operations/ (43 files)

**High-Value:**
- RELEASE_RUNBOOK.md (4) - Release procedures
- keycloak-integration.md (4) - Keycloak setup
- tenant-management-master-plan.md (4) - Tenant management

**Medium-Value:**
- Various operational runbooks and procedures

**Low-Value:**
- Many phase-specific tenant management docs that may be superseded
- Temporal reports and checklists

---

## docs/testing/ (12 files)

**High-Value:**
- TEST_CATALOG.md (4) - Test catalog
- production-invariants.md (4) - Production invariants
- test-quality-audit.md (4) - Test quality audit

**Medium-Value:**
- test-gap-matrix.md (3)
- test-inventory.md (3)

**Low-Value:**
- Temporal reports (test_pass_rate_improvements_2026-05-06.md, etc.)

---

## apps/web/docs/ (8 files)

| File | Type | Density | Duplication | Orphan | Notes |
|------|------|---------|-------------|--------|-------|
| UI_UX_AUDIT.md | Audit Report | 1 | No | No | Temporal audit |
| ROUTE_INVENTORY.md | Reference | 3 | No | No | Route inventory |
| route-layer-dependency-map.md | Reference | 4 | No | No | **Critical** - frontend-backend mapping |
| MOCK_AUTH_IMPLEMENTATION.md | Guide | 3 | No | No | Mock auth implementation |
| hook-coverage-qa-notes.md | Audit Report | 1 | No | No | Temporal QA notes |
| calculator-route-migration.md | Migration Log | 2 | No | No | Historical migration |
| async-boundary-inventory.md | Reference | 3 | No | No | Async boundary inventory |

---

## artifacts/ Directory

**Status:** Contains temporal reports and test artifacts

**Subdirectories:**
- testing/ (21 files) - Test quality reports, audits, summaries
- mandatory_security/ (1 file) - Security summary

**Recommendation:** These are artifacts, not documentation. Should be moved to a separate artifacts/ directory outside docs/.

---

## reports/ Directory

**Status:** Contains autonomous test assurance reports

**Files:**
- autonomous-test-inventory.md
- autonomous-production-invariants.md
- autonomous-test-gap-analysis.md
- autonomous-test-validation.md
- autonomous-test-assurance-pr-ready.md

**Recommendation:** These are temporal reports, not canonical documentation. Should be archived or moved to artifacts/.

---

## Key Findings

1. **Strong Core Documentation:** README.md, AGENTS.md, DESIGN.md, docs/README.md are excellent entry points
2. **Archive Policy Working:** docs/archive/ is well-organized with proper registry
3. **Temporal Report Bloat:** Many temporal audit reports at docs/ root and in subdirectories
4. **Redirect-Only Files:** DEPRECATIONS.md is just a redirect pointer
5. **Duplicate Security Docs:** THREAT_MODEL.md and threat-model.md exist
6. **Large Files:** ROADMAP.md (4650 lines), layer4-route-contract-matrix.md (49756 bytes)
7. **Artifacts in docs/:** artifacts/ and reports/ contain temporal reports, not documentation
8. **JSON Baselines:** Many JSON files in docs/reference/ that are configuration, not documentation

---

## Next Steps

**Phase 2: Valuation & Triage** - Identify highest-value documents for new engineers
**Phase 3: Consolidation Opportunities** - Find merge candidates
**Phase 4: Archive vs Update Decision Matrix** - Decide keep/update/archive
**Phase 5: README as Navigation Layer** - Propose new README structure
