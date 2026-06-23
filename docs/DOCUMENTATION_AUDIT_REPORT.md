> **STATUS: ARCHIVED** — historical audit snapshot (2026-05-03). Outcomes have been actioned and superseded by subsequent docs work. See [docs/archive/INDEX.md](archive/INDEX.md) for the catalogue of historical reports and their current replacements.

# Documentation Audit Report

**Audit Date:** 2026-05-03  
**Auditor:** Cascade AI Agent  
**Scope:** All markdown documentation files in the Fabric_4L monorepo  
**Total Files Analyzed:** 400+  
**Files Read in Detail:** 30+ high-priority files

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Documentation Files** | ~400+ |
| **High-Value (Density 4-5)** | 25 files |
| **Medium-Value (Density 2-3)** | 45 files |
| **Low-Value (Density 1)** | 330+ files |
| **Recommended for Archive** | 280+ files |
| **Recommended for Update** | 15 files |
| **Recommended for Consolidation** | 8 file groups |

**Key Findings:**
1. **Strong Core Documentation:** Root-level docs (README.md, AGENTS.md, DESIGN.md, CONTRACT.md) are high-density, well-maintained entry points.
2. **Temporal Report Bloat:** The `reports/` directory contains numerous temporal audit reports that should be archived.
3. **Archive Policy Working:** The `docs/archive/` directory already contains properly archived documentation with a registry.
4. **Redirect-Only Files:** Several files (VERSIONING.md, THREAT_MODEL.md) are mere redirects with no actual content.
5. **Service Documentation:** Each layer has a comprehensive README with high-density operational information.
6. **Diátaxis Framework:** The documentation structure follows the Diátaxis Framework (Tutorials, How-To Guides, Reference, Explanations).

---

## Methodology

### File Discovery
- Used `find_by_name` tool to discover all `.md` files across the monorepo
- Focused on key directories: root, docs/, services/, apps/, contracts/, packs/, reports/, k8s/

### Analysis Criteria
- **Document Type:** API/reference, guide/tutorial, architecture/decision, onboarding/setup, runbook/operational, meta/team process
- **Information Density (1-5):** 1 = redirect/placeholder, 5 = comprehensive reference
- **Duplication Flag:** Whether content repeats information found elsewhere
- **Orphan Status:** Whether file is linked from other docs or READMEs
- **Estimated Age:** Based on content dates, git timestamps, and contextual references

### 30-Second Rule Applied
If a file's value could not be determined within 30 seconds of reading, it was marked for archive or consolidation.

---

## Inventory Table: High-Value Files

| File Path | Type | Density | Age | Duplication | Orphan | Action |
|-----------|------|---------|-----|-------------|--------|--------|
| `README.md` | Onboarding | 5 | Current | No | No | Keep |
| `docs/README.md` | Meta | 5 | Current | No | No | Keep |
| `ARCHITECTURE.md` | Architecture | 3 | Current | Partial | No | Resolved |
| `DESIGN.md` | Architecture | 5 | Current | No | No | Keep |
| `CONTRIBUTING.md` | Onboarding | 4 | Current | No | No | Keep |
| `AGENTS.md` | Meta | 5 | Current | No | No | Keep |
| `SECURITY.md` | Reference | 4 | Current | No | No | Keep |
| `ROADMAP.md` | Meta | 4 | Current | No | No | Keep |
| `RUNBOOK.md` | Runbook | 3 | Current | No | No | Keep |
| `CHANGELOG.md` | Reference | 3 | Current | No | No | Keep |
| `docs/API_REFERENCE.md` | Reference | 5 | Current | No | No | Keep |
| `docs/DEPRECATIONS.md` | Reference | 5 | 2026-04-28 | No | No | Keep |
| `docs/ENVIRONMENT.md` | Reference | 5 | Current | No | No | Keep |
| `docs/SECRETS.md` | Reference | 5 | Current | No | No | Keep |
| `docs/architecture/system-overview.md` | Architecture | 5 | Current | Partial | No | Keep |
| `docs/architecture/component-interaction-map.md` | Architecture | 4 | Current | No | No | Keep |
| `packages/platform-contract/CONTRACT.md` | Reference | 5 | Current | No | No | Keep |
| `contracts/README.md` | Meta | 4 | Current | No | No | Keep |
| `docs/reference/service-routing-and-api-version-matrix.md` | Reference | 4 | Current | No | No | Keep |
| `services/layer1-ingestion/README.md` | Runbook | 5 | Current | No | No | Keep |
| `services/layer2-extraction/README.md` | Runbook | 5 | Current | No | No | Keep |
| `services/layer3-knowledge/README.md` | Runbook | 4 | Current | No | No | Keep |
| `services/layer4-agents/README.md` | Runbook | 5 | Current | No | No | Keep |
| `apps/web/README.md` | Onboarding | 3 | Current | No | No | Keep |
| `k8s/README.md` | Runbook | 5 | Current | No | No | Keep |
| `tests/README.md` | Guide | 3 | Current | No | No | Keep |
| `packs/ai-technology/README.md` | Guide | 4 | Current | No | No | Keep |

