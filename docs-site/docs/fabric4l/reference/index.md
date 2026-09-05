---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Reference

This section contains authoritative reference materials for the ValuePact platform. Unlike tutorials or how-to guides, reference pages are optimized for lookup: they are structured, comprehensive, and maintained in lockstep with the codebase.

## What belongs in Reference

- Definitions, taxonomies, and glossaries
- Canonical file paths and source-of-truth locations
- Command quick-reference cards
- Link directories to external and internal documentation
- Documentation conventions and page templates

## What does not belong in Reference

- Step-by-step tutorials
- Procedural runbooks (those belong in Operations)
- Architectural decision rationale (those belong in ADRs)
- Product marketing or narrative explanations

## Sections

- [Glossary](glossary.md) — Comprehensive definitions of platform, architecture, and testing terminology.
- [Links](links.md) — Important internal documentation links, source-of-truth files, and external references.
- [Documentation Rules](documentation-rules.md) — Diataxis structure, page templates, front matter, review process, and code example standards.

## Page index

### Glossary

The [Glossary](glossary.md) defines over 60 terms across six categories:

- **Platform** — ValuePact, Value Fabric, six-layer architecture, pack, tenant, tenant isolation
- **Architecture** — layer, service, source-of-truth path, compatibility shim, API gateway, middleware
- **Layer-specific** — ingestion job, ontology, GraphRAG, LangGraph, checkpoint, TruthObject, maturity ladder, benchmark dataset
- **Testing** — behavior contract, readiness ladder, drift, tenant boundary, fail closed, behavior debt, waiver
- **Frontend** — PageShell, right rail, horizontal tabs, TanStack Query, shadcn/ui
- **Security** — RLS, OWASP Top 10, auth bypass, ProductionSafetyValidator, audit log, correlation ID

Use the glossary when writing behavior contracts, runbooks, or ADRs to ensure consistent terminology.

### Links

The [Links](links.md) page is a curated directory of:

- Internal source-of-truth files (architecture, governance, configuration, baselines)
- Runtime source-of-truth paths for all six layers plus the API gateway
- Contract artifacts (OpenAPI, JSON Schema, tool manifests, behavior contract)
- Test suite directories (contract, security, backend integrated, chaos, abuse)
- External references (FastAPI, Neo4j, PostgreSQL, Celery, Playwright, LangGraph, etc.)
- Quick reference card with the most-visited commands and file paths

Bookmark this page for daily development.

### Documentation Rules

The [Documentation Rules](documentation-rules.md) page specifies:

- Diataxis quadrant boundaries and directory conventions
- Required front matter (`owner`, `status`, `last_reviewed`)
- Page template requirements (H1, lead paragraph, tables, admonitions, related docs)
- When to update docs (same-PR rule)
- Review checklist for docs changes
- Link conventions for internal and external references
- Code example standards for bash, Python, TypeScript/JSX, and file paths
- Admonition syntax and table formatting rules
- Terminology and style guide

## How to use this section

| If you need to… | Go to… |
|---|---|
| Understand a term like "TruthObject" or "tenant boundary" | [Glossary](glossary.md) |
| Find the canonical path for a runtime module or OpenAPI spec | [Links](links.md) |
| Know when to update docs and which template to use | [Documentation Rules](documentation-rules.md) |
| Check the correct MkDocs admonition syntax | [Documentation Rules](documentation-rules.md) |
| Look up a pytest marker definition | [Links](links.md) → `pytest.ini` |
| Find the behavior contract baseline | [Links](links.md) → `config/ci/behavior_contract_baseline.json` |
| Verify external dependency documentation | [Links](links.md) → External references table |

## Maintenance schedule

Reference pages are maintained continuously, not on a fixed calendar. Update rules:

| Trigger | Action |
|---|---|
| New capability added to behavior contract | Update Glossary and Links |
| New layer or service introduced | Update Links runtime paths and Glossary layer terms |
| New external dependency adopted | Update Links external references |
| Docs site theme or syntax changes | Update Documentation Rules |
| Quarterly review | Verify all `last_reviewed` dates; update stale pages |

!!! tip "Reference pages are active documents"
    Every page in this section carries `status: active` and a `last_reviewed` date. If you find outdated content, file a docs-debt ticket and update the page in the same PR as the code change that made it stale.

## Related documentation

- `docs/development/DISCOVERY_MAP.md` — Routes issue types to source-of-truth files, drift checks, and validation commands
- `AGENTS.md` — Concise agent entry point with links to scoped guidance
- `DESIGN.md` — Frontend design system and UX governance
- `docs/governance/behavior-first-testing.md` — Canonical testing governance
