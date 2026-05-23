# Frontend Cleanup Summary

This document tracks frontend cleanup claims and verification status.

## Completed — Sprint 3

### FIX-001: Merge Conflict Markers
- **File:** `apps/web/src/hooks/usePersistFn.ts`
- Removed unresolved `<<<<<<< HEAD` / `=======` / `>>>>>>>` markers from timed-out subagent.

### FIX-002: TypeScript Errors (0 errors)
- Resolved all `tsc --noEmit` errors across `apps/web/src/` (from ~34 down to 0).
- Key fixes:
  - Added placeholder generated types for `l4`/`l5` (`api/generated/l4/index.ts`, `l5/index.ts`).
  - Fixed `withApiError` arity in `useValueSignals.ts`.
  - Fixed `useTargets.ts` missing `schedule` property and unsafe `ApiTargetSummary` access.
  - Fixed `GovernanceAuditTrail.tsx` type mismatch and export cast.
  - Fixed `GovernanceCompliance.tsx` `DataTable` generic inference.
  - Fixed `HypothesesTab.tsx` `usePersistWorkspaceTab` usage and driver/linkage typing.
  - Fixed `TargetsAdmin.detail.tsx` schedule null-safety.
  - Fixed `TargetsAdmin.form.tsx` Zod v4 / `@hookform/resolvers` v5 mismatch.
  - Fixed `DriverTreePage.tsx` navigation to valid `RouteState`.
  - Fixed `useAgentEvents.ts` `workflowId` undefined in `runMetadataIds`.
  - Added missing `QK.versions.list` and `QK.workspace.accountTab` query key factories.
  - Added non-hook async utilities `getOrCreateCanonicalCaseId` and `persistWorkspaceTab` to `useWorkspaceCase.ts`.

### FIX-003: Test Fixes
- Fixed `GovernanceAuditTrail.test.tsx` & `TeamAccessPages.test.tsx`: added missing `getCapabilityDecision` to mocks.
- Fixed `useAuth.test.ts`: hardened `safeAsync` to handle non-Promise arguments gracefully.
- Remaining pre-existing test failures (2 tests, 2 files):
  - `HypothesisValidationToDriverFlow.test.tsx`: test asserts `.pathname` on a string `navigate` argument (test bug).
  - `ground-truth.contract.test.ts`: test provides 2 history items but asserts length 3 (test data/expectation mismatch).

### FE-002a: Async Error Handling (8 files)
- **`useWorkflows.ts`**: Added `.catch()` to all `queryClient.invalidateQueries()` calls in `onSuccess` handlers to prevent unhandled rejections.
- **`AuthContext.tsx`**: Wrapped session restore `useEffect` in try/catch; wrapped `authClient.logout()` in try/catch inside `logout`.
- **`ExportMenu.tsx`**: Added `toast.error()` in catch block for export failures.
- **`TasksPage.tsx`**: Switched `updateTask.mutate` to `mutateAsync` with try/catch + `toast.error`.
- **`NotificationsPage.tsx`**: Switched `markRead.mutate` to `mutateAsync` with try/catch + `toast.error`.
- **`DecisionTrace.tsx`**: Added `toast.error()` to `handleExportProvO` catch block.
- **`ValuePacks.tsx`**: Added `toast.success()` on deploy success and `toast.error()` on deploy failure.
- **`lib/async.ts`**: Hardened `safeAsync` to guard against non-Promise inputs.

### FE-007: ARIA Labels (9 files)
- **`VariableRegistry.tsx`**: Added `role="tab"`, `aria-selected` to tab buttons; `aria-label` to search input and filter selects; `aria-label` to expand/collapse chevrons.
- **`FormulaGovernance.tsx`**: Added `role="tab"`, `aria-selected` to tab buttons; `aria-label` to search input; `aria-pressed` to status filter buttons.
- **`PropertyEditor.tsx`**: Added `aria-label="Delete property"` to icon-only delete button.
- **`PersonalProfile.tsx`**: Added `aria-label` to Configure buttons with item context.
- **`PersonalSecurity.tsx`**: Added `aria-label` to Enable and Connect buttons.
- **`ProspectPromptBuilder.tsx`**: Already compliant — icon-only buttons have `aria-label`.
- **`FormulaBuilder.tsx`**: Already compliant — inputs have labels and `aria-invalid`/`aria-describedby`.
- **`login-form.tsx`**: Already compliant — password toggle has `aria-label`, alerts have `role`.
- **`pagination.tsx`**: Already compliant — `aria-label`, `aria-current`, `sr-only` ellipsis text.

### CI / Lint Gate
- `node scripts/quality/assert-frontend-hygiene.mjs` → **passes**
- `npx tsc --noEmit` → **EXIT 0**

## Validation Commands

```bash
# Typecheck
npx tsc --noEmit

# Frontend hygiene
node scripts/quality/assert-frontend-hygiene.mjs

# Unit tests
npx vitest run
```
