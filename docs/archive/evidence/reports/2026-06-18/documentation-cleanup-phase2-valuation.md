# Documentation Cleanup - Phase 2: Valuation & Triage

**Audit Date:** 2026-05-28
**Auditor:** Documentation Archaeologist

---

## Valuation Criteria

| Criterion | Weight | What to look for |
|-----------|--------|----------------|
| Entry-point value | High | Docs that answer "How do I build/run/test this?" |
| Architectural clarity | High | Docs that explain *why* the system is shaped this way |
| API completeness | Medium | Reference docs with full coverage, not partial examples |
| Historical necessity | Low | Only keep if decisions are still binding; otherwise archive |

**Key Question:** *If a new senior engineer joined tomorrow and had 2 hours, which 3 docs would give them the most accurate mental model?*

---

## Highest-Value Documents (Tier 1)

### 1. README.md (Root)
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Entry-point / Onboarding
**Why Critical:**
- Primary entry point for the entire repository
- Explains 6-layer architecture with ASCII diagram
- Links to all critical documentation
- Provides quickstart commands
- Explains package manager policy (pnpm-only)
- Maps repository structure with canonical paths

**Entry-point Value:** MAXIMUM - Answers "What is this?" and "How do I start?" in 5 minutes

---

### 2. docs/contract.md
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Architecture / Decision / Governance
**Why Critical:**
- **Canonical platform contract** - defines enforced direction for the entire codebase
- Specifies single unambiguous canonical contract for 6 cross-layer concerns
- Includes automated enforcement and deprecation map
- Converts codebase from evolving to governed product platform
- Covers: Tenant Context, DB Session, Middleware, Tool Invocation, Agent Output, Error Envelopes

**Architectural Clarity:** MAXIMUM - Explains *why* the system is shaped this way and *how* to contribute correctly

---

### 3. docs/reference/layer-runtime-path-governance.md
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Reference / Governance
**Why Critical:**
- **Canonical contribution guide** - where new code must be added per platform layer
- Prevents drift into archived, compatibility-only, or wrapper-only paths
- Maps canonical runtime paths vs legacy/compatibility paths
- Specifies allowed new development targets
- Includes deprecation owner/date for each layer

**Entry-point Value:** MAXIMUM - Answers "Where do I add code?" for every layer

---

## High-Value Documents (Tier 2)

### 4. AGENTS.md (Root)
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Runbook / Operational
**Why Critical:**
- Practical commands and directory map for AI agents and contributors
- Setup instructions with prerequisites
- Dev server commands for all layers
- Build, testing, lint, format commands
- Contract & governance checks
- Migration commands
- Key directories and important files

**Entry-point Value:** HIGH - Essential for AI agents and new contributors

---

### 5. DESIGN.md (Root)
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Architecture / Decision / Governance
**Why Critical:**
- **Production frontend governance contract** for apps/web/
- Combines implementation rules, design-system tokens, quality gates
- Defines operating rules for coding agents
- Specifies stack conventions (React, Vite, Tailwind, shadcn/ui, TanStack Query)
- Component architecture and state management patterns

**Architectural Clarity:** HIGH - Critical for any frontend work

---

### 6. docs/core-concepts/architecture.md
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Explanation / Architecture
**Why Critical:**
- Explains 6-layer pipeline architecture
- Data flow through the system
- Container and component-level designs
- Deployment topology for production
- Prerequisites and related documentation

**Architectural Clarity:** MAXIMUM - Core architectural understanding

---

### 7. docs/README.md
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Meta / Navigation
**Why Critical:**
- **Diátaxis hub** - follows Diátaxis Framework organization
- Quick navigation table for all user needs
- Documentation taxonomy explanation
- Folder structure with descriptions
- Documentation standards (YAML frontmatter, cross-linking, diagrams)
- Freshness tracking and archive policy
- Success metrics

**Entry-point Value:** MAXIMUM - Primary documentation navigation hub

---

### 8. docs/reference/testing-strategy.md
**Value:** ⭐⭐⭐⭐ (4/5)
**Type:** Reference / Guide
**Why Critical:**
- Comprehensive testing strategy for Silicon Valley production standards
- Test pyramid (70% unit, 20% integration, 10% E2E)
- Coverage requirements (≥80% line coverage)
- Test frameworks and tools
- Contract testing requirements
- CI/CD integration

**Entry-point Value:** HIGH - Answers "How do I test this?"

---

### 9. docs/getting-started/quickstart.md
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Tutorial / Onboarding
**Why Critical:**
- 15-minute setup and first API call
- Prerequisites with verify commands
- Step-by-step local instance setup
- First document ingestion
- First knowledge graph query
- First agent workflow run

**Entry-point Value:** MAXIMUM - Fastest path to first success

---

### 10. docs/core-concepts/security-model.md
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Explanation / Architecture
**Why Critical:**
- Authentication, authorization, audit
- Tenant isolation model
- Security boundaries
- Multi-tenancy architecture
- Related to core platform contract

**Architectural Clarity:** HIGH - Critical for security understanding

---

### 11. docs/governance/compatibility-debt-registry.md
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** Reference / Governance
**Why Critical:**
- **Canonical source of truth** for runtime compatibility shims
- Deprecated paths and target-removal dates
- Machine-readable mirror in deprecations.json
- CI gate input
- Migration strategies

**Historical Necessity:** HIGH - Binding decisions for compatibility

---

### 12. docs/reference/api-overview.md
**Value:** ⭐⭐⭐⭐ (4/5)
**Type:** API / Reference
**Why Critical:**
- Multi-layer API structure
- Authentication patterns across all layers
- Common request/response patterns
- Links to layer-specific API documentation
- Frontend dependency mapping

