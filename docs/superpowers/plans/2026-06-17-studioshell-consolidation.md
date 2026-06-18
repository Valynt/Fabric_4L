# StudioShell Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Value Studio workspace use one consistent shell, one canonical tab model, and one tenant/account-aware routing structure across all core Studio pages.

**Architecture:** Keep the existing route-level `StudioShell` as the single chrome owner; remove inner shells from Studio tab components; move the AI right rail into `StudioShell` via a tab-level registry configuration; fix Driver Tree sub-tabs to stay inside Studio; add regression tests and docs.

**Tech Stack:** React, React Router v7, TypeScript, Tailwind CSS, Vitest, React Testing Library, pnpm.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `apps/web/src/features/value-studio/types.ts` | `StudioTabDef` shape including optional right-rail config |
| `apps/web/src/features/value-studio/studioTabRegistry.ts` | Single source of truth for Studio tabs and their rails |
| `apps/web/src/features/value-studio/StudioShell.tsx` | Renders header + tabs + content + right rail |
| `apps/web/src/features/value-studio/StudioTabs.tsx` | Canonical tab bar from registry |
| `apps/web/src/features/value-studio/components/StudioTabFrame.tsx` | Resolves active tab and renders its component |
| `apps/web/src/features/value-studio/components/StudioRightRail.tsx` | Shell-level right-rail renderer driven by active tab |
| `apps/web/src/shell/router.tsx` | Studio routes with `handle.title`/`handle.category` metadata |
| `apps/web/src/pages/studio/ActionPlanTab.tsx` | Page content only (no shell) |
| `apps/web/src/pages/studio/ValueModelTab.tsx` | Page content only (no shell) |
| `apps/web/src/pages/studio/NarrativeTab.tsx` | Page content only (no shell) |
| `apps/web/src/pages/drivers/DriverTreePage.tsx` | Page content + in-page sub-tab switcher (no duplicate header) |
| `apps/web/src/pages/calculator/ROITab.tsx` | Page content only (no shell) |
| `apps/web/src/pages/calculator/ValueModelTab.tsx` | Page content only (no shell) |
| `apps/web/src/pages/value-case/ValueCasePage.tsx` | Page content only (no shell) |
| `apps/web/src/pages/realization/RealizationPage.tsx` | Page content only (no shell) |
| `apps/web/src/components/workspace/DriverTreeShell.tsx` | In-page sub-tab switcher, no account header |
| `apps/web/src/components/workspace/ValueStudioShell.tsx` | Retired or repurposed outside Studio |
| `apps/web/src/components/workspace/CalculatorShell.tsx` | Retired or repurposed outside Studio |
| `apps/web/src/components/workspace/ValueCaseShell.tsx` | Retired |
| `apps/web/src/components/workspace/RealizationShell.tsx` | Retired |
| `apps/web/src/features/value-studio/StudioShell.test.tsx` | New regression tests for single shell |
| `apps/web/src/features/value-studio/StudioTabs.test.tsx` | New regression tests for canonical tab model |
| `apps/web/src/features/value-studio/studioTabRegistry.test.ts` | New registry contract tests |
| `apps/web/src/navigation/accountRouting.test.ts` | Add non-tenant-scoped fallback tests |
| `apps/web/docs/ROUTE_INVENTORY.md` | Updated Studio route/tab model docs |

---

### Task 1: Extend `StudioTabDef` to support a shell-level right rail

**Files:**
- Modify: `apps/web/src/features/value-studio/types.ts`

- [ ] **Step 1: Add optional right-rail config to `StudioTabDef`**

```typescript
import type { ComponentType, ReactNode } from "react";

export interface StudioTabProps {
  accountId: string;
  workspaceId?: string;
  organizationId?: string;
}

export interface StudioTabRailProps {
  accountId: string;
}

export type StudioTabId =
  | "action-plan"
  | "value-model"
  | "driver-tree"
  | "calculator"
  | "narrative"
  | "value-case"
  | "value-realization"
  | "solution-cost";

export type StudioTabStatus = "active" | "stub";

export type StudioTabCategory = "input" | "synthesis" | "output";

export interface StudioTabDef {
  id: StudioTabId;
  label: string;
  description: string;
  component: ComponentType<StudioTabProps> | null;
  /** Optional tab-specific right-rail component rendered by StudioShell */
  rightRail?: ComponentType<StudioTabRailProps>;
  queryKey?: string;
  status: StudioTabStatus;
  category: StudioTabCategory;
}
```

- [ ] **Step 2: Run typecheck**

