# Repo Hygiene Report Governance Check (Non-Blocking)

## Purpose

Provide a lightweight documentary control so cleanup debt is always actionable and traceable.

## Scope

Applies to future reports under `reports/` that summarize repository cleanup, hygiene, or artifact-removal work.

## Required Metadata for Unresolved Items

Every unresolved checklist item MUST include:

1. **Owner** (team or role accountable for closure)
2. **Target date** (YYYY-MM-DD)
3. **Tracking ID** (issue/work item identifier)

## Check Procedure (Documentary)

- During report authoring or review, confirm unresolved items include all three metadata fields.
- If metadata is missing, the report should be revised before approval/merge.
- This check is **non-blocking CI** and enforced through documentation review discipline.

## Suggested Snippet

Use the following format near unresolved items:

```markdown
- Tracked Issue: RH-2026-001
- Owner: Dev Productivity
- Target Date: 2026-05-20
```