**API Completeness:** HIGH - API entry point

---

## Medium-Value Documents (Tier 3)

### 13. docs/core-concepts/ontology-system.md
**Value:** ⭐⭐⭐⭐ (4/5)
**Type:** Explanation / Reference
**Why Important:** Entity types, relationships, extraction pipeline

### 14. docs/reference/service-routing-and-api-version-matrix.md
**Value:** ⭐⭐⭐ (3/5)
**Type:** Reference
**Why Important:** Service ports, base paths, version compatibility

### 15. docs/reference/frontend-query-patterns.md
**Value:** ⭐⭐⭐⭐ (4/5)
**Type:** Reference
**Why Important:** TanStack Query, Zustand, generated-client rules for apps/web/

### 16. docs/how-to-guides/setup-local-dev.md
**Value:** ⭐⭐⭐⭐ (4/5)
**Type:** Guide
**Why Important:** Configure local development

### 17. docs/how-to-guides/drift-detection.md
**Value:** ⭐⭐⭐⭐ (4/5)
**Type:** Guide
**Why Important:** API contract, schema, and documentation drift detection

### 18. docs/how-to-guides/operators.md
**Value:** ⭐⭐⭐⭐ (4/5)
**Type:** Guide
**Why Important:** Single jumping-off point for operator-facing runbooks

### 19. docs/troubleshooting/index.md
**Value:** ⭐⭐⭐⭐ (4/5)
**Type:** Troubleshooting
**Why Important:** Decision tree navigation for problem resolution

### 20. docs/explanations/adr/ADR-002-six-layer-architecture.md
**Value:** ⭐⭐⭐⭐⭐ (5/5)
**Type:** ADR / Explanation
**Why Important:** Critical ADR explaining six-layer architecture decision

---

## Low-Value / Archive Candidates (Tier 4)

### Temporal Audit Reports (Archive)
- docs/DOCUMENTATION_AUDIT_REPORT.md (ARCHIVED banner)
- docs/BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md (ARCHIVED banner)
- docs/SECURITY_FIXES_SUMMARY.md (ARCHIVED banner)
- docs/CHANGES.md (ARCHIVED banner)
- docs/test-quality-audit.md
- docs/test-audit-2026-04-28.md
- docs/governance/auth-tenant-todo-audit-2026-05-12.md
- docs/security/triage-notes-2026-04-14.md
- docs/testing/test_pass_rate_improvements_2026-05-06.md
- apps/web/docs/UI_UX_AUDIT.md
- apps/web/docs/hook-coverage-qa-notes.md

### Redirect-Only Files (Archive or Consolidate)
- docs/DEPRECATIONS.md (Redirect only - points to governance/)
- docs/VERSIONING.md (May be outdated, check against CHANGELOG.md)

### Duplicate Files (Consolidate)
- docs/security/THREAT_MODEL.md (Duplicate of threat-model.md)
- docs/ARCHITECTURE.md (Partial duplicate of docs/core-concepts/architecture.md)

### Large Files (Review for Splitting)
- docs/ROADMAP.md (4650 lines - likely outdated)
- docs/reference/layer4-route-contract-matrix.md (49756 bytes - very large)
- docs/ValuePack_Framework_v2.0.md (1437 lines - may need separate section)

### JSON Baselines (Move to config/)
- docs/reference/migration-safety-baseline.json
- docs/reference/readiness-language-baseline.json
- docs/reference/deprecation-drift-baseline.json
- docs/governance/deprecations.json
- docs/governance/deprecation-debt-registry.json
- docs/governance/layer-quality-scorecard.json
- docs/governance/layer-quality-threshold-policy.json

### Artifacts (Move to artifacts/)
- reports/autonomous-test-*.md (5 files - temporal reports)
- artifacts/testing/*.md (21 files - test quality reports)

---

## The "2-Hour Mental Model" Selection

**If a new senior engineer joined tomorrow and had 2 hours, these 3 docs would give them the most accurate mental model:**

1. **README.md** (15 minutes)
   - What is Value Fabric?
   - 6-layer architecture overview
   - How to start (quickstart)
   - Repository structure

2. **docs/contract.md** (45 minutes)
   - Canonical platform contracts
   - Why the system is shaped this way
   - How to contribute correctly
   - Enforced patterns for 6 cross-layer concerns

3. **docs/reference/layer-runtime-path-governance.md** (30 minutes)
   - Where new code must be added
   - Canonical vs legacy paths
   - Deprecation timeline
   - CI enforcement

**Remaining 30 minutes:**
- docs/README.md (navigation hub) - 10 minutes
- docs/core-concepts/architecture.md - 15 minutes
- AGENTS.md (commands and directory map) - 5 minutes

---

## Valuation Summary

**Tier 1 (Critical - Must Keep):** 12 documents
**Tier 2 (High Value - Keep):** 8 documents
**Tier 3 (Medium Value - Review):** ~20 documents
**Tier 4 (Low Value - Archive/Consolidate):** ~120+ documents

**Recommendation:** Focus consolidation efforts on Tier 1 and Tier 2 documents. Archive Tier 4 temporal reports and redirect-only files. Review Tier 3 for consolidation opportunities.

---

## Next Steps

**Phase 3: Consolidation Opportunities** - Find merge candidates where 1+1 > 2
**Phase 4: Archive vs Update Decision Matrix** - Decide keep/update/archive for each file
**Phase 5: README as Navigation Layer** - Propose new README structure
