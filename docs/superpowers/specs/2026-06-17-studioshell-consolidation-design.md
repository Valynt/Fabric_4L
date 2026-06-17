# StudioShell Consolidation Design

## Goal

Make the Value Studio workspace use one consistent shell, one canonical tab model, and one tenant/account-aware routing structure across all core Studio pages.

## Current State

The canonical Studio route is already defined in `apps/web/src/shell/router.tsx`:

```tsx
path: "/t/:tenantSlug/accounts/:accountId/studio/:tabId"
element: <StudioShell />
```

`StudioShell` (`apps/web/src/features/value-studio/StudioShell.tsx`) renders:

```tsx
<StudioHeader />
<StudioTabs />
<StudioTabFrame />
```

However, most tab components registered in `studioTabRegistry.ts` wrap themselves in an inner shell that duplicates this chrome:

| Tab | Inner Shell | Duplicates |
|-----|-------------|------------|
| Action Plan | `ValueStudioShell` | account header + Studio tab bar + right rail |
| Value Model | `ValueStudioShell` | account header + Studio tab bar + right rail |
| Narrative | `ValueStudioShell` | account header + Studio tab bar + right rail |
| Driver Tree | `DriverTreeShell` | account header + sub-tabs linking to `/intelligence/*` |
| ROI Calculator | `CalculatorShell` | account header + ROI/Value Model tab bar + right rail |
| Value Case | `ValueCaseShell` | account header + right rail |
| Realization | `RealizationShell` | account header + right rail |
| Solution Cost | none | only outer `StudioShell` chrome |

All inner shells ultimately delegate to `WorkspacePagePattern`, which draws an account header bar, optional horizontal tabs, and an optional 320px right rail.

## Design Decisions

### 1. `StudioShell` is the single source of chrome

Only `StudioShell` renders:

- Account/workspace header (`StudioHeader`)
- Canonical Studio tab bar (`StudioTabs`)
- AI right rail (new, shell-level)
- Tab content frame (`StudioTabFrame`)

Individual Studio page components render **only page-specific content**. They do not render `WorkspacePagePattern`, `ValueStudioShell`, `CalculatorShell`, `DriverTreeShell`, `ValueCaseShell`, or `RealizationShell`.

### 2. Canonical tab model

The single source of truth remains `apps/web/src/features/value-studio/studioTabRegistry.ts`.

`StudioTabs` consumes `getActiveStudioTabDefs()` and builds links using the canonical path:

```tsx
`/t/${tenantSlug}/accounts/${accountId}/studio/${tab.id}`
```

Tab labels, order, visibility, and active-state logic come from the registry only.

Route `handle` metadata in `router.tsx` will be enriched with `title` and `category` for Studio routes where useful, so that consumers such as telemetry, breadcrumbs, and future header title normalization can read a stable value.

### 3. Tenant/account-aware routing

Every Studio tab link must preserve:

- `tenantSlug` from `useParams`
- `accountId` from `useParams`
- `activeTab` resolved via `getStudioTabOrDefault(tabId)`
- workspace context (`studio`)

Navigation helpers in `apps/web/src/navigation/accountRouting.ts` (`resolveAccountScopedWorkspacePath`, `getWorkspaceTabState`) are the canonical way to build cross-tab paths. No Studio tab link will hardcode `/intelligence/*` unless the explicit user intent is to leave Studio (e.g., "Back to Signals" in Realization).

### 4. Driver Tree sub-tabs stay inside Studio

`DriverTreePage` currently uses `DriverTreeShell` with sub-tabs (`trees`, `evidence`, `alternatives`, `solution-cost`) that link to `/intelligence/:tab`. These links will be replaced with in-tab navigation using query parameters or an in-page segmented control, so the user remains inside the Studio `driver-tree` tab. The sub-tab switcher will be rendered as page content, not as a duplicate workspace tab bar.

### 5. Right rail consolidation

The AI right rail will be **always present in `StudioShell`** and controlled by a single shell-level configuration based on the active tab.

