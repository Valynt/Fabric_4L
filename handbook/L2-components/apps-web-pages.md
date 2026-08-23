# L2 Component — apps-web-pages

## Purpose

React/Vite frontend (`apps/web/`). Renders the canonical ValuePilot journey as one continuous
account-scoped workspace. Presents, edits, and dispositions server state; browser storage holds
navigation and presentation caches only — never authoritative domain state (R-2). Authorization
UI fails closed (R-6): loading/denied/expired/tenant-switch states render no protected data.

## Owned journey stages / behaviors

- J-1 / BEH-01 — `src/pages/ProspectSetup.tsx`, `src/pages/Accounts.tsx`, `src/pages/Onboarding.tsx`,
  `src/pages/AcceptInvite.tsx`, `src/pages/SelectOrganization.tsx`; auth: `ClerkSignIn.tsx`, `ClerkSignUp.tsx`, `ClerkSsoCallback.tsx`
- J-2–J-4 / BEH-02 — `src/pages/intelligence/EnrichmentTab.tsx`, `intelligence/HypothesesTab.tsx`,
  `intelligence/OntologyMatchTab.tsx`, `src/pages/hypothesis/AssumptionsTab.tsx`,
  `hypothesis/DiscoveryQuestionsTab.tsx`, `hypothesis/PersonaFitTab.tsx`,
  `src/features/intelligence-workspace/IntelligenceWorkspace.tsx` (+ `workspaceTabRegistry.ts`, `workspaceRoutes.ts`)
- J-5 / BEH-03 — `src/pages/drivers/DriverTreePage.tsx`, `src/pages/ValueTreeExplorer.tsx`
- J-6–J-7 / BEH-04 — `src/pages/FormulaBuilder.tsx`, `src/pages/FormulaBuilder/`,
  `src/pages/FormulaList.tsx`, `src/pages/calculator/ROITab.tsx`, `src/pages/MyModels.tsx`
- J-6 / BEH-05 — `src/pages/evidence/AlternativesTab.tsx`, `src/pages/evidence/SolutionCostTab.tsx`,
  `src/pages/GovernanceEvidence.tsx`
- J-8 / BEH-06 — `src/pages/BusinessCase.tsx`, `BusinessCaseList.tsx`, `InteractiveBusinessCase.tsx`,
  `src/pages/value-case/ValueCasePage.tsx`, `src/pages/studio/NarrativeTab.tsx`,
  `studio/ActionPlanTab.tsx`, `src/features/value-studio/StudioShell.tsx`
- J-9 / BEH-07 — `src/pages/deliverables/CFOView.tsx`, `ExecutiveView.tsx`, `TechnicalView.tsx`
- J-9 / BEH-08 — `src/pages/ReviewQueuePage.tsx`, `src/pages/VersionHistoryPage.tsx`,
  `GovernanceAuditLog.tsx`, `GovernanceChangeHistory.tsx`, `GovernanceCompliance.tsx`
- J-10 / BEH-09 — `src/pages/realization/RealizationPage.tsx`

## Key verified paths

- Entry/routing: `apps/web/src/App.tsx`, `apps/web/src/main.tsx`
- Feature shells: `apps/web/src/features/intelligence-workspace/`, `features/value-studio/`,
  `features/value-case/`
- Support dirs: `src/{api,auth,components,contexts,hooks,lib,navigation,schemas,services,shell,stores,types,workflow}/`
- Tests: `apps/web/e2e/`, `apps/web/test/`, colocated flow tests
  (`src/pages/intelligence/HypothesisValidationToDriverFlow.test.tsx`)
- Root config: `apps/web/package.json`, `vite.config.ts`, `playwright.config.ts`, `AGENTS.md`, `DESIGN.md`

## Dependencies

- Consumes: `services/api` (BFF) through versioned contracts in `contracts/openapi/` and
  `contracts/frontend/` (01-api-boundary, 02-type-synchronization, 03-hook-architecture).
- Uses: `packages/shared/`, `packages/feature-flags/`, `packages/platform-contract/`.
- MUST NOT call layer services directly; gateway only.

## Primary gates

- **AG-05** tenant-isolation-and-behavior — fail-closed frontend auth, query-cache separation by
  identity/tenant/account.
- **AG-02** code-quality-and-tests — Vitest/RTL component tests, Playwright browser journeys.
- **AG-03** contract-compliance — generated-client drift, type synchronization with backend schemas.
