# UI Component Canonicalization Note

## Canonical UI primitives

The **canonical production UI primitive library** is:

- `frontend/client/src/components/ui`

All active product code must import UI primitives from this tree (typically through the `@/components/ui/*` alias).

## Duplicate inventory scope

This migration inventory compares component filenames across:

- `_ui-prototype/app/src/components/ui`
- `_ui-prototype/app-value-old/src/components/ui` (path does not exist as of 2026-04-29)
- `frontend/client/src/components/ui`

## Decision policy

- **Migrate**: keep and evolve in `frontend/client/src/components/ui`.
- **Archive**: keep prototype copies only under a non-production namespace.
- **Delete**: remove dead prototype artifacts that are superseded and not needed for reference.
