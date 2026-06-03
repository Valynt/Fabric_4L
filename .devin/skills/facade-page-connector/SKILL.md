---
skill_id: facade-page-connector
name: facade-page-connector
version: 1.0.0
description: Rewire frontend pages from static/mock data or generic useWorkspaceTabQuery to real backend hooks. Use when a page renders hardcoded data, uses MOCK_ arrays, or connects to the generic workspace endpoint instead of its dedicated DIL service. Fixes the 74% of pages with zero API calls identified in FRONTEND_AUDIT_REPORT.md.
side_effects: write
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Facade Page Connector

Converts facade pages (static/mock data, generic workspace queries) into real API-connected pages with loading states and error boundaries.

## When to Use

- A page renders hardcoded or mock data
- A workspace tab uses `useWorkspaceTabQuery` instead of a DIL hook
- FRONTEND_AUDIT_REPORT.md flags a page as "facade" or "mock-dependent"
- You are asked to "wire up" or "connect" a page to its backend

## Page Categories

### Mock-Dependent Pages (hardcoded data)

| Page | File | Evidence | Target Backend |
|------|------|----------|----------------|
| SourceConfiguration | `pages/SourceConfiguration.tsx` | `MOCK_SOURCES` array | L1 `/v1/sources` |
| FormulaBuilder | `pages/FormulaBuilder.tsx` | `// Constants & Mock Data` | L3 `/v1/formulas/evaluate` |
| Stage1-6 (6 pages) | `pages/value-studio/Stage*.tsx` | Zero API calls | **DEAD CODE** |

### Facade Pages (generic endpoint)

| Page | Current Hook | Target Hook | Target Backend |
|------|-------------|------------|----------------|
| SignalsTab | `useWorkspaceTabQuery("signals")` | `useAccountSignals(accountId)` | L4 `/v1/accounts/{id}/signals` |
| DriversTab | `useWorkspaceTabQuery("drivers")` | `useValueHypotheses(accountId)` | L4 `/v1/value-hypotheses` |
| EvidenceTab | `useWorkspaceTabQuery("evidence")` | `useEvidenceLibrary({account_id})` | L3 `/v1/evidence` |
| StakeholdersTab | `useWorkspaceTabQuery("stakeholders")` | `useEnrichment(accountId)` | L4 `/v1/enrichment` |
| ActionPlanTab | `useWorkspaceTabQuery("action-plan")` | `useValueHypotheses(accountId)` | L4 `/v1/value-hypotheses` |
| ValueModelTab | `useWorkspaceTabQuery("value-model")` | `useROICalculator(accountId)` | L3 `/v1/roi` |
| NarrativeTab | `useWorkspaceTabQuery("narrative")` | `useNarratives(accountId)` | L4 `/v1/narratives` |

### Orphan Pages (exist but not routed)

| Page | File | Action |
|------|------|--------|
| OntologyBrowser | `pages/OntologyBrowser.tsx` | Add route or delete |
| Home | `pages/Home.tsx` | Delete — `/home` renders `ValueNarrativeHome` |

## Workflow Steps

### Step 1: Read Target Page

Read the page file and identify:
1. **Data source:** mock data, `useWorkspaceTabQuery`, or dedicated hook?
2. **UI structure:** data fields rendered (tables, cards)
3. **Interactions:** mutations (create, update, delete, trigger)
4. **Existing states:** loading, error, empty states present?

### Step 2: Verify Backend Hook Exists

```bash
ls frontend/client/src/hooks/use{TargetHook}.ts
```

If NOT exists, use `/dil-hook-scaffolder` first.

### Step 3: Replace Data Source

**Mock-dependent pages:**
1. Remove `MOCK_*` arrays and hardcoded data
2. Import target hook: `import { use{Entity}List } from '@/hooks';`
3. Replace static data: `const { data, isLoading, error } = use{Entity}List(filters);`
4. Wire data fields to existing UI

**Facade pages (workspace → dedicated):**
1. Remove `useWorkspaceTabQuery("tab_key")` import and call
2. Import target hook: `import { use{Entity}List } from '@/hooks';`
3. Get accountId: `const { accountId } = useParams<{ accountId: string }>();`
4. Replace: `const { data } = useWorkspaceTabQuery("signals")` → `const { data, isLoading, error } = useAccountSignals(accountId!);`
5. Map new data shape to existing UI

### Step 4: Add Loading/Error/Empty States

**Loading:**
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

**Error:**
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

**Empty:**
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

If create/update/delete buttons:
1. Import mutation hooks from same hook file
2. Replace `alert('coming soon')` with actual mutation calls
3. Add optimistic updates for list mutations
4. Add toast notifications on success/failure

### Step 6: Verify

1. TypeScript: `cd frontend && pnpm tsc --noEmit`
2. Tests: `cd frontend && pnpm test --run -- {PageName}`
3. Verify no mock data: `grep -n "MOCK_\|coming soon" frontend/client/src/pages/{PageFile}`

## Edge Cases

- **Missing hook:** Run `/dil-hook-scaffolder` first
- **Data shape mismatch:** Map backend field names to UI fields explicitly
- **Workspace persistence:** Don't remove if also used for saving workspace state
- **AccountContext:** Get `accountId` from `useParams` via parent route
- **Stage pages:** 6 Stage pages are dead code (redirected to new system). Delete them.
