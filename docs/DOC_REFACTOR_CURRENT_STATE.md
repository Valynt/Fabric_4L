# Documentation Refactor — Phase 0: Current State Report

**Date:** 2026-07-15
**Branch:** `docs/refactor-methodology`
**Scope:** All `.md` files in the Fabric_4L monorepo (excluding `node_modules` and `.git`)
**Method:** Read-only inventory. No files modified.

---

## 1. Scale

| Metric | Count |
|--------|-------|
| Total `.md` files | 1,765 |
| Root-level `.md` files | 14 |
| `docs/` directory `.md` files | ~1,400+ |
| `docs-site/` directory `.md` files | 166 |
| Service/app-level `.md` files | ~50+ |
| Agent instruction files (`.agent/`, `.agents/`, `.devin/`, `.fabric/`) | ~100+ |

---

## 2. Root-Level Files — Classification

| File | Classification | Notes |
|------|---------------|-------|
| `README.md` | **Authoritative** | Entry point; quickstart claims need reconciliation with `AGENTS.md` (DOC-002) |
| `AGENTS.md` | **Authoritative** | Comprehensive agent operating contract; references missing `.windsurf/AGENTS.md` (AGENT-001) |
| `ARCHITECTURE.md` | **Authoritative** | Thin index pointing to `docs/architecture/`; claims verified against codebase |
| `SECURITY.md` | **Authoritative** | Vulnerability reporting policy; dev bypass documented |
| `DESIGN.md` | **Authoritative** | Frontend governance; required reading before `apps/web` changes |
| `CONTRIBUTING.md` | **Authoritative** | Contributor guidelines |
| `CLAUDE.md` | **Authoritative** | Claude-specific agent instructions |
| `GEMINI.md` | **Authoritative** | Gemini-specific agent instructions |
| `CHANGELOG.md` | **Authoritative** | Release history |
| `ROADMAP.md` | **Authoritative** | Product roadmap |
| `PRODUCTION_READINESS_REPORT.md` | **Historical** | Snapshot report; not a living document |
| `REPO_AUDIT.md` | **Historical** | Audit snapshot (2026-07-15); not a living document |
| `AUDIT_REMEDIATION_ROADMAP.md` | **Derived** | Remediation plan derived from `REPO_AUDIT.md` |
| `PROMPTS.md` | **Derived** | Agent execution prompts derived from audit findings |

---

## 3. Key Structural Issues

### 3.1 Duplicate Topic Coverage

The following topics have multiple competing documents with no clear canonical owner:

| Topic | Competing Files | Problem |
|-------|----------------|---------|
| **Architecture** | `ARCHITECTURE.md`, `docs/architecture.md`, `docs/architecture_overview.md`, `docs/architecture/system-overview.md`, `docs-site/docs/fabric4l/architecture/system-overview.md` | 5+ files; root `ARCHITECTURE.md` is a thin index but `docs/architecture.md` and `docs/architecture_overview.md` are standalone |
| **Runbooks** | `docs/operations/RUNBOOK.md`, `docs/operations/runbook-overview.md`, `docs/runbooks/00-runbook-index.md`, `docs/LAUNCH_RUNBOOK.md`, `docs/drills/DRILL-RUNBOOK.md`, `monitoring/jaeger-storage-runbook.md` | 6+ files; `docs/runbooks/00-runbook-index.md` is the most comprehensive index |
| **Security** | `SECURITY.md`, `docs/SECURITY_FIXES_SUMMARY.md`, `docs/SECURITY_FIXES_EXECUTION_LOG.md`, `docs/MCP_GATEWAY_SECURITY_ASSESSMENT_2026-04-24.md`, `docs/SECURITY_TRIAGE_RUBRIC.md` + 10+ archived | Root `SECURITY.md` owns policy; others are historical/derived |
| **Operations** | `docs/operations/RUNBOOK.md`, `docs/operations/runbook-overview.md`, `docs/operations/operational-kpis-scorecard.md`, `services/layer4-agents/docs/OPERATIONS.md` | Scattered; no single root entry point |
| **API Reference** | `docs/API_REFERENCE.md`, `docs/api/README.md`, `docs/api-contract.md`, `docs/api-contracts/user-workflow-apis.md`, `docs-site/docs/api/` | Multiple competing API docs |
| **Contributing** | `CONTRIBUTING.md`, `docs/CONTRIBUTING-additions.md` | Additions file has 0 inbound links; likely orphaned |

### 3.2 Missing Referenced Files

| Reference Location | Missing File | Impact |
|-------------------|-------------|--------|
| `AGENTS.md:6` | `.windsurf/AGENTS.md` | Agent confusion — cross-agent coordination registry not found |