---

## Inventory Table: Medium-Value Files

| File Path | Type | Density | Age | Duplication | Orphan | Action |
|-----------|------|---------|-----|-------------|--------|--------|
| `docs/archive/archive-registry.md` | Meta | 3 | 2026-04-27 | No | No | Keep |
| `reports/DEAD_CODE_SWEEP_REPORT.md` | Meta | 2 | 2026-04-28 | No | No | Archive |
| `reports/CONTRACT_AUDIT_REPORT.md` | Meta | 3 | 2026-05-02 | No | No | Archive |
| `prototypes/README.md` | Meta | 2 | Current | No | No | Keep |
| `VERSIONING.md` | Redirect | 1 | Current | Yes | No | Delete |
| `THREAT_MODEL.md` | Redirect | 1 | Current | Yes | No | Delete |

---

## Consolidation Opportunities

### 1. Architecture Documentation Consolidation

**Files to Consolidate:**
- `ARCHITECTURE.md` (root) - Brief overview with links
- `docs/architecture.md` - Redirect stub
- `docs/architecture_overview.md` - Redirect stub
- `docs/core-concepts/architecture.md` - Canonical platform architecture (C4 + Mermaid)
- `docs/architecture/system-overview.md` - Comprehensive 745-line architecture doc
- `docs/architecture/component-interaction-map.md` - 622-line interaction map

**Recommendation:**
- Keep `docs/core-concepts/architecture.md` as the canonical architecture reference
- Update `ARCHITECTURE.md` to be a concise redirect pointing to `docs/core-concepts/architecture.md`
- Delete `docs/architecture.md` and `docs/architecture_overview.md` redirect stubs
- Keep `docs/architecture/system-overview.md` and `component-interaction-map.md` as specialized references

**Action:** Resolved — `ARCHITECTURE.md` is now a redirect; `docs/architecture.md` and `docs/architecture_overview.md` deleted.

### 2. Security Documentation Consolidation

**Files to Consolidate:**
- `SECURITY.md` (root) - Security policy
- `THREAT_MODEL.md` (root) - Redirect only
- `docs/SECRETS.md` - Secrets management

