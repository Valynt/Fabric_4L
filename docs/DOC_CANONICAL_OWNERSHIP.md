# Documentation Refactor — Phase 2: Canonical Ownership Map

**Date:** 2026-07-15
**Branch:** `docs/refactor-methodology`
**Rule:** Only one document owns a topic. All others must link to the owner, not duplicate content.

---

## Ownership Table

| Topic | Canonical Owner | All Other Files Must... | Notes |
|-------|----------------|------------------------|-------|
| **Architecture overview** | `docs/core-concepts/architecture.md` | Link to it | `ARCHITECTURE.md` (root) is the correct thin index; `docs/architecture.md` and `docs/architecture_overview.md` are correct redirect stubs |
| **System overview / C4 diagrams** | `docs/architecture/system-overview.md` | Link to it | Detailed diagrams live here; `docs/core-concepts/architecture.md` summarises and links |
| **Security policy** | `SECURITY.md` | Link to it | All security fix logs, triage rubrics, and assessments are **derived/historical** |
| **Agent operating contract** | `AGENTS.md` (root) | Nested `AGENTS.md` files add service-specific overrides only | `.windsurf/AGENTS.md` must be created as a cross-agent registry stub |
| **Claude-specific instructions** | `CLAUDE.md` | — | Standalone; no duplication expected |
| **Gemini-specific instructions** | `GEMINI.md` | — | Standalone; no duplication expected |
| **Frontend governance** | `DESIGN.md` (root) + `apps/web/DESIGN.md` | Link to root `DESIGN.md` for platform rules | `apps/web/DESIGN.md` owns component-level rules |
| **Contributing guidelines** | `CONTRIBUTING.md` | Link to it | `docs/CONTRIBUTING-additions.md` must be merged in or archived |
| **API contracts** | `packages/platform-contract/CONTRACT.md` | Link to it | `docs/api-contract.md`, `docs/api-contracts/`, `docs/API_REFERENCE.md` should link here |
| **API reference** | `docs/api/README.md` | Link to it | `docs/API_REFERENCE.md` should redirect |
| **Runbooks / incident response** | `docs/runbooks/00-runbook-index.md` | Link to it | `docs/operations/RUNBOOK.md` and `docs/operations/runbook-overview.md` are supplementary; a root `RUNBOOK.md` stub should point here |
| **Operations entry point** | `docs/operations/RUNBOOK.md` (short-form) | — | Needs a root-level pointer (REL-001 gap) |
| **CI gate map** | `docs/development/CI_GATES.md` (to be created — CICD-001) | Link to it | Currently scattered across Makefile comments |
| **Build system / commands** | `docs/development/BUILD_SYSTEM.md` | Link to it | `docs/development/COMMANDS.md` is a companion; both are referenced from `AGENTS.md` |
| **ADRs / decisions** | `docs/explanations/adr/` | Link to index | `docs/decisions/README.md` should redirect to ADR index |
| **Threat model** | `THREAT_MODEL.md` (to be created — DOC-THREAT) | Link to it | Currently missing at root |
| **Changelog** | `CHANGELOG.md` | — | Authoritative release history |
| **Product roadmap** | `ROADMAP.md` | — | Authoritative product roadmap |
| **Audit remediation** | `AUDIT_REMEDIATION_ROADMAP.md` | — | Derived from `REPO_AUDIT.md` |
| **Code ownership** | `CODEOWNERS` (to be created — DOC-CODEOWNERS) | — | Currently missing |
| **Testing strategy** | `docs/testing/` index (to be verified) | Link to it | Root `TESTING.md` stub needed (TEST-001 gap) |
| **Deployment** | `docs/deployment/` index | Link to it | Root `DEPLOYMENT.md` stub needed |
| **Supply chain / SBOM** | `docs/SUPPLY_CHAIN.md` | Link to it | |
| **Accessibility policy** | `docs/accessibility_policy.md` | Link to it | `docs/accessibility.md` should redirect |

---

## Ownership Conflict Resolutions

### Architecture (5 competing files → 1 canonical)

```
docs/core-concepts/architecture.md   ← CANONICAL (last-reviewed 2026-06-20)
         ↑
ARCHITECTURE.md (root)               ← thin index, correct
         ↑
docs/architecture/system-overview.md ← detailed diagrams, correct
         ↑
docs/architecture.md                 ← redirect stub, correct
docs/architecture_overview.md        ← redirect stub, correct
```

No changes needed. Ownership is already resolved.

### Runbooks (6 competing files → 1 canonical index)

```
docs/runbooks/00-runbook-index.md    ← CANONICAL INDEX
         ↑
docs/operations/RUNBOOK.md           ← operational quick-reference (keep, link to index)
docs/operations/runbook-overview.md  ← incident severity table (keep, link to index)
docs/LAUNCH_RUNBOOK.md               ← launch-specific (keep in docs/, link from index)
docs/drills/DRILL-RUNBOOK.md         ← drill-specific (keep, link from index)
monitoring/jaeger-storage-runbook.md ← monitoring-specific (keep, link from index)
```

**Gap:** No root-level `RUNBOOK.md` pointer. Phase 4 will create one by extracting from `docs/runbooks/00-runbook-index.md`.

### Security (root + 4 active + 10+ archived)

```
SECURITY.md                          ← CANONICAL (policy)
         ↑
docs/SECURITY_TRIAGE_RUBRIC.md       ← derived (keep, link from SECURITY.md)
docs/MCP_GATEWAY_SECURITY_ASSESSMENT_2026-04-24.md  ← historical (move to archive)
docs/SECURITY_FIXES_SUMMARY.md       ← historical (move to archive)
docs/SECURITY_FIXES_EXECUTION_LOG.md ← historical (move to archive)
```

### Contributing (2 files → 1 canonical)

```
CONTRIBUTING.md                      ← CANONICAL
         ↑
docs/CONTRIBUTING-additions.md       ← orphaned, 0 inbound links → MERGE or ARCHIVE
```

---

## Files That Should Remain Separate (Not Merged)

The following files cover distinct topics and should **not** be merged:

- `AGENTS.md` vs `CLAUDE.md` vs `GEMINI.md` — different agent audiences
- `DESIGN.md` vs `apps/web/DESIGN.md` — platform vs component level
- `docs/development/BUILD_SYSTEM.md` vs `docs/development/COMMANDS.md` — complementary, not duplicates
- `docs/runbooks/00-runbook-index.md` vs individual runbooks — index vs content
- `docs/architecture/system-overview.md` vs `docs/core-concepts/architecture.md` — detailed diagrams vs conceptual overview

---

*No files were modified during Phase 2.*
