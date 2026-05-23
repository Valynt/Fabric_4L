# Frontend Cleanup Summary

This document tracks frontend cleanup claims and verification status.

## Completed — Sprint 3 (FIX-002)

- **TypeScript errors**: Resolved all `tsc --noEmit` errors across `apps/web/src/` (from ~31 down to 0).
  - Fixed merge-conflict markers in `usePersistFn.ts` (FIX-001).
  - Added placeholder generated types for `l4`/`l5` (`api/generated/l4/index.ts`, `l5/index.ts`).
  - Fixed `withApiError` arity in `useValueSignals.ts`.
  - Fixed `useTargets.ts` missing `schedule` property and unsafe `ApiTargetSummary` access.
  - Fixed `useAccounts.ts`, `useL5Governance.ts` type issues.
  - Fixed `GovernanceAuditTrail.tsx` type mismatch and export cast.
  - Fixed `GovernanceCompliance.tsx` `DataTable` generic inference.
  - Fixed `HypothesesTab.tsx` `usePersistWorkspaceTab` usage and driver/linkage typing.
  - Fixed `TargetsAdmin.detail.tsx` schedule null-safety.
  - Fixed `TargetsAdmin.form.tsx` Zod v4 / `@hookform/resolvers` v5 mismatch.
  - Fixed `DriverTreePage.tsx` navigation to valid `RouteState`.
  - Fixed `useAgentEvents.ts` `workflowId` undefined in `runMetadataIds`.
  - Added missing `QK.versions.list` and `QK.workspace.accountTab` query key factories.
  - Added non-hook async utilities `getOrCreateCanonicalCaseId` and `persistWorkspaceTab` to `useWorkspaceCase.ts`.

## Test Fixes

- Fixed `GovernanceAuditTrail.test.tsx` and `TeamAccessPages.test.tsx` mocks to include `getCapabilityDecision` (was missing from `useSettingsAccess` mock).
- Remaining pre-existing test failures (not caused by Sprint 3 changes):
  - `HypothesisValidationToDriverFlow.test.tsx`: test asserts `.pathname` on a string `navigate` argument (test bug).
  - `DecisionTrace.test.tsx`: MSW handler timeout (pre-existing).
  - `ProspectSetup.submission.test.tsx`: test timeouts (pre-existing).