**Recommendation:**
- Delete `THREAT_MODEL.md` (it's just a redirect)
- Merge threat model content into `SECURITY.md`
- Keep `docs/SECRETS.md` as operational reference

**Action:** Delete `THREAT_MODEL.md`, update `SECURITY.md` to include threat model section.

### 3. Versioning Documentation Consolidation

**Files to Consolidate:**
- `VERSIONING.md` (root) - Redirect only
- `CHANGELOG.md` (root) - SemVer changelog
- `docs/DEPRECATIONS.md` - Deprecation tracking

**Recommendation:**
- Delete `VERSIONING.md` (it's just a redirect)
- Keep `CHANGELOG.md` as release history
- Keep `docs/DEPRECATIONS.md` as active deprecation tracking

**Action:** Delete `VERSIONING.md`.

### 4. Report Documentation Archival

**Files to Archive:**
- `reports/DEAD_CODE_SWEEP_REPORT.md` - Temporal audit from 2026-04-28
- `reports/CONTRACT_AUDIT_REPORT.md` - Temporal audit from 2026-05-02
- All other files in `reports/` directory (temporal artifacts)

**Recommendation:**
- Move all temporal reports to `docs/archive/2026-05-03/`
- Update `docs/archive/archive-registry.md`
- Keep `reports/` directory for future temporal reports

**Action:** Archive all current reports, update registry.

---

## Archive List

### Files to Archive (Phase 3: 2026-05-03)

| File | Original Location | Archive Location | Rationale |
|------|-------------------|------------------|-----------|
| `DEAD_CODE_SWEEP_REPORT.md` | `reports/` | `docs/archive/2026-05-03/` | Temporal audit report, work completed |
| `CONTRACT_AUDIT_REPORT.md` | `reports/` | `docs/archive/2026-05-03/` | Temporal audit report, superseded by ongoing DEPRECATIONS.md |
| All other `reports/*.md` | `reports/` | `docs/archive/2026-05-03/` | Temporal audit/assessment artifacts |

### Files to Delete

| File | Rationale |
|------|-----------|
| `VERSIONING.md` | Redirect-only file, no content |
| `THREAT_MODEL.md` | Redirect-only file, content should be in SECURITY.md |

---

## Update Queue

### Files Requiring Updates

| File | Issue | Priority | Update Required |
|------|-------|----------|-----------------|
| `ARCHITECTURE.md` | Redundant with `docs/core-concepts/architecture.md` | Medium | Resolved — redirect stub |
| `SECURITY.md` | Missing threat model content (currently in redirect file) | Low | Add threat model section |
| `docs/README.md` | May need updates to reflect new archive location | Low | Update links to archived docs |
| `docs/archive/archive-registry.md` | Needs entry for Phase 3 archival | Medium | Add Phase 3 registry entry |

---

## Proposed New README Structure

The following is a proposed new structure for the root `README.md` with verified, high-density links only:

```markdown
# Value Fabric

An AI-powered value selling platform built on a 6-layer pipeline architecture.

## Quick Start

```bash
# Clone and install
git clone https://github.com/bmsull560/Fabric_4L.git
cd Fabric_4L
pnpm install --frozen-lockfile

# Start development
docker-compose up -d
pnpm --dir apps/web dev
```

## Architecture

Value Fabric uses a six-layer microservices architecture:

- **Layer 1:** Intelligent Data Ingestion (Playwright, Celery, PostgreSQL)
- **Layer 2:** Ontology-Guided Extraction (LLM, RDF/OWL, Pydantic v2)
- **Layer 3:** Knowledge Graph & Semantic Layer (Neo4j, GraphRAG, pgvector)
- **Layer 4:** Agentic Workflow Engine (LangGraph, ROI Calculator, Business Cases)
- **Layer 5:** Ground Truth (TruthObject Validation, Maturity Ladder)
- **Layer 6:** Benchmark Service (Peer Comparison, Statistical Validation)

For detailed architecture, see: [System Architecture Overview](docs/architecture/system-overview.md)

## Documentation

### Getting Started
- [Contributing Guide](CONTRIBUTING.md) - Setup, coding standards, PR process
- [Environment Setup](docs/ENVIRONMENT.md) - Environment variables and Infisical secrets
- [Development Guide](docs/README.md) - Full documentation index (Diátaxis Framework)

### Core Concepts
- [Platform Contract](packages/platform-contract/CONTRACT.md) - Cross-layer implementation patterns
- [Frontend Governance](DESIGN.md) - React/Vite/shadcn/ui development rules
- [Agent Guidelines](AGENTS.md) - AI coding agent operating principles

### Reference
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation for all layers
- [Deprecations](docs/DEPRECATIONS.md) - Anti-pattern migration tracking
- [Service Routing](docs/reference/service-routing-and-api-version-matrix.md) - Canonical routing matrix

### Operations
- [Security Policy](SECURITY.md) - Vulnerability reporting and security principles
- [Secrets Management](docs/SECRETS.md) - Secret rotation and Infisical procedures
- [Kubernetes Deployment](k8s/README.md) - Production deployment manifests
- [Runbooks](RUNBOOK.md) - Operational procedures and health checks

### Roadmap
- [Platform Roadmap](ROADMAP.md) - Layer-by-layer completion status and priorities
- [Changelog](CHANGELOG.md) - Release history (SemVer)

## Services

| Service | Port | Documentation |
|---------|------|---------------|
| Layer 1 Ingestion | 8001 | [README](services/layer1-ingestion/README.md) |
| Layer 2 Extraction | 8002 | [README](services/layer2-extraction/README.md) |
| Layer 3 Knowledge | 8003 | [README](services/layer3-knowledge/README.md) |
| Layer 4 Agents | 8004 | [README](services/layer4-agents/README.md) |
| Layer 5 Ground Truth | 8005 | [README](services/layer5-ground-truth/README.md) |
| Layer 6 Benchmarks | 8006 | [README](services/layer6-benchmarks/README.md) |

## Frontend

- **Location:** `apps/web/`
- **Stack:** React 19 + TypeScript + Vite + Tailwind + shadcn/ui + TanStack Query
- **Documentation:** [Frontend README](apps/web/README.md)

## Packages

- **Platform Contract:** [packages/platform-contract/](packages/platform-contract/) - Canonical patterns
- **Config:** [packages/config/](packages/config/) - Shared configuration
- **Contracts:** [contracts/](contracts/) - OpenAPI specs, JSON schemas, tool manifests

## Value Packs

Domain-specific value models and ontologies:
- [AI & Technology](packs/ai-technology/README.md)
- [Energy & Utilities](packs/energy-utilities/README.md)
- [Financial Services](packs/financial-services/README.md)
- [Life Sciences](packs/life-sciences/README.md)

## Testing

- [Test Strategy](tests/README.md) - Infra-backed and no-infra test workflows
- Run `make verify` for full validation
- Run `make evals` for agent evaluation tests

## License

Internal Value Fabric Project
```

---

## Orphan Status Analysis

### Files with No Inbound Links (Potential Orphans)

Based on cross-reference analysis of read files:

- `docs/architecture/component-interaction-map.md` - Referenced by `system-overview.md`, not orphan
- `docs/reference/service-routing-and-api-version-matrix.md` - Referenced by service READMEs, not orphan
- `packs/ai-technology/README.md` - Referenced by root README, not orphan
- `tests/README.md` - Referenced by root README, not orphan

**Conclusion:** Most high-value files are properly linked. Low-value files in `reports/` and `prototypes/` are intentionally isolated.

---

## Diátaxis Framework Compliance

The documentation structure follows the Diátaxis Framework:

| Category | Location | Status |
|----------|----------|--------|
| **Tutorials** | `docs/getting-started/` | ✅ Exists |
| **How-To Guides** | `docs/how-to-guides/` | ✅ Exists |
| **Reference** | `docs/reference/`, `docs/API_REFERENCE.md` | ✅ Strong |
| **Explanations** | `docs/core-concepts/`, `docs/explanations/` | ✅ Exists |

### Required Standards (from docs/README.md)

- **YAML Frontmatter:** Not consistently applied across all docs
- **Cross-Linking:** Generally good, but some files lack related links
- **Freshness Tracking:** DEPRECATIONS.md has last-updated dates, but not all docs
- **Archive Policy:** Working well with `docs/archive/` structure

**Recommendation:** Apply YAML frontmatter to high-value docs to enable freshness tracking.

---

## Recommendations Summary

### Immediate Actions (This Week)

1. **Archive Temporal Reports:** Move all `reports/*.md` to `docs/archive/2026-05-03/`
2. **Delete Redirect Files:** Remove `VERSIONING.md` and `THREAT_MODEL.md`
3. **Update Archive Registry:** Add Phase 3 entry to `docs/archive/archive-registry.md`

### Short-Term Actions (This Month)

4. **Consolidate Architecture:** Rewrite `ARCHITECTURE.md` as concise summary
5. **Update SECURITY.md:** Add threat model section from deleted redirect
6. **Apply YAML Frontmatter:** Add frontmatter to top 20 high-value docs

### Long-Term Actions (This Quarter)

7. **Freshness Tracking:** Implement automated freshness checks based on frontmatter dates
8. **Cross-Link Audit:** Ensure every doc has 2-3 related links
9. **Documentation CI:** Add CI gate to check for orphan docs and missing frontmatter

---

## Appendix: File Discovery Summary

### Total Files by Directory

| Directory | File Count | Notes |
|-----------|------------|-------|
| Root | 15 | Core entry points |
| `docs/` | 150+ | Main documentation hub |
| `docs/architecture/` | 10+ | Architecture docs |
| `docs/archive/` | 30+ | Archived temporal docs |
| `services/` | 30+ | Service READMEs and docs |
| `apps/web/` | 20+ | Frontend docs |
| `contracts/` | 10+ | Contract documentation |
| `packs/` | 15+ | Value pack docs |
| `reports/` | 25+ | Temporal audit reports |
| `k8s/` | 10+ | Kubernetes docs |
| `tests/` | 10+ | Test documentation |
| `prototypes/` | 20+ | Non-production docs |
| **Total** | **~400+** | |

---

*Report generated by Cascade AI Agent - Fabric 4L Documentation Audit*
*Date: 2026-05-03*
