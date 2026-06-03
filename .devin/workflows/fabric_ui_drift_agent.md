---
workflow_id: fabric-ui-drift-agent
name: Fabric UI Drift Agent
version: 1.0.0
description: Fabric System Hardening + UI Consistency Deployment with autonomous multi-agent enforcement loop
pattern: manager-worker
risk_level: medium
---

# Fabric UI System Enforcement

Autonomous Multi-Agent Enforcement Loop for achieving zero drift across all UI — token-driven, primitive-based, visually consistent.

**Mode**: Looped autonomous execution. Does not stop at partial completion.

---

## WORKFLOW ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION LOOP                               │
│         DISCOVER → ANALYZE → FIX → VALIDATE → VERIFY → REPEAT  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │DISCOVERY │───→│ ANALYZE  │───→│   FIX    │                 │
│  │  AGENT   │    │  AGENT   │    │  AGENT   │                 │
│  └──────────┘    └──────────┘    └────┬─────┘                 │
│       ↑                                 │                       │
│       │                                 ▼                       │
│  ┌────┴────┐    ┌──────────┐    ┌──────────┐                 │
│  │ REPEAT  │◄───│  VERIFY  │◄───│ VALIDATE │                 │
│  │(if drift│    │  AGENT   │    │  AGENT   │                 │
│  │ remains)│    └──────────┘    └──────────┘                 │
│  └─────────┘                                                   │
│                                                                 │
│  ┌──────────┐    ┌──────────┐                                  │
│  │  AUDIT   │    │ REPORT   │                                  │
│  │  AGENT   │    │  AGENT   │                                  │
│  │ (parallel│    │ (final)  │                                  │
│  │   lens)  │    └──────────┘                                  │
│  └──────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Loop Termination Condition**:
- ALL pages use Fabric primitives
- AND zero inline styles remain
- AND zero magic values exist
- AND entity colors centralized
- AND build + lint + visual checks pass
- AND audit agent reports zero violations

---

## AGENT 1: DISCOVERY AGENT

**Purpose**: Map current state without judgment.  
**Input**: `frontend/client/src/`  
**Output**: Raw inventory of everything UI-related.

### Tasks

#### 1.1 TOKEN AUDIT

```bash
# Extract every CSS custom property
grep -rn "oklch\|--[a-z-]*:" src/index.css src/globals.css 2>/dev/null > /tmp/token_inventory.txt

# Compare to Fabric spec
diff /tmp/token_inventory.txt <(echo "[SPEC_TOKENS]")
```

**Document**: every present token, every missing token, every mismatched value.

#### 1.2 STYLE DRIFT SCAN

```bash
# Inline styles
grep -rn "style={{" src/pages/ src/components/ 2>/dev/null

# Magic values (arbitrary brackets)
grep -rn "\[\(px\|rem\|em\|vh\|vw\|%\)\]" src/pages/ src/components/ 2>/dev/null | grep -v "w-full\|h-full\|w-screen\|h-screen"

# Non-token colors
grep -rn "bg-gray-\|bg-slate-\|bg-zinc-\|bg-neutral-\|bg-blue-\|bg-green-\|bg-red-\|bg-amber-\|bg-yellow-\|bg-purple-\|bg-pink-" src/pages/ src/components/ 2>/dev/null | grep -v "entityColors\|EntityBadge\|getEntityColors"

# Custom shadows
grep -rn "shadow-\[" src/pages/ src/components/ 2>/dev/null

# Custom radii
grep -rn "rounded-\[" src/pages/ src/components/ 2>/dev/null

# Magic font sizes
grep -rn "text-\[" src/pages/ src/components/ 2>/dev/null
```

**Output**: file, line, current value, classification.

#### 1.3 PRIMITIVE USAGE MAP

```bash
# Count imports of existing primitives
grep -rn "from.*WfPrimitives\|from.*fabric\|PageHeader\|FabricCard\|FilterBar\|StatusBadge\|MetricCard\|DataTable\|SidePanel\|FabricDialog\|TeamMemberList\|LoadingSkeleton\|EntityBadge\|EntityColors" src/pages/ src/components/ 2>/dev/null | sort
```