Run: `pnpm --dir apps/web run typecheck`
Expected: No new errors from this file.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/value-studio/types.ts
git commit -m "feat(studio): add optional right-rail config to StudioTabDef"
```

---

### Task 2: Create shell-level right-rail renderer

**Files:**
- Create: `apps/web/src/features/value-studio/components/StudioRightRail.tsx`
- Modify: `apps/web/src/features/value-studio/studioTabRegistry.ts`

- [ ] **Step 1: Create `StudioRightRail.tsx`**

```tsx
/**
 * StudioRightRail — Shell-level right rail selected by active tab
 */
import { useStudioContext } from "../hooks/useStudioContext";
import { getStudioTabDef, getStudioTabOrDefault } from "../studioTabRegistry";

export default function StudioRightRail() {
  const { accountId, tabId } = useStudioContext();
  const resolvedTabId = getStudioTabOrDefault(tabId);
  const tabDef = getStudioTabDef(resolvedTabId);
  const RailComponent = tabDef?.rightRail;

  if (!RailComponent) {
    return (
      <div className="w-[320px] shrink-0 border-l border-border bg-background" />
    );
  }

  return (
    <div className="w-[320px] shrink-0 border-l border-border overflow-y-auto">
      <RailComponent accountId={accountId} />
    </div>
  );
}
```

- [ ] **Step 2: Create a generic `StudioAgentRail` component for tabs that use `useAgentEvents`**

Create: `apps/web/src/features/value-studio/components/StudioAgentRail.tsx`

```tsx
/**
 * StudioAgentRail — Reusable agent stream rail for Studio tabs
 */
import { useState } from "react";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import type { StudioTabRailProps } from "../types";

interface StudioAgentRailProps extends StudioTabRailProps {
  activeTab: string;
}

export default function StudioAgentRail({ accountId, activeTab }: StudioAgentRailProps) {
  const [mode, setMode] = useState<RightRailMode>("agent");
  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } =
    useAgentEvents({ activeTab, accountName: accountId });

  return (
    <RightRail
      mode={mode}
      onModeChange={setMode}
      activeTab={activeTab}
      messages={messages}
      onSendMessage={sendMessage}
      suggestedActions={suggestedActions}
      steps={steps}
      isStreaming={isStreaming}
      runMetadata={metadata}
    />
  );
}
```

- [ ] **Step 3: Update `studioTabRegistry.ts` to attach rails**

Add imports:

```typescript
import StudioAgentRail from "./components/StudioAgentRail";
```

Attach `rightRail` to each active tab that currently renders a rail:

```typescript
export const studioTabs: StudioTabDef[] = [
  {
    id: "action-plan",
    label: "Action Plan",
    description: "Product-anchored intervention plan mapping pain to capabilities.",
    component: ActionPlanTab,
    rightRail: () => <StudioAgentRail accountId="" activeTab="action-plan" />,
    status: "active",
    category: "synthesis",
  },
  {
    id: "value-model",
    label: "Value Model",
    description: "Quantified value model behind the business case.",
    component: ValueModelTab,
    queryKey: "value-model",
    rightRail: () => <StudioAgentRail accountId="" activeTab="value-model" />,
    status: "active",
    category: "synthesis",
  },
  {
    id: "driver-tree",
    label: "Driver Tree",
    description: "Interactive value driver tree editor.",
    component: DriverTreeTab,
    rightRail: () => <StudioAgentRail accountId="" activeTab="driver-tree" />,
    status: "active",
    category: "synthesis",
  },
  {
    id: "calculator",
    label: "ROI Calculator",
    description: "Interactive ROI calculator inputs and outputs.",
    component: CalculatorTab,
    rightRail: () => <StudioAgentRail accountId="" activeTab="calculator" />,
    status: "active",
    category: "synthesis",
  },
  {
    id: "narrative",
    label: "Narrative",
    description: "Storytelling layer for the value case.",
    component: NarrativeTab,
    queryKey: "narrative",
    rightRail: () => <StudioAgentRail accountId="" activeTab="narrative" />,
    status: "active",
    category: "output",
  },
  {
    id: "value-case",
    label: "Executive Value Case",
    description: "Generates the final written narrative and messaging.",
    component: ValueCaseTab,
    queryKey: "value-case",
    rightRail: () => <StudioAgentRail accountId="" activeTab="value-case" />,
    status: "active",
    category: "output",
  },
  {
    id: "value-realization",
    label: "Realization Plan",
    description: "Step-by-step plan turning validated hypotheses into milestones.",
    component: RealizationTab,
    queryKey: "action-plan",
    rightRail: () => <StudioAgentRail accountId="" activeTab="value-realization" />,
    status: "active",
    category: "output",
  },
  {
    id: "solution-cost",
    label: "Solution Cost",
    description: "Pricing and cost inputs for the business case.",
    component: SolutionCostTab,
    status: "stub",
    category: "input",
  },
];
```

> Note: `accountId` is passed at render time by `StudioRightRail`; the arrow functions above are placeholders that will be replaced by proper components in the next task.

- [ ] **Step 4: Run typecheck**

Run: `pnpm --dir apps/web run typecheck`
Expected: No new errors.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/value-studio/components/StudioRightRail.tsx \
        apps/web/src/features/value-studio/components/StudioAgentRail.tsx \
        apps/web/src/features/value-studio/studioTabRegistry.ts

git commit -m "feat(studio): add shell-level right-rail renderer and registry config"
```

---

### Task 3: Wire `StudioShell` to render the single right rail

**Files:**
- Modify: `apps/web/src/features/value-studio/StudioShell.tsx`

- [ ] **Step 1: Update `StudioShell.tsx`**

```tsx
/**
 * StudioShell — Main Value Studio workspace shell
 *
 * Composes: Header → Tabs → Content + Right Rail
 *
 * Route: /t/:tenantSlug/accounts/:accountId/studio/:tabId
 */
import StudioHeader from "./components/StudioHeader";
import StudioTabs from "./StudioTabs";
import StudioTabFrame from "./components/StudioTabFrame";
import StudioRightRail from "./components/StudioRightRail";

export default function StudioShell() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StudioHeader />
      <StudioTabs />
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <div className="flex-1 min-w-0 overflow-y-auto p-6">
          <StudioTabFrame />
        </div>
        <StudioRightRail />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run typecheck**

Run: `pnpm --dir apps/web run typecheck`
Expected: No new errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/value-studio/StudioShell.tsx
git commit -m "feat(studio): render single right rail from StudioShell"
```

---

### Task 4: Add route handle metadata to Studio routes

**Files:**
- Modify: `apps/web/src/shell/router.tsx`

- [ ] **Step 1: Locate the Studio route block**

Find the two Studio route objects near lines 451–473:

```tsx
{
  path: "/t/:tenantSlug/accounts/:accountId/studio",
  element: <UnifiedRouteGuard><Navigate to="action-plan" replace /></UnifiedRouteGuard>,
  handle: { accessPolicy: accountStdPolicy("studio.workspace") },
},
{
  path: "/t/:tenantSlug/accounts/:accountId/studio/:tabId",
  element: (
    <UnifiedRouteGuard>
      <Suspense fallback={...}><StudioShell /></Suspense>
    </UnifiedRouteGuard>
  ),
  handle: { accessPolicy: accountStdPolicy("studio.workspace") },
},
```

- [ ] **Step 2: Add `title` and `category` metadata**

```tsx
{
  path: "/t/:tenantSlug/accounts/:accountId/studio",
  element: <UnifiedRouteGuard><Navigate to="action-plan" replace /></UnifiedRouteGuard>,
  handle: {
    accessPolicy: accountStdPolicy("studio.workspace"),
    title: "Value Studio",
    category: "Workspace",
  },
},
{
  path: "/t/:tenantSlug/accounts/:accountId/studio/:tabId",
  element: (
    <UnifiedRouteGuard>
      <Suspense fallback={...}><StudioShell /></Suspense>
    </UnifiedRouteGuard>
  ),
  handle: {
    accessPolicy: accountStdPolicy("studio.workspace"),
    title: "Value Studio",
    category: "Workspace",
  },
},
```

- [ ] **Step 3: Run typecheck**

Run: `pnpm --dir apps/web run typecheck`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/shell/router.tsx
git commit -m "feat(studio): add route handle metadata for Value Studio"
```

---

### Task 5: Refactor tab rail components to receive `accountId`

**Files:**
- Modify: `apps/web/src/features/value-studio/components/StudioAgentRail.tsx`
- Modify: `apps/web/src/features/value-studio/studioTabRegistry.ts`

- [ ] **Step 1: Update `StudioAgentRail` to accept `accountId` and use it for account name lookup**

```tsx
/**
 * StudioAgentRail — Reusable agent stream rail for Studio tabs
 */
import { useState } from "react";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import type { StudioTabRailProps } from "../types";

interface StudioAgentRailProps extends StudioTabRailProps {
  activeTab: string;
}

export default function StudioAgentRail({ accountId, activeTab }: StudioAgentRailProps) {
  const [mode, setMode] = useState<RightRailMode>("agent");
  const { data: account } = useAccount(accountId ?? null);
  const accountName = account?.name ?? accountId ?? "Account";
  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } =
    useAgentEvents({ activeTab, accountName });

  return (
    <RightRail
      mode={mode}
      onModeChange={setMode}
      activeTab={activeTab}
      messages={messages}
      onSendMessage={sendMessage}
      suggestedActions={suggestedActions}
      steps={steps}
      isStreaming={isStreaming}
      runMetadata={metadata}
    />
  );
}
```

- [ ] **Step 2: Update `studioTabRegistry.ts` to use component references instead of inline arrows**

Replace each `rightRail: () => <StudioAgentRail ... />` with:

```typescript
rightRail: StudioAgentRail,
```

Then define a small wrapper for each `activeTab` value, or pass `activeTab` through the registry. Since `rightRail` receives only `accountId`, the simplest approach is to create thin wrappers:

Create: `apps/web/src/features/value-studio/rails/ActionPlanRail.tsx`

```tsx
import StudioAgentRail from "../components/StudioAgentRail";
import type { StudioTabRailProps } from "../types";

export default function ActionPlanRail(props: StudioTabRailProps) {
  return <StudioAgentRail {...props} activeTab="action-plan" />;
}
```

Create similar wrappers for:
- `ValueModelRail.tsx` (`activeTab="value-model"`)
- `DriverTreeRail.tsx` (`activeTab="driver-tree"`)
- `CalculatorRail.tsx` (`activeTab="calculator"`)
- `NarrativeRail.tsx` (`activeTab="narrative"`)
- `ValueCaseRail.tsx` (`activeTab="value-case"`)
- `RealizationRail.tsx` (`activeTab="value-realization"`)

Then in `studioTabRegistry.ts`:

```typescript
import ActionPlanRail from "./rails/ActionPlanRail";
import ValueModelRail from "./rails/ValueModelRail";
import DriverTreeRail from "./rails/DriverTreeRail";
import CalculatorRail from "./rails/CalculatorRail";
import NarrativeRail from "./rails/NarrativeRail";
import ValueCaseRail from "./rails/ValueCaseRail";
import RealizationRail from "./rails/RealizationRail";

export const studioTabs: StudioTabDef[] = [
  {
    id: "action-plan",
    label: "Action Plan",
    description: "Product-anchored intervention plan mapping pain to capabilities.",
    component: ActionPlanTab,
    rightRail: ActionPlanRail,
    status: "active",
    category: "synthesis",
  },
  {
    id: "value-model",
    label: "Value Model",
    description: "Quantified value model behind the business case.",
    component: ValueModelTab,
    queryKey: "value-model",
    rightRail: ValueModelRail,
    status: "active",
    category: "synthesis",
  },
  {
    id: "driver-tree",
    label: "Driver Tree",
    description: "Interactive value driver tree editor.",
    component: DriverTreeTab,
    rightRail: DriverTreeRail,
    status: "active",
    category: "synthesis",
  },
  {
    id: "calculator",
    label: "ROI Calculator",
    description: "Interactive ROI calculator inputs and outputs.",
    component: CalculatorTab,
    rightRail: CalculatorRail,
    status: "active",
    category: "synthesis",
  },
  {
    id: "narrative",
    label: "Narrative",
    description: "Storytelling layer for the value case.",
    component: NarrativeTab,
    queryKey: "narrative",
    rightRail: NarrativeRail,
    status: "active",
    category: "output",
  },
  {
    id: "value-case",
    label: "Executive Value Case",
    description: "Generates the final written narrative and messaging.",
    component: ValueCaseTab,
    queryKey: "value-case",
    rightRail: ValueCaseRail,
    status: "active",
    category: "output",
  },
  {
    id: "value-realization",
    label: "Realization Plan",
    description: "Step-by-step plan turning validated hypotheses into milestones.",
    component: RealizationTab,
    queryKey: "action-plan",
    rightRail: RealizationRail,
    status: "active",
    category: "output",
  },
  {
    id: "solution-cost",
    label: "Solution Cost",
    description: "Pricing and cost inputs for the business case.",
    component: SolutionCostTab,
    status: "stub",
    category: "input",
  },
];
```

- [ ] **Step 3: Run typecheck**

Run: `pnpm --dir apps/web run typecheck`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/features/value-studio/components/StudioAgentRail.tsx \
        apps/web/src/features/value-studio/rails/ \
        apps/web/src/features/value-studio/studioTabRegistry.ts

git commit -m "feat(studio): make right-rail components account-aware and registry-driven"
```

