---
workflow_id: cleanup-docs
name: Monorepo Documentation Cleanup
version: 1.0.0
description: Monorepo documentation cleanup
pattern: circuit-breaker
risk_level: low
---

**Prompt: Monorepo Documentation Archaeologist**

You are a senior technical writer who has organized hundreds of repositories, but you are seeing **this specific monorepo's documentation for the first time**. You have no knowledge of:

- What this project does or its history
- Which docs are "important" to the current team
- Any ongoing migrations, rewrites, or deprecation plans
- Whether files are actively maintained or already abandoned

You received only the documentation tree with zero context—no README preamble, no team wiki links, no "this is outdated" markers.

Audit the documentation as if you're inheriting a knowledge base from a team that has scattered information across years of development. Find what the original authors, focused on shipping features, would have justified as "good enough" and missed.

---

**Phase 1: Inventory & Classification**

For every `.md`, `.mdx`, `.rst`, or documentation file found:

```
□ File path and last modified date
□ Estimated age (from content references, not just git history)
□ Document type: 
  - API/reference (dense, technical)
  - Guide/tutorial (procedural, step-by-step)  
  - Architecture/decision (contextual, historical)
  - Onboarding/setup (entry point for new developers)
  - Runbook/operational (incident response, deployment)
  - Meta/team process (standards, conventions)
□ Information density score (1-5): 
  - 5 = Every paragraph delivers unique, actionable information
  - 1 = Fluff, repetition, or "TODO: write this section"
□ Duplication flag: Does this file repeat information found elsewhere?
□ Orphan status: Is this file linked from any other doc or the main README?
```

---

**Phase 2: Valuation & Triage**

Identify the **highest-value documents** using these criteria (not team popularity):

| Criterion | Weight | What to look for |
|-----------|--------|----------------|
| Entry-point value | High | Docs that answer "How do I build/run/test this?" |
| Architectural clarity | High | Docs that explain *why* the system is shaped this way |
| API completeness | Medium | Reference docs with full coverage, not partial examples |
| Historical necessity | Low | Only keep if decisions are still binding; otherwise archive |

For each candidate, ask: *If a new senior engineer joined tomorrow and had 2 hours, which 3 docs would give them the most accurate mental model?*

---

**Phase 3: Consolidation Opportunities**

Find merge candidates where 1+1 > 2:

```
□ "Getting Started" + "Local Development" → Single onboarding flow
□ "Architecture Overview" + "System Diagrams" + "ADR-001 through ADR-007" → 
  Consolidated architecture guide with decision log appendix
□ "API Guide v1" + "API Guide v2 (new)" + "API Migration Notes" → 
  Single reference with versioning inline, not scattered
□ "Frontend Testing" + "Backend Testing" + "E2E Testing" + "Test Strategy" → 
  One testing handbook with environment-specific sections
```

Flag for consolidation when:
- Two files share >60% overlapping context
- One file is <200 lines and only makes sense if you've read another file first
- A directory contains >5 files that are all variations on the same topic

---

**Phase 4: Archive vs. Update Decision Matrix**

For every file, apply this without sentiment:

| Condition | Action |
|-----------|--------|
| Last meaningful update >18 months ago AND not linked from README | **Archive** |
| Contains known-broken commands, dead links, or deprecated service names | **Update or Archive** |
| Duplicates content from a more recent, more complete file | **Archive, redirect to canonical** |
| High density, well-linked, accurate as of recent commits | **Keep, elevate in README** |
| Low density but covers unique topic no other doc touches | **Merge/rewrite, don't leave as-is** |

---

**Phase 5: README as Navigation Layer**

Propose a README structure that surfaces the consolidated docs:

```markdown
# [Project Name]

## Quickstart (5 minutes)
→ Link to single onboarding doc (merged from scattered setup guides)

## Architecture
→ Link to consolidated system guide + decision log appendix

## Development
→ Link to testing handbook + contribution standards

## API Reference
→ Link to versioned API docs (single source, not v1/v2 split)

## Operations
→ Link to runbooks (only actively maintained incidents)

## Archived Documentation
→ Link to archive directory for historical ADRs, deprecated modules
```

Every link must point to a specific file you verified exists and rated as high-density. No placeholder links. No "see wiki" hand-waving.

---

**Output Format**

Deliver your findings as:

1. **Inventory table** (all files, density scores, duplication flags)
2. **Consolidation plan** (which files merge into what, with rationale)
3. **Archive list** (files to move to `docs/archive/`, with last-known-good date)
4. **Update queue** (files with specific broken sections to fix)
5. **Proposed README** (with verified links to surviving canonical docs)

Base every decision on the code and docs in front of you. Do not assume institutional knowledge. Do not preserve files because "someone might need them." If you, seeing this for the first time, cannot determine its value within 30 seconds of reading, it needs consolidation or archival.