---
workflow_id: facade-page-connector
name: Facade Page Connector
version: 1.0.0
description: Rewire frontend pages from static/mock data or generic useWorkspaceTabQuery to real backend hooks. Use when a page renders hardcoded data, uses MOCK_ arrays, or connects to the generic workspace endpoint instead of its dedicated DIL service. Fixes the 74% of pages with zero API calls identified in FRONTEND_AUDIT_REPORT.md.
pattern: circuit-breaker
risk_level: medium
---

# Facade Page Connector

Converts facade pages (static data, mock arrays, generic workspace queries) into real API-connected pages using dedicated hooks, loading states, and error boundaries.

## When to Use

- A page renders hardcoded or mock data
- A workspace tab uses `useWorkspaceTabQuery` instead of a dedicated DIL hook
- The FRONTEND_AUDIT_REPORT.md flags a page as "facade" or "mock-dependent"
- You are asked to "wire up" or "connect" a page to its backend

## Page Categories

### Category 1: Mock-Dependent Pages (hardcoded data, no API calls)

| Page | File | Evidence | Target Backend |
|------|------|----------|----------------|
| SourceConfiguration | `pages/SourceConfiguration.tsx` | `MOCK_SOURCES` array (line ~57) | L1 `/v1/sources` |
| FormulaBuilder | `pages/FormulaBuilder.tsx` | `// Constants & Mock Data` section | L3 `/v1/formulas/evaluate` |
| Stage1-6 (6 pages) | `pages/value-studio/Stage*.tsx` | Zero API calls, 1,955 lines total | **DEAD CODE — delete** |

### Category 2: Facade Pages (generic endpoint, wrong data source)

| Page | File | Current Hook | Target Hook | Target Backend |
|------|------|-------------|------------|----------------|
| SignalsTab | `pages/intelligence/SignalsTab.tsx` | `useWorkspaceTabQuery("signals")` | `useAccountSignals(accountId)` | L4 `/v1/accounts/{id}/signals` |
| DriversTab | `pages/intelligence/DriversTab.tsx` | `useWorkspaceTabQuery("drivers")` | `useValueHypotheses(accountId)` | L4 `/v1/value-hypotheses` |
| EvidenceTab | `pages/intelligence/EvidenceTab.tsx` | `useWorkspaceTabQuery("evidence")` | `useEvidenceLibrary({ account_id })` | L3 `/v1/evidence` |
| StakeholdersTab | `pages/intelligence/StakeholdersTab.tsx` | `useWorkspaceTabQuery("stakeholders")` | `useEnrichment(accountId)` | L4 `/v1/enrichment` |
| ActionPlanTab | `pages/studio/ActionPlanTab.tsx` | `useWorkspaceTabQuery("action-plan")` | `useValueHypotheses(accountId)` + `useIntelligence.dealReadiness(accountId)` | L4 `/v1/value-hypotheses` + `/v1/intelligence` |
| ValueModelTab | `pages/studio/ValueModelTab.tsx` | `useWorkspaceTabQuery("value-model")` | `useROICalculator(accountId)` | L3 `/v1/roi` |
| NarrativeTab | `pages/studio/NarrativeTab.tsx` | `useWorkspaceTabQuery("narrative")` | `useNarratives(accountId)` | L4 `/v1/narratives` |

### Category 3: Orphan Pages (exist but not routed)

| Page | File | Action |
|------|------|--------|
| OntologyBrowser | `pages/OntologyBrowser.tsx` | Either add route in App.tsx or delete |
| Home | `pages/Home.tsx` | Delete — `/home` renders `ValueNarrativeHome` |

### Category 4: Broken Routes

| Route | Issue | Fix |
|-------|-------|-----|
| `/deliverables/embeds` | Nav entry but no route | Add route or remove from TieredNav |
| `/context/ontology` | Self-redirect | Redirect to `/context/ontology/entities` |
| `/deliverables/views/{cfo,executive,technical}` | All render identical BusinessCase | Add `viewMode` prop to BusinessCase |

## Workflow Steps

### Step 1: Read the Target Page

Read the full page component file and identify:
1. **Data source:** Is it using mock data, `useWorkspaceTabQuery`, or a dedicated hook?
2. **UI structure:** What data fields does the page render? (table columns, card fields, etc.)
3. **User interactions:** What mutations exist? (create, update, delete, trigger actions)
4. **Existing states:** Does it have loading, error, and empty states?

### Step 2: Verify Backend Hook Exists

Check if the target hook exists:
```bash
ls apps/web/src/hooks/use{TargetHook}.ts
```

If the hook does NOT exist, use the `/dil-hook-scaffolder` workflow to create it first.

### Step 3: Replace Data Source

**For mock-dependent pages:**
1. Remove `MOCK_*` arrays and hardcoded data objects
2. Import the target hook: `import { use{Entity}List } from '@/hooks';`
3. Replace static data with hook: `const { data, isLoading, error } = use{Entity}List(filters);`
4. Wire the data fields to the existing UI components

**For facade pages (workspace tab → dedicated hook):**
1. Remove `useWorkspaceTabQuery("tab_key")` import and call
2. Import the target hook: `import { use{Entity}List } from '@/hooks';`
3. Get `accountId` from route params: `const { accountId } = useParams<{ accountId: string }>();`
4. Replace: `const { data } = useWorkspaceTabQuery("signals")` → `const { data, isLoading, error } = useAccountSignals(accountId!);`
5. Map the new data shape to the existing UI (field names may differ)

### Step 4: Add Loading/Error/Empty States

Every connected page MUST have these three states:

**Loading state (skeleton):**
```tsx
if (isLoading) {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
```

**Error state:**
```tsx
if (error) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <AlertCircle className="h-12 w-12 text-destructive mb-4" />
      <h3 className="text-lg font-semibold">Failed to load data</h3>
      <p className="text-muted-foreground mt-1">{error.message}</p>
      <Button variant="outline" onClick={() => refetch()} className="mt-4">
        Retry
      </Button>
    </div>
  );
}
```

**Empty state:**
```tsx
if (!data || data.length === 0) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <p className="text-muted-foreground">No data available yet.</p>
    </div>
  );
}
```

### Step 5: Wire Mutations (if applicable)

If the page has create/update/delete buttons:
1. Import mutation hooks from the same hook file
2. Replace `alert('coming soon')` or no-op handlers with actual mutation calls
3. Add optimistic updates for list mutations
4. Add toast notifications on success/failure

### Step 6: Verify

1. TypeScript compilation: `cd frontend && pnpm tsc --noEmit`
2. Run page tests if they exist: `cd frontend && pnpm test --run -- {PageName}`
3. Verify no mock data remains: `grep -n "MOCK_\|mockData\|hardcoded\|coming soon" apps/web/src/pages/{PageFile}`

## Edge Cases

- **Missing hook:** If the target hook doesn't exist, run `/dil-hook-scaffolder` first
- **Data shape mismatch:** The backend may return different field names than the mock data used. Map them explicitly.
- **Workspace persistence:** Don't remove `useWorkspaceTabQuery` if it's also used for saving workspace state (some tabs use it for both reading and writing)
- **AccountContext:** Workspace tabs get `accountId` from route params via `useParams`. Ensure the parent route passes it.
- **Stage pages:** The 6 Stage1-6 pages are dead code (all routes redirect to new system). Delete them rather than connecting them.
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "facade-page-connector-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.