---

### Task 6: Remove `ValueStudioShell` from `ActionPlanTab`

**Files:**
- Modify: `apps/web/src/pages/studio/ActionPlanTab.tsx`

- [ ] **Step 1: Read current file to locate the `ValueStudioShellComponent` wrapper**

- [ ] **Step 2: Remove the wrapper and keep only page content**

The diff should remove:

```tsx
import ValueStudioShellComponent from "@/components/workspace/ValueStudioShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
```

And remove the `rightRail` prop and `useAgentEvents` hook if it was only used for the rail.

The render should return only the content that was previously inside `<ValueStudioShellComponent>...</ValueStudioShellComponent>`.

For example, if the file currently returns:

```tsx
return (
  <ValueStudioShellComponent account={{ accountName, industry, revenue }} rightRail={...}>
    <div className="space-y-6">...</div>
  </ValueStudioShellComponent>
);
```

Change to:

```tsx
export default function ActionPlanTab({ accountId }: StudioTabProps) {
  // existing data hooks
  return (
    <div className="space-y-6">...</div>
  );
}
```

- [ ] **Step 3: Run tests for this page**

Run: `pnpm --dir apps/web run test -- src/pages/studio/ActionPlanTab.test.tsx`
Expected: If no tests exist, the command exits successfully. If tests exist, they should still pass or be updated.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/studio/ActionPlanTab.tsx
git commit -m "refactor(studio): remove inner shell from ActionPlanTab"
```

---

### Task 7: Remove `ValueStudioShell` from `ValueModelTab`

**Files:**
- Modify: `apps/web/src/pages/studio/ValueModelTab.tsx`

- [ ] **Step 1: Remove `ValueStudioShellComponent`, `RightRail`, and rail-only state**

Remove imports:

```tsx
import ValueStudioShellComponent from "@/components/workspace/ValueStudioShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
```

Remove rail-only state:

```tsx
const [railMode, setRailMode] = useState<RightRailMode>("agent");
const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } =
  useAgentEvents({ activeTab: "value-model", accountName: account?.name ?? "Account" });
```

- [ ] **Step 2: Return only page content**

If the current return is:

```tsx
return (
  <ValueStudioShellComponent account={{...}} rightRail={...}>
    {content}
  </ValueStudioShellComponent>
);
```

Change to:

```tsx
return (
  <div className="space-y-6">
    {content}
  </div>
);
```

- [ ] **Step 3: Run typecheck and tests**

Run: `pnpm --dir apps/web run typecheck`
Run: `pnpm --dir apps/web run test -- src/pages/studio/ValueModelTab.test.tsx`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/studio/ValueModelTab.tsx
git commit -m "refactor(studio): remove inner shell from ValueModelTab"
```

---

### Task 8: Remove `ValueStudioShell` from `NarrativeTab`

**Files:**
- Modify: `apps/web/src/pages/studio/NarrativeTab.tsx`

- [ ] **Step 1: Remove the wrapper and rail-only code**

Same transformation as Task 6 and Task 7.

- [ ] **Step 2: Return only page content**

```tsx
return (
  <div className="space-y-6">
    {content}
  </div>
);
```

- [ ] **Step 3: Run typecheck and tests**

Run: `pnpm --dir apps/web run typecheck`
Run: `pnpm --dir apps/web run test -- src/pages/studio/NarrativeTab.test.tsx`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/studio/NarrativeTab.tsx
git commit -m "refactor(studio): remove inner shell from NarrativeTab"
```

---

### Task 9: Refactor `DriverTreePage` to stay inside Studio

**Files:**
- Modify: `apps/web/src/pages/drivers/DriverTreePage.tsx`
- Modify: `apps/web/src/components/workspace/DriverTreeShell.tsx`

- [ ] **Step 1: Change `DriverTreeShell` to render only an in-page sub-tab switcher**

```tsx
/**
 * DriverTreeShell — In-page sub-tab switcher for the Studio Driver Tree tab
 */
import { Link, useLocation, useParams } from "react-router-dom";
import { cn } from "@/lib/utils";

interface DriverTreeShellProps {
  children: React.ReactNode;
}

const SUB_TABS = [
  { key: "trees", label: "Trees" },
  { key: "evidence", label: "Evidence" },
  { key: "alternatives", label: "Alternatives" },
  { key: "solution-cost", label: "Solution Cost" },
];

