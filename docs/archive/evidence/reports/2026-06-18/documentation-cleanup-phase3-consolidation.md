# Documentation Cleanup - Phase 3: Consolidation Opportunities

**Audit Date:** 2026-05-28
**Auditor:** Documentation Archaeologist

---

## Consolidation Criteria

Flag for consolidation when:
- Two files share >60% overlapping context
- One file is <200 lines and only makes sense if you've read another file first
- A directory contains >5 files that are all variations on the same topic

---

## Consolidation Opportunity 1: Architecture Documentation

**Current State:**
- `ARCHITECTURE.md` (root) - 42 lines, links to other docs
- `docs/core-concepts/architecture.md` - 550 lines, detailed architecture
- `docs/architecture/system-overview.md` (if exists)
- `docs/architecture/component-interaction-map.md` (if exists)
- `docs/explanations/adr/ADR-002-six-layer-architecture.md` - 139 lines

**Overlap:** ~70% - ARCHITECTURE.md is essentially a redirect stub

**Consolidation Plan:**
```
Merge into: docs/core-concepts/architecture.md

Actions:
1. Add ADR-002 content as appendix to architecture.md
2. Delete ARCHITECTURE.md (root) - it's just a redirect stub
3. Update README.md to link directly to docs/core-concepts/architecture.md
4. Keep ADR-002 in adr/ for historical record
```

**Rationale:** ARCHITECTURE.md adds no value beyond what's already in docs/core-concepts/architecture.md. Consolidating reduces confusion and maintains single source of truth.

---

## Consolidation Opportunity 2: Security Documentation

**Current State:**
- `docs/core-concepts/security-model.md` - 19737 bytes, authentication/RBAC/tenant isolation
- `docs/security/THREAT_MODEL.md` - 718 bytes (duplicate)
- `docs/security/threat-model.md` - 5978 bytes
- `docs/security/multi-tenancy.md` - 14124 bytes
- `docs/security/secrets-management.md` - 6026 bytes
- `docs/security/secure-software-supply-chain.md` - 17079 bytes
- `docs/security/token-contract.md` - 11302 bytes

**Overlap:** ~40% - THREAT_MODEL.md is duplicate

**Consolidation Plan:**
```
Merge into: docs/core-concepts/security-model.md

Actions:
1. Delete docs/security/THREAT_MODEL.md (duplicate)
2. Add multi-tenancy section to security-model.md
3. Add secrets management section to security-model.md
4. Add supply chain security section to security-model.md
5. Keep token-contract.md as separate reference (too large to merge)
6. Keep threat-model.md as detailed threat model reference
```

**Rationale:** Consolidate core security concepts into single document. Keep specialized references (token contract, detailed threat model) separate.

---

## Consolidation Opportunity 3: API Reference Documentation

**Current State:**
- `docs/API_REFERENCE.md` - 741 bytes, human-readable summary
- `docs/reference/api-overview.md` - 415 bytes, API structure overview
- `docs/reference/layer1-ingestion-api.md` - 8956 bytes
- `docs/reference/layer2-extraction-api.md` - 9231 bytes
- `docs/reference/layer3-knowledge-api.md` - 10670 bytes
- `docs/reference/layer4-agents-api.md` - 12370 bytes
- `docs/reference/layer5-ground-truth-api.md` - 10295 bytes

**Overlap:** ~30% - API_REFERENCE.md and api-overview.md serve similar purpose

**Consolidation Plan:**
```
Merge into: docs/reference/api-overview.md

Actions:
1. Merge API_REFERENCE.md content into api-overview.md
2. Delete API_REFERENCE.md (docs/)
3. Keep layer-specific API docs separate (too large to merge)
4. Add service ports table from API_REFERENCE.md to api-overview.md
```

**Rationale:** API_REFERENCE.md is redundant with api-overview.md. Consolidate into single API entry point.

---

## Consolidation Opportunity 4: Testing Documentation

**Current State:**
- `docs/reference/testing-strategy.md` - 476 bytes, comprehensive test strategy
- `docs/testing/TEST_CATALOG.md` - 21793 bytes, test catalog
- `docs/testing/production-invariants.md` - 19873 bytes, production invariants
- `docs/testing/test-quality-audit.md` - 29147 bytes, test quality audit
- `docs/testing/test-gap-matrix.md` - 11764 bytes, test gap matrix
- `docs/testing/test-inventory.md` - 17112 bytes, test inventory
- `docs/testing/rewrite-queue.md` - 5047 bytes, rewrite queue

**Overlap:** ~50% - Multiple test-related docs with overlapping content