**Output**: which primitives are used, where, and how often.

#### 1.4 ENTITY COLOR PATTERN DETECTION

```bash
grep -rn "violet-100\|violet-800\|cyan-100\|cyan-800\|amber-100\|amber-800\|emerald-100\|emerald-800\|blue-100\|blue-800" src/pages/ src/components/ 2>/dev/null
```

**Output**: every location where semantic entity colors are used ad-hoc.

#### 1.5 PAGE STRUCTURE INVENTORY

```bash
ls src/pages/*.tsx src/pages/**/*.tsx 2>/dev/null
# For each page: note title structure, card usage, table usage, filter usage, dialog usage
```

**Output**: structural inventory of every page.

---

## AGENT 2: ANALYZE AGENT

**Purpose**: Compare discovery output against Fabric spec. Produce gap analysis.  
**Input**: Discovery Agent output + Fabric spec  
**Output**: Prioritized gap report.

### Analysis Dimensions

| Dimension | Check | Severity |
|-----------|-------|----------|
| Token accuracy | Each oklch value matches spec exactly | P0 if different |
| Token completeness | All 18 light + 18 dark + 5 chart tokens present | P0 if missing |
| Primitive coverage | Page uses Fabric primitives where applicable | P1 if using ad-hoc |
| Spacing consistency | Uses scale (space-1..12), no magic values | P1 if magic values |
| Typography | Matches type scale (24/18/16/14/13/12/11px) | P1 if off-scale |
| Shadow usage | Uses token shadows, no custom | P2 if custom |
| Radius | Uses token radii, no custom | P2 if custom |
| Entity colors | Centralized in entity-colors.ts, not ad-hoc | P1 if scattered |
| Import discipline | Imports from @/components/ui/fabric/ | P1 if deep relative |

### Output Format

```
GAP REPORT — [PageName].tsx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Token Drift:     [N] issues (list)
Primitive Gaps:  [N] issues (list)
Spacing:         [N] magic values (list)
Typography:      [N] off-scale (list)
Entity Colors:   [N] ad-hoc (list)
Priority:        P0 / P1 / P2
Recommended Fix: [action]
```

---

## AGENT 3: FIX AGENT (Refactor)

**Purpose**: Apply smallest correct fix for each gap. Never break functionality.

### Hard Rules (Non-Negotiable)

**Rule 1: No Ad-hoc Styling**
- Any inline style (`style={{`) → replace with className + token
- Any magic value (`w-[317px]`) → replace with scale value (`w-80`)
- Any non-token color (`bg-gray-100`) → replace with token (`bg-muted`)
- Custom shadow (`shadow-[...]`) → replace with shadow-sm/md/lg
- Custom radius (`rounded-[...]`) → replace with rounded-md/lg

**Rule 2: Primitives First**
Every repeated UI pattern must use:
- `<PageHeader>` for page titles
- `<FabricCard>` for card surfaces
- `<FilterBar>` for filter rows
- `<StatusBadge>` for status indicators
- `<MetricCard>` for KPI displays
- `<DataTable>` for data tables
- `<SidePanel>` for detail panels
- `<FabricDialog>` for modals
- `<LoadingSkeleton>` for loading states
- `<EntityBadge>` for entity type badges

**Rule 3: Semantic Colors Protected**

```
capability  → violet (NEVER change to neutral)
usecase     → cyan   (NEVER change to neutral)
persona     → amber  (NEVER change to neutral)
valuedriver → emerald(NEVER change to neutral)
pack        → blue
account     → slate
formula     → indigo
job         → orange
workflow    → rose
```

These go through entityColors map, not ad-hoc Tailwind classes.

**Rule 4: Bridge, Don't Break**
- If page imports from WfPrimitives.tsx → keep that import working
- Create bridge re-exports if needed
- Migrate import path in a separate commit/step
- Never leave a page with broken imports

**Rule 5: Smallest Correct Fix**
- Fix one pattern at a time per file
- Build check after every 3 files
- If build breaks → revert last change, diagnose, retry