export default function DriverTreeShell({ children }: DriverTreeShellProps) {
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const activeSubTab = searchParams.get("sub") ?? "trees";

  return (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-border px-6" role="tablist" aria-label="Driver Tree sections">
        {SUB_TABS.map((tab) => {
          const to = `/t/${tenantSlug}/accounts/${accountId}/studio/driver-tree?sub=${tab.key}`;
          return (
            <Link key={tab.key} to={to} role="tab" aria-selected={activeSubTab === tab.key}>
              <button
                className={cn(
                  "px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
                  activeSubTab === tab.key
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )}
              >
                {tab.label}
              </button>
            </Link>
          );
        })}
      </div>
      <div className="flex-1 overflow-y-auto p-6">{children}</div>
    </div>
  );
}
```

- [ ] **Step 2: Update `DriverTreePage` to read `sub` query param and remove account header construction**

Remove the account header metadata construction (`accountName`, `industry`, `revenue`) unless used by page content.

Change the return from:

```tsx
return (
  <DriverTreeShell accountName={accountName} industry={industry} revenue={revenue}>
    {tab === "trees" && <TreesTab />}
    ...
  </DriverTreeShell>
);
```

To:

```tsx
const sub = searchParams.get("sub") ?? "trees";

return (
  <DriverTreeShell>
    {sub === "trees" && <TreesTab />}
    {sub === "evidence" && <EvidenceTabContent />}
    {sub === "alternatives" && <AlternativesTab />}
    {sub === "solution-cost" && <SolutionCostTab />}
  </DriverTreeShell>
);
```

- [ ] **Step 3: Run typecheck and tests**

Run: `pnpm --dir apps/web run typecheck`
Run: `pnpm --dir apps/web run test -- src/pages/drivers/DriverTreePage.test.tsx`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/drivers/DriverTreePage.tsx \
        apps/web/src/components/workspace/DriverTreeShell.tsx

git commit -m "refactor(studio): keep Driver Tree sub-tabs inside Studio"
```

---

### Task 10: Remove `CalculatorShell` from ROI Calculator tabs

**Files:**
- Modify: `apps/web/src/pages/calculator/ROITab.tsx`
- Modify: `apps/web/src/pages/calculator/ValueModelTab.tsx`

- [ ] **Step 1: In `ROITab.tsx`, remove `CalculatorShell` and `RightRail` imports and wrapper**

Return only page content.

- [ ] **Step 2: In `ValueModelTab.tsx`, remove `CalculatorShell` and `RightRail` imports and wrapper**

Return only page content.

- [ ] **Step 3: Run typecheck and tests**

Run: `pnpm --dir apps/web run typecheck`
Run: `pnpm --dir apps/web run test -- src/pages/calculator/ROITab.test.tsx src/pages/calculator/ValueModelTab.test.tsx`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/calculator/ROITab.tsx \
        apps/web/src/pages/calculator/ValueModelTab.tsx

git commit -m "refactor(studio): remove CalculatorShell from calculator tabs"
```

---

### Task 11: Remove `ValueCaseShell` and `RealizationShell`

**Files:**
- Modify: `apps/web/src/pages/value-case/ValueCasePage.tsx`
- Modify: `apps/web/src/pages/realization/RealizationPage.tsx`

- [ ] **Step 1: In `ValueCasePage.tsx`, remove `ValueCaseShell`, `RightRail`, and rail-only code**

Return only page content wrapped in a simple container.

- [ ] **Step 2: In `RealizationPage.tsx`, remove `RealizationShell`, `RightRail`, and rail-only code**

Keep the "Back to Signals" action but route it through the canonical `intelligence-signals` state instead of any flat path.

- [ ] **Step 3: Run typecheck and tests**

Run: `pnpm --dir apps/web run typecheck`
Run: `pnpm --dir apps/web run test -- src/pages/value-case/ValueCasePage.test.tsx src/pages/realization/RealizationPage.test.tsx`
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/pages/value-case/ValueCasePage.tsx \
        apps/web/src/pages/realization/RealizationPage.tsx

git commit -m "refactor(studio): remove ValueCaseShell and RealizationShell"
```

---

### Task 12: Retire unused shell components

**Files:**
- Modify: `apps/web/src/components/workspace/ValueStudioShell.tsx`
- Modify: `apps/web/src/components/workspace/CalculatorShell.tsx`
- Modify: `apps/web/src/components/workspace/ValueCaseShell.tsx`
- Modify: `apps/web/src/components/workspace/RealizationShell.tsx`