**Consolidation Plan:**
```
Merge into: docs/reference/testing-strategy.md

Actions:
1. Create comprehensive testing handbook:
   - Part 1: Strategy (from testing-strategy.md)
   - Part 2: Test Catalog (from TEST_CATALOG.md)
   - Part 3: Production Invariants (from production-invariants.md)
   - Part 4: Gap Analysis (from test-gap-matrix.md)
2. Archive temporal reports:
   - test-quality-audit.md → docs/archive/2026-05-28/
   - test-inventory.md → docs/archive/2026-05-28/
   - rewrite-queue.md → docs/archive/2026-05-28/
3. Delete docs/testing/ directory (move content to archive or consolidate)
```

**Rationale:** Testing documentation scattered across multiple files. Consolidate into single handbook with clear sections.

---

## Consolidation Opportunity 5: Governance Documentation

**Current State:**
- `docs/DEPRECATIONS.md` - 403 bytes, redirect only
- `docs/governance/compatibility-debt-registry.md` - 30905 bytes, canonical registry
- `docs/governance/deprecations.json` - 14672 bytes, machine-readable mirror
- `docs/governance/deprecation-debt-registry.json` - 1080 bytes
- `docs/governance/contract-exception-policy.md` - 7558 bytes
- `docs/governance/contract-remediation-queue-by-layer.md` - 7381 bytes
- `docs/governance/launch-drift-prevention-sop.md` - 2889 bytes
- `docs/governance/production-readiness-status-2026-05-14.md` - 7530 bytes

**Overlap:** ~20% - DEPRECATIONS.md is redirect only

**Consolidation Plan:**
```
Merge into: docs/governance/compatibility-debt-registry.md

Actions:
1. Delete docs/DEPRECATIONS.md (redirect only)
2. Add contract exception policy section to compatibility-debt-registry.md
3. Add launch drift prevention SOP section to compatibility-debt-registry.md
4. Archive temporal status reports:
   - production-readiness-status-2026-05-14.md → docs/archive/2026-05-28/
   - contract-remediation-queue-by-layer.md → docs/archive/2026-05-28/
5. Keep JSON files as machine-readable mirrors (not documentation)
```

**Rationale:** DEPRECATIONS.md is just a redirect. Consolidate governance policies into single registry document.

---

## Consolidation Opportunity 6: Getting Started Documentation

**Current State:**
- `README.md` - Quickstart section (lines 78-114)
- `docs/getting-started/quickstart.md` - 346 bytes, 15-minute setup
- `docs/getting-started/environment.md` - 15587 bytes, environment configuration
- `docs/how-to-guides/setup-local-dev.md` - 9533 bytes, local development setup
- `AGENTS.md` - Setup section (lines 10-48)

**Overlap:** ~60% - Multiple setup guides with overlapping content

**Consolidation Plan:**
```
Merge into: docs/getting-started/quickstart.md

Actions:
1. Create unified onboarding guide:
   - Part 1: Quickstart (15-minute setup)
   - Part 2: Environment Configuration (from environment.md)
   - Part 3: Local Development Setup (from setup-local-dev.md)
2. Remove quickstart section from README.md (keep link to docs/getting-started/quickstart.md)
3. Remove setup section from AGENTS.md (keep link to docs/getting-started/quickstart.md)
4. Keep environment.md as detailed reference (too large to merge entirely)
```

**Rationale:** Setup instructions scattered across README, AGENTS.md, and multiple docs files. Consolidate into single onboarding flow.

---

## Consolidation Opportunity 7: Provider Documentation

**Current State:**
- `docs/Providers.md` - 410 bytes, external provider catalog
- `docs/core-concepts/ontology-system.md` - 13065 bytes, mentions providers
- `docs/ENVIRONMENT.md` - 201 bytes, environment variable standard

**Overlap:** ~20% - Some overlap in provider configuration

**Consolidation Plan:**
```
Merge into: docs/Providers.md

Actions:
1. Expand Providers.md to include:
   - LLM providers (OpenAI, Anthropic)
   - Database providers (PostgreSQL, Neo4j, pgvector)
   - Infrastructure providers (Docker, Kubernetes)
   - External services (Keycloak, Vault)
2. Add environment variable references to each provider section
3. Keep ENVIRONMENT.md as classification standard (reference)
```

**Rationale:** Providers.md is small but important. Expand to comprehensive provider catalog.

---

## Consolidation Opportunity 8: Temporal Reports