### 3.3 Orphaned Documents (0 inbound links from root/docs)

The following `docs/` root files have zero inbound links from `AGENTS.md`, `README.md`, or `ARCHITECTURE.md`:

- `docs/CONTRIBUTING-additions.md`
- `docs/RELEASE_READINESS.md`
- `docs/WORKFLOW_API_DESIGN.md`
- `docs/WORKFLOW_MOCK_DATA_STATUS.md`
- `docs/contract-dashboard.md`
- `docs/health-scorecard.md`
- `docs/how-to-progressive-enforcement-rollout.md`
- `docs/layer3_route_ownership.md`
- `docs/legacy-table-tabs-followup.md`
- `docs/plan-harness-mvp.md`

### 3.4 Parallel Documentation Trees

The repository has **three parallel documentation trees** with overlapping content:

| Tree | Path | Purpose | Files |
|------|------|---------|-------|
| Internal engineering docs | `docs/` | Developer-facing; ADRs, runbooks, architecture, governance | ~1,400 |
| Published docs site | `docs-site/` | User-facing; tutorials, how-to, reference | 166 |
| Source of truth originals | `docs/_SOURCE OF TRUTH/` | Original design briefs; PDFs and raw docs | 8 |

These trees are not linked to each other and have overlapping architecture and security content.

### 3.5 Archive Policy

The `docs/archive/` directory contains dated snapshots. The archive policy appears to be working (files are prefixed `ARCHIVED_`), but the archive has grown to include multiple subdirectories with hundreds of files that are no longer referenced.

---

## 4. Validation Findings (Phase 1 Preview)

| Document | Claim | Reality | Verdict |
|----------|-------|---------|---------|
| `ARCHITECTURE.md` | FastAPI across all services | 409 FastAPI imports confirmed | ✅ Accurate |
| `ARCHITECTURE.md` | Celery/Redis in Layer 1 | 125 Celery references in L1 `src/` | ✅ Accurate |
| `ARCHITECTURE.md` | Six-layer core + adjacent billing/signal | Confirmed by service directory structure | ✅ Accurate |
| `docs/architecture/system-overview.md` | Celery/Redis in Layer 1 diagram | Confirmed | ✅ Accurate |
| `ARCHITECTURE.md` | Redis Streams | Zero `XADD`/`XREAD` references in `services/` | ⚠️ Not implemented (Kafka comment in L1 orchestrator suggests it was planned) |
| `ARCHITECTURE.md` | Kafka | Zero production Kafka imports; only test fixtures and comment references | ⚠️ Planned but not implemented — not documented as such |
| `docs/DOCUMENTATION_AUDIT_REPORT.md` | Status: archived (2026-05-03) | Correctly self-marked as archived | ✅ Accurate |

---

## 5. Canonical Ownership Map (Phase 2 Preview)

| Topic | Proposed Canonical Owner | Current State |
|-------|-------------------------|--------------|
| Architecture overview | `ARCHITECTURE.md` (thin index) → `docs/architecture/system-overview.md` | Partially implemented |
| Security policy | `SECURITY.md` | Correct; others are derived/historical |
| Agent instructions | `AGENTS.md` (root) → nested `AGENTS.md` per service | Partially implemented; `.windsurf/AGENTS.md` missing |
| Runbooks | `docs/runbooks/00-runbook-index.md` | Exists but not linked from root |
| API contracts | `packages/platform-contract/CONTRACT.md` | Correct; others should link here |
| Contributing | `CONTRIBUTING.md` | Correct; `docs/CONTRIBUTING-additions.md` should be merged or removed |
| Operations entry point | **Missing** — `RUNBOOK.md` at root needed | Gap identified (REL-001) |

---

## 6. Recommended Action Sequence

Based on this inventory, the following phases will proceed in order:

1. **Phase 1** — Validate `ARCHITECTURE.md`, `README.md`, `AGENTS.md`, and `docs/architecture/system-overview.md` against codebase reality. Assign confidence scores.
2. **Phase 2** — Declare canonical ownership per topic. Update `ARCHITECTURE.md` to note Redis Streams and Kafka as planned-not-implemented.
3. **Phase 3** — Merge `docs/CONTRIBUTING-additions.md` into `CONTRIBUTING.md`. Remove orphaned docs or add redirect stubs.
4. **Phase 4** — Extract `RUNBOOK.md` root entry point from `docs/runbooks/00-runbook-index.md` (REL-001). Create `.windsurf/AGENTS.md` stub (AGENT-001).
5. **Phase 5** — Create `.ai/` context layer summarising the authoritative docs.
6. **Phase 6** — Run link validation and produce final audit.

---

*This report is read-only output. No files were modified during Phase 0.*