### Fix Sequence Per Page

```
1. Replace page title structure → <PageHeader>
2. Replace card containers     → <FabricCard>
3. Replace metric displays     → <MetricCard>
4. Replace status badges       → <StatusBadge>
5. Replace filter bars         → <FilterBar>
6. Replace tables              → <DataTable>
7. Replace entity colors       → <EntityBadge> or getEntityColors()
8. Remove inline styles
9. Remove magic values
10. Replace loading spinners   → <LoadingSkeleton>
11. Replace dialogs/panels     → <FabricDialog> / <SidePanel>
```

---

## AGENT 4: VALIDATE AGENT

**Purpose**: Confirm correctness after fixes.

### Validation Gates (All Must Pass)

```
GATE 1: TypeScript Compilation
  Command: npx tsc --noEmit
  Expected: 0 errors, 0 warnings
  
GATE 2: ESLint
  Command: npm run lint
  Expected: 0 errors
  
GATE 3: Build
  Command: npm run build
  Expected: successful completion, no warnings about CSS
  
GATE 4: Visual Structure (automated checks)
  - No <div> acting as page header without <PageHeader>
  - No bg-[#...] or bg-gray-... in page files
  - No style={{ in page files
  - No w-[...] or h-[...] magic values
  
GATE 5: Primitive Adoption
  - Every page imports at least 1 Fabric primitive
  - No page imports from WfPrimitives directly (post-migration)
  
GATE 6: Entity Color Centralization
  - No bg-violet-100 outside entity-colors.ts
  - No bg-cyan-100 outside entity-colors.ts
  - No bg-amber-100 outside entity-colors.ts
  - No bg-emerald-100 outside entity-colors.ts
```

### On Failure

1. Log exact error
2. Identify which fix caused it
3. Revert or repair
4. Re-run all gates
5. Repeat until all pass

---

## AGENT 5: AUDIT AGENT

**Purpose**: Apply enterprise-grade consistency lens.

### Checks (from audit framework)

- [ ] Architecture consistency — all pages use same primitive set
- [ ] Import discipline — barrel imports from @/components/ui/fabric/
- [ ] No duplicate styling systems — only Fabric tokens, no remnants
- [ ] UI contract integrity — props interfaces consistent
- [ ] Data flow correctness — no styling logic in data hooks
- [ ] Accessibility — focus states visible, semantic HTML preserved
- [ ] Dark mode — all colors have dark variants
- [ ] Performance — no unnecessary re-renders from style changes

### Output

```
AUDIT RESULT
━━━━━━━━━━━━
Violations:  [N] (list)
Risks:       [N] (list)
Inconsistencies: [N] (list)
Grade:       PASS / CONDITIONAL / FAIL
```

If FAIL → loop back to FIX AGENT.

---

## AGENT 6: REPORT AGENT

**Purpose**: Produce final deployment report.

**Trigger**: When loop terminates (all gates pass, audit passes).  
**Output**: `frontend/FABRIC_DEPLOYMENT_REPORT.md`

```markdown
# Workflow: Fabric UI System Enforcement

**Start**: [timestamp]  
**End**: [timestamp]  
**Iterations**: [N] complete loops

## Execution Summary

- Pages audited: [N]
- Components audited: [N]
- Token mismatches found: [N]
- Primitive usage instances: [N]
- Drift patterns found: [N]
- Entity color ad-hoc usages: [N]

### Phase 1: Discovery

| Severity | Count |
|----------|-------|
| Critical gaps (P0) | [N] |
| High gaps (P1) | [N] |
| Medium gaps (P2) | [N] |
| Low gaps (P3) | [N] |

### Phase 2: Analysis

| Page | Primitives Added | Drift Removed | Entity Colors Fixed |
|------|-----------------|---------------|---------------------|
| ... | ... | ... | ... |

### Phase 3: Fixes Applied

- TypeScript: ✅ PASS
- ESLint: ✅ PASS
- Build: ✅ PASS
- Visual: ✅ PASS
- Dark mode: ✅ PASS

### Phase 4: Validation

- Architecture: ✅ PASS
- Consistency: ✅ PASS
- Accessibility: ✅ PASS
- Performance: ✅ PASS
- **Grade**: [PASS / CONDITIONAL / FAIL]

### Phase 5: Audit

- Pages using Fabric primitives: [N]/[N] (100%)
- Primitives in use: [list]
- Entity color system: ✅ Centralized
- Token drift: 0
- Inline styles: 0
- Magic values: 0

## Final State

### Remaining Risks

*None identified*

## Sign-off

Value Fabric Platform  
Fabric UI System Deployment Report
```