- [ ] **Step 1: Decide whether to delete or repurpose each shell**

If a shell is only used by Studio pages, delete it and its test file.

If a shell is also used outside Studio (e.g., `ValueStudioShell` is referenced by the Intelligence workspace route for `value-model`), repurpose it as a non-Studio helper or move the page content to the canonical Studio route only.

- [ ] **Step 2: For shells used only by Studio, delete files**

```bash
rm apps/web/src/components/workspace/ValueCaseShell.tsx
rm apps/web/src/components/workspace/RealizationShell.tsx
rm apps/web/src/components/workspace/CalculatorShell.tsx
rm apps/web/src/components/workspace/ValueStudioShell.tsx
rm apps/web/src/components/workspace/ValueStudioShell.test.tsx
```

- [ ] **Step 3: Run typecheck and tests**

Run: `pnpm --dir apps/web run typecheck`
Run: `pnpm --dir apps/web run test -- src/components/workspace/`
Expected: No new errors; deleted tests no longer run.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(studio): retire unused inner shell components"
```

---

### Task 13: Add regression tests for `StudioTabs`

**Files:**
- Create: `apps/web/src/features/value-studio/StudioTabs.test.tsx`

- [ ] **Step 1: Write the test file**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import StudioTabs from "./StudioTabs";

function renderTabs(path = "/t/acme/accounts/acc-123/studio/value-model") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/t/:tenantSlug/accounts/:accountId/studio/:tabId" element={<StudioTabs />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("StudioTabs", () => {
  it("renders exactly one canonical tablist", () => {
    renderTabs();
    expect(screen.getAllByRole("tablist")).toHaveLength(1);
  });

  it("marks the active tab selected", () => {
    renderTabs();
    expect(screen.getByRole("tab", { name: "Value Model" })).toHaveAttribute("aria-current", "page");
  });

  it("falls back to the default tab for an invalid tab id", () => {
    renderTabs("/t/acme/accounts/acc-123/studio/not-a-tab");
    expect(screen.getByRole("tab", { name: "Action Plan" })).toHaveAttribute("aria-current", "page");
  });

  it("builds tenant-scoped links that preserve account id", () => {
    renderTabs();
    expect(screen.getByRole("link", { name: "Action Plan" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/studio/action-plan"
    );
    expect(screen.getByRole("link", { name: "Executive Value Case" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/studio/value-case"
    );
  });

  it("does not link any Studio tab to /intelligence/*", () => {
    renderTabs();
    const links = screen.getAllByRole("link");
    for (const link of links) {
      const href = link.getAttribute("href") ?? "";
      expect(href).not.toMatch(/\/intelligence\//);
    }
  });
});
```

- [ ] **Step 2: Run the new tests**

Run: `pnpm --dir apps/web run test -- src/features/value-studio/StudioTabs.test.tsx`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/value-studio/StudioTabs.test.tsx
git commit -m "test(studio): add StudioTabs regression tests"
```

---

### Task 14: Add regression tests for `StudioShell`

**Files:**
- Create: `apps/web/src/features/value-studio/StudioShell.test.tsx`

- [ ] **Step 1: Write the test file**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import StudioShell from "./StudioShell";

vi.mock("@/hooks/useAccounts", () => ({
  useAccount: () => ({
    data: { name: "Acme Corp", industry: "Manufacturing", annual_revenue: 120000000 },
    isLoading: false,
  }),
}));

function renderShell(path = "/t/acme/accounts/acc-123/studio/value-model") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/t/:tenantSlug/accounts/:accountId/studio/:tabId" element={<StudioShell />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("StudioShell", () => {
  it("renders exactly one account header", () => {
    renderShell();
    const headers = screen.getAllByText("Acme Corp");
    expect(headers).toHaveLength(1);
  });

  it("renders exactly one canonical tablist", () => {
    renderShell();
    expect(screen.getAllByRole("tablist")).toHaveLength(1);
  });

  it("preserves tenant and account context in tab links", () => {
    renderShell();
    expect(screen.getByRole("link", { name: "Action Plan" })).toHaveAttribute(
      "href",
      "/t/acme/accounts/acc-123/studio/action-plan"
    );
  });
});
```

- [ ] **Step 2: Run the new tests**

