# Frontend Legacy Deprecation Migration Status

## Scope

This note tracks deprecated frontend compatibility exports in:

- `apps/web/src/api/legacy.ts`
- `apps/web/src/components/WfPrimitives.tsx`
- `apps/web/src/services/sessionService.ts`

## Canonical migration status (as of 2026-05-12)

- `sessionService.persistSession(...)` internal production usage has been migrated to `persistSessionMeta(...)` in auth/signup flows.
- `@/api/legacy` has no in-repo runtime consumers and remains as a compatibility shim only.
- `@/components/WfPrimitives` still has in-repo consumers; migration remains active and is now explicitly tracked by the legacy-removal policy check.

## Enforcement policy

- Canonical policy constant: `apps/web/src/governance/legacyRemovalPolicy.ts` (`LEGACY_REMOVAL_DATE = 2026-08-31`).
- Guard command: `pnpm --dir apps/web run test:legacy-removals`.
- Before the cutoff date, the guard reports remaining usage for visibility.
- After the cutoff date, the guard fails CI when deprecated imports/usages remain.