---

## LOOP TERMINATION CONDITIONS

### STOP (Success)

ALL of:
- ✓ Every page imports from @/components/ui/fabric/
- ✓ Zero inline style={{ }} in src/pages/ and src/components/
- ✓ Zero magic [px/rem/vh] values (except w-full, h-full, w-screen, h-screen)
- ✓ Zero ad-hoc entity colors (all through entity-colors.ts)
- ✓ TypeScript compiles with 0 errors
- ✓ ESLint passes with 0 errors
- ✓ Build succeeds
- ✓ Visual smoke test passes
- ✓ Dark mode verified
- ✓ Audit agent grade = PASS

### STOP (Blocker)

ANY of:
- ✗ Build broken after 3 retry attempts
- ✗ shadcn/ui components cannot be resolved
- ✗ Cannot write to source directory (permissions)

---

## WORKFLOW TRIGGER PROMPT

Copy-paste this into Windsurf to execute:

```
Execute the Fabric UI System Enforcement workflow across frontend/client/src/.

Follow the strict 6-agent loop:
  1. DISCOVER: Scan all tokens, styles, primitives, entity colors, page structures
  2. ANALYZE: Compare against Fabric spec — produce gap report with P0/P1/P2/P3
  3. FIX: Refactor to canonical primitives, remove drift, centralize entity colors
  4. VALIDATE: TypeScript, lint, build, visual, primitive adoption, entity colors
  5. AUDIT: Architecture consistency, import discipline, no duplicate systems, a11y, dark mode
  6. REPORT: Produce FABRIC_DEPLOYMENT_REPORT.md

Loop until:
  - ALL pages use Fabric primitives
  - ZERO inline styles remain
  - ZERO magic values exist
  - Entity colors centralized in entity-colors.ts
  - Build + lint are clean
  - Audit grade is PASS

Apply these non-negotiable rules:
  RULE 1: No ad-hoc styling — inline styles and magic values are forbidden
  RULE 2: Primitives first — PageHeader, FabricCard, FilterBar, StatusBadge, MetricCard, DataTable, SidePanel, FabricDialog, LoadingSkeleton, EntityBadge
  RULE 3: Semantic colors protected — capability→violet, usecase→cyan, persona→amber, valuedriver→emerald (never neutral)
  RULE 4: Bridge, don't break — keep existing imports working during migration
  RULE 5: Zero drift target — eliminate all inconsistency

Priority: Top 5 pages first (Home/Dashboard, GraphExplorer, Library/ValuePacks, FormulaBuilder, Accounts)

Do not stop after partial completion. Continue iterating until all termination conditions are met.

Output: FABRIC_DEPLOYMENT_REPORT.md with changes made, pages refactored, drift eliminated, remaining risks.
```

---

## SINGLE-AGENT FALLBACK

If multi-agent execution is unavailable, collapse to single-agent mode:

```
You are the Fabric UI System Enforcement Agent. Execute all 6 agent
responsibilities sequentially in a single context window:

1. Run all discovery commands (grep scans)
2. Analyze output against spec (gap report)
3. Apply fixes page by page (refactor)
4. Run all validation gates (build/lint)
5. Audit for consistency (architecture review)
6. Produce final report (markdown)

Loop until termination conditions met.
```

---

## BEGIN EXECUTION

Paste the **Workflow Trigger Prompt** into Windsurf and execute.  
Monitor iteration count. Expected: 2-4 complete loops for initial deployment.