Each Studio tab that needs a rail will provide a tab-specific rail component or configuration through the registry. `StudioShell` will look up the active tab and render its rail in a fixed 320px panel, consistent with the current `WorkspacePagePattern` layout.

Right rail props that are currently duplicated in every page (`useAgentEvents`, `mode` state, etc.) will move into the tab-specific rail component or a shared `useStudioRightRail` hook.

### 6. Page-specific content only

After consolidation, each page component receives `StudioTabProps` (`accountId`, optional `workspaceId`/`organizationId`) and renders only its content. Account metadata is fetched via `useAccount(accountId)` where needed, but the header is never rendered inside the page.

## Files to Change

### Shell and registry

- `apps/web/src/features/value-studio/StudioShell.tsx` — add right rail, ensure single chrome
- `apps/web/src/features/value-studio/StudioTabs.tsx` — canonical tab bar (already mostly correct)
- `apps/web/src/features/value-studio/studioTabRegistry.ts` — add optional rail config per tab
- `apps/web/src/features/value-studio/types.ts` — add `rightRail` field to `StudioTabDef` if needed
- `apps/web/src/features/value-studio/components/StudioTabFrame.tsx` — pass rail context if needed
- `apps/web/src/shell/router.tsx` — add `handle.title`/`handle.category` to Studio routes

### Page components (remove inner shells)

- `apps/web/src/pages/studio/ActionPlanTab.tsx`
- `apps/web/src/pages/studio/ValueModelTab.tsx`
- `apps/web/src/pages/studio/NarrativeTab.tsx`
- `apps/web/src/pages/drivers/DriverTreePage.tsx`
- `apps/web/src/pages/calculator/ROITab.tsx`
- `apps/web/src/pages/calculator/ValueModelTab.tsx`
- `apps/web/src/pages/value-case/ValueCasePage.tsx`
- `apps/web/src/pages/realization/RealizationPage.tsx`
- `apps/web/src/pages/evidence/SolutionCostTab.tsx` (used as Studio tab)

### Shell components (retire or repurpose)

- `apps/web/src/components/workspace/ValueStudioShell.tsx` — remove or repurpose as non-Studio helper
- `apps/web/src/components/workspace/CalculatorShell.tsx` — remove Studio usage
- `apps/web/src/components/workspace/DriverTreeShell.tsx` — remove account-header duplication
- `apps/web/src/components/workspace/ValueCaseShell.tsx`
- `apps/web/src/components/workspace/RealizationShell.tsx`

### Routing helpers

- `apps/web/src/navigation/accountRouting.ts` — ensure helpers cover all Studio tabs; add tests
- `apps/web/src/navigation/navigationService.ts` — verify Studio route states are complete

### Tests

- `apps/web/src/features/value-studio/StudioShell.test.tsx` — new: single header, single tab bar, tenant preservation, no duplicate shells
- `apps/web/src/features/value-studio/StudioTabs.test.tsx` — new: active state, canonical links, invalid tab fallback
- `apps/web/src/features/value-studio/studioTabRegistry.test.ts` — new: registry completeness, no `/intelligence/*` routes
- `apps/web/src/navigation/accountRouting.test.ts` — add non-tenant-scoped fallback cases
- `apps/web/src/components/workspace/ValueStudioShell.test.tsx` — update or remove

### Documentation

- `apps/web/docs/ROUTE_INVENTORY.md` — update Studio route/tab model
- `DESIGN.md` or `docs/NAVIGATION_ARCHITECTURE.md` — update shell/right-rail conventions if needed

## Acceptance Criteria

- Every Studio page shows exactly one account/workspace header.
- Every Studio page shows exactly one canonical Studio tab bar.
- Switching tabs preserves tenant and account/case context.
- No Studio tab links route to `/intelligence/*` unless explicitly intended.
- Active tab state is correct on all Studio routes.
- AI right rail behavior is consistent across all Studio tabs.
- Tests cover tenant-scoped and non-tenant-scoped routes.
- No duplicate shell/header/tab markup remains in individual Studio pages.