Run: `pnpm --dir apps/web run test -- src/features/value-studio/StudioShell.test.tsx`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/value-studio/StudioShell.test.tsx
git commit -m "test(studio): add StudioShell regression tests"
```

---

### Task 15: Add registry contract tests

**Files:**
- Create: `apps/web/src/features/value-studio/studioTabRegistry.test.ts`

- [ ] **Step 1: Write the test file**

```ts
import { describe, expect, it } from "vitest";
import { studioTabs, getActiveStudioTabDefs, DEFAULT_STUDIO_TAB } from "./studioTabRegistry";

describe("studioTabRegistry", () => {
  it("contains the default tab", () => {
    const ids = getActiveStudioTabDefs().map((t) => t.id);
    expect(ids).toContain(DEFAULT_STUDIO_TAB);
  });

  it("every active tab has a component", () => {
    for (const tab of getActiveStudioTabDefs()) {
      expect(tab.component, `tab ${tab.id} should have a component`).toBeTruthy();
    }
  });

  it("no active tab links to /intelligence/*", () => {
    for (const tab of getActiveStudioTabDefs()) {
      expect(tab.id).not.toMatch(/^intelligence-/);
    }
  });
});
```

- [ ] **Step 2: Run the new tests**

Run: `pnpm --dir apps/web run test -- src/features/value-studio/studioTabRegistry.test.ts`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/value-studio/studioTabRegistry.test.ts
git commit -m "test(studio): add studio tab registry contract tests"
```

---

### Task 16: Add non-tenant-scoped routing tests

**Files:**
- Modify: `apps/web/src/navigation/accountRouting.test.ts`

- [ ] **Step 1: Add tests for fallback behavior when tenant or account is missing**

```ts
import { describe, expect, it } from "vitest";
import {
  resolveAccountScopedWorkspacePath,
  getWorkspaceTabOrDefault,
} from "./accountRouting";

describe("accountRouting fallback behavior", () => {
  it("returns a non-tenant-scoped fallback when accountId is missing", () => {
    const path = resolveAccountScopedWorkspacePath({
      workspace: "studio",
      accountId: null,
      tab: "value-model",
      tenantSlug: "acme",
    });
    expect(path).toBe("/t/default/accounts");
  });

  it("defaults to the canonical studio tab when an invalid tab is supplied", () => {
    expect(getWorkspaceTabOrDefault("studio", "not-a-tab")).toBe("action-plan");
  });

  it("preserves tenant slug and account id for valid studio tabs", () => {
    const path = resolveAccountScopedWorkspacePath({
      workspace: "studio",
      accountId: "acc-123",
      tab: "narrative",
      tenantSlug: "acme",
    });
    expect(path).toBe("/t/acme/accounts/acc-123/studio/narrative");
  });
});
```

- [ ] **Step 2: Run the updated tests**

Run: `pnpm --dir apps/web run test -- src/navigation/accountRouting.test.ts`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/navigation/accountRouting.test.ts
git commit -m "test(navigation): add non-tenant-scoped Studio routing tests"
```

---

### Task 17: Update documentation

**Files:**
- Modify: `apps/web/docs/ROUTE_INVENTORY.md`

- [ ] **Step 1: Locate the Value Studio section and update it**

Update the section to describe:

- Single route: `/t/:tenantSlug/accounts/:accountId/studio/:tabId`
- `StudioShell` is the only chrome owner.
- Tabs are sourced from `studioTabRegistry.ts`.
- AI right rail is rendered by `StudioShell` via the registry.
- Driver Tree sub-tabs use `?sub=` query param and stay inside Studio.
- No Studio tab links to `/intelligence/*` except explicit cross-workspace actions.

- [ ] **Step 2: Commit**

```bash
git add apps/web/docs/ROUTE_INVENTORY.md
git commit -m "docs(studio): document consolidated Studio route and tab model"
```

---

### Task 18: Final verification

- [ ] **Step 1: Run typecheck**

Run: `pnpm --dir apps/web run typecheck`
Expected: No errors.

- [ ] **Step 2: Run frontend tests**

Run: `pnpm --dir apps/web run test`
Expected: All tests pass.

- [ ] **Step 3: Run lint**

Run: `pnpm --dir apps/web run lint`
Expected: No errors.

- [ ] **Step 4: Commit any final fixes**

```bash
git add -A
git commit -m "fix(studio): address final review feedback"
```

---

## Self-Review Checklist

1. **Spec coverage:** Every acceptance criterion maps to at least one task.
2. **Placeholder scan:** No TBD, TODO, or vague steps.
3. **Type consistency:** `StudioTabDef.rightRail` uses `ComponentType<StudioTabRailProps>` consistently; `StudioRightRail` passes `accountId` to the rail component.
