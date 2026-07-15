# AI Memory — Value Fabric (Fabric_4L)

> **This file records key architectural decisions and lessons extracted from ADRs, the audit, and the refactoring process.**
> Sources: `docs/explanations/adr/`, `REPO_AUDIT.md`, `docs/DOC_REFACTOR_CURRENT_STATE.md`.
> It is a summary — always read the primary sources for full context.

---

## Architectural Decisions (Key ADRs)

| Decision | ADR | Status | Summary |
|----------|-----|--------|---------|
| Six-layer pipeline architecture | ADR-002 | Accepted | Core pipeline is L1–L6; billing (L7) and signal refinery are adjacent deployable capabilities, not core layers |
| PostgreSQL RLS for multi-tenancy | ADR-010 | Accepted | Row-level security enforced at DB layer; application middleware sets `tenant_id` per request |
| Hybrid graph database (Neo4j + pgvector) | ADR-002 | Accepted | Neo4j for graph traversal; pgvector for vector similarity; both in L3 |
| Contract-first development | Platform Contract | Accepted | All cross-layer boundaries declared in `contracts/`; enforced by CI |
| ADR-027: canonical package structure | ADR-027 | Accepted | Runtime packages live in `services/layer*/src/`; legacy root `value_fabric/` shim removed |
| pnpm-only package management | AGENTS.md | Accepted | npm and yarn are forbidden; lockfile must be frozen in CI |

---

## Known Gaps (from REPO_AUDIT.md, 2026-07-15)

| Finding | Description | Sprint |
|---------|-------------|--------|
| SEC-001 | PR workflow permissions are not least-privilege | 1 |
| SEC-002 | MCP bearer token was exposed in a prompt | 1 (human action) |
| AGENT-001 | Root `AGENTS.md` referenced `.windsurf/AGENTS.md` which did not exist | 1 — **RESOLVED** in phase 4 |
| DOC-002 | `README.md` `make setup` claim overclaims (does not start infra or migrate) | 1 |
| TEST-001 | 15 security tests use `xfail(strict=False)` — silent pass on failure | 2 |
| QUAL-001 | No type-escape ratchet; generated files inflate escape counts | 2 |
| CICD-001 | No CI gate map document | 3 — **PARTIALLY RESOLVED** (ownership map created in phase 2) |
| REL-001 | No root runbook entry point | 3 — **RESOLVED** in phase 4 |
| ARCH-001 | Layer 4 analysis route is an oversized hotspot | 4 |

---

## Documentation Refactoring Lessons (2026-07-15)

The following lessons were learned during the `docs/refactor-methodology` branch:

**Never invent architecture.** The `docs/architecture/system-overview.md` file claimed "Redis / RabbitMQ for async Celery tasks." A codebase scan found zero RabbitMQ imports in production code. The claim was corrected to "Redis only (RabbitMQ was planned, not implemented)." Always verify technology claims against `grep` output before documenting.

**Redirect stubs are correct.** `docs/architecture.md` and `docs/architecture_overview.md` are correctly self-marked as redirect stubs pointing to `docs/core-concepts/architecture.md`. This pattern (thin redirect + canonical owner) is the right approach for duplicate topics.

**Orphaned docs accumulate silently.** Ten `docs/` root files had zero inbound links. They were either historical snapshots or planning artifacts that should have been archived when completed. The archive policy (`docs/archive/YYYY-MM-DD/ARCHIVED_*.md`) is working; the gap was that new files were not being archived promptly.

**`docs/CONTRIBUTING-additions.md` was a merge artifact.** It contained onboarding, ADR template, PR checklist, common issues, and mentorship sections that were never merged into `CONTRIBUTING.md`. These sections are now merged and the source file archived.

**The `.windsurf/AGENTS.md` reference was a broken pointer.** The `.windsurf/` directory existed but contained only `REMEDIATION_PLAN.md`, `plans/`, and `workflows/` — no `AGENTS.md`. The actual agent fleet registry was in `.devin/AGENTS.md`. A stub was created at `.windsurf/AGENTS.md` to resolve the broken reference and route agents to the correct sources.

---

## Documentation Structure (Post-Refactor)

The repository now has a clear three-tier documentation structure:

**Tier 1 — Root authoritative files** (`README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `SECURITY.md`, `DESIGN.md`, `CONTRIBUTING.md`, `RUNBOOK.md`): Entry points for humans and agents. Thin indexes pointing to canonical detail.

**Tier 2 — Canonical detail** (`docs/core-concepts/`, `docs/architecture/`, `docs/runbooks/`, `docs/development/`, `docs/explanations/adr/`): Full content, owned by topic, cross-linked.

**Tier 3 — Archive** (`docs/archive/YYYY-MM-DD/ARCHIVED_*.md`): Historical snapshots, correctly dated and prefixed. Not linked from active documentation.