**Current State:**
- `reports/autonomous-test-*.md` (5 files) - Autonomous test assurance reports
- `artifacts/testing/*.md` (21 files) - Test quality reports
- `docs/governance/auth-tenant-todo-audit-2026-05-12.md` - Temporal audit
- `docs/security/triage-notes-2026-04-14.md` - Temporal notes
- `docs/testing/test_pass_rate_improvements_2026-05-06.md` - Temporal report
- `apps/web/docs/UI_UX_AUDIT.md` - Temporal audit
- `apps/web/docs/hook-coverage-qa-notes.md` - Temporal QA notes

**Overlap:** ~80% - All are temporal reports with no ongoing value

**Consolidation Plan:**
```
Archive to: docs/archive/2026-05-28/

Actions:
1. Move all temporal reports to docs/archive/2026-05-28/
2. Update docs/archive/INDEX.md with new entries
3. Delete reports/ directory (move to archive)
4. Delete artifacts/testing/ directory (move to archive)
5. Keep only current production invariants and active test catalogs
```

**Rationale:** Temporal reports clutter documentation. Archive by date with proper registry.

---

## Consolidation Opportunity 9: JSON Baselines

**Current State:**
- `docs/reference/migration-safety-baseline.json` - 74997 bytes
- `docs/reference/readiness-language-baseline.json` - 3891 bytes
- `docs/reference/deprecation-drift-baseline.json` - 12143 bytes
- `docs/governance/deprecations.json` - 14672 bytes
- `docs/governance/deprecation-debt-registry.json` - 1080 bytes
- `docs/governance/layer-quality-scorecard.json` - 5193 bytes
- `docs/governance/layer-quality-threshold-policy.json` - 371 bytes

**Overlap:** ~0% - These are configuration files, not documentation

**Consolidation Plan:**
```
Move to: config/baselines/

Actions:
1. Create config/baselines/ directory
2. Move all JSON baselines to config/baselines/
3. Update references in code to point to new location
4. Keep governance JSON files in docs/governance/ (referenced by docs)
```

**Rationale:** JSON baselines are configuration, not documentation. Move to config/ directory.

---

## Consolidation Opportunity 10: Large Files

**Current State:**
- `docs/ROADMAP.md` - 4650 lines, likely outdated
- `docs/reference/layer4-route-contract-matrix.md` - 49756 bytes, very large
- `docs/ValuePack_Framework_v2.0.md` - 1437 lines, product framework

**Overlap:** ~0% - Different content

**Consolidation Plan:**
```
Split/Archive:

1. ROADMAP.md:
   - Review for current relevance
   - If outdated, archive to docs/archive/2026-05-28/
   - If current, split into smaller sections

2. layer4-route-contract-matrix.md:
   - Consider moving to contracts/ (it's a contract matrix)
   - Or split into smaller layer-specific files

3. ValuePack_Framework_v2.0.md:
   - Move to packs/ (it's about ValuePacks)
   - Or create docs/packs/ directory
```

**Rationale:** Large files are hard to navigate. Split or relocate to appropriate directories.

---

## Consolidation Summary

| Opportunity | Files Involved | Action | Complexity |
|--------------|---------------|--------|------------|
| Architecture | 4 files | Merge into docs/core-concepts/architecture.md | Low |
| Security | 7 files | Merge into docs/core-concepts/security-model.md | Medium |
| API Reference | 7 files | Merge into docs/reference/api-overview.md | Low |
| Testing | 7 files | Create testing handbook, archive temporal | Medium |
| Governance | 8 files | Merge into compatibility-debt-registry.md | Medium |
| Getting Started | 4 files | Create unified onboarding guide | Medium |
| Providers | 3 files | Expand Providers.md to comprehensive catalog | Low |
| Temporal Reports | 30+ files | Archive to docs/archive/2026-05-28/ | Low |
| JSON Baselines | 7 files | Move to config/baselines/ | Low |
| Large Files | 3 files | Split or relocate | High |

**Total Files Affected:** ~80 files

**Priority:**
1. **High Priority:** Temporal Reports (quick win, high impact)
2. **High Priority:** JSON Baselines (wrong location)
3. **Medium Priority:** Getting Started (user-facing)
4. **Medium Priority:** Architecture (consolidation)
5. **Medium Priority:** API Reference (consolidation)
6. **Low Priority:** Security (consolidation)
7. **Low Priority:** Testing (consolidation)
8. **Low Priority:** Governance (consolidation)
9. **Low Priority:** Providers (expansion)
10. **Low Priority:** Large Files (review needed)

---

## Next Steps

**Phase 4: Archive vs Update Decision Matrix** - Decide keep/update/archive for each file
**Phase 5: README as Navigation Layer** - Propose new README structure
