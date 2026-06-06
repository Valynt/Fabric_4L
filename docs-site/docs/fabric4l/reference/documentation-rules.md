---
owner: docs-team
status: draft
last_reviewed: 2026-06-06
---

# Documentation Rules

## Source of truth

- Product docs are the source of truth for how users experience ValuePact.
- API docs are the source of truth for external integration behavior.
- ADRs are the source of truth for architectural decisions.
- Security readiness gates are the source of truth for production safety requirements.
- Behavior contracts are the source of truth for intended behavior.
- Runbooks are the source of truth for operational response.
- Generated API docs are not hand-edited.

## Required front matter

Each durable page should eventually include:

owner: team-or-person
status: draft | active | deprecated
last_reviewed: YYYY-MM-DD

## Page lifecycle

- Draft: useful but incomplete
- Active: current and maintained
- Deprecated: preserved for history, no longer authoritative

## Review rule

Any production-critical doc must be reviewed when the related implementation changes.
