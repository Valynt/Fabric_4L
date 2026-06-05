---
workflow_id: dead-code-sweeper
name: Dead Code Sweeper
version: 1.0.0
description: Identify and safely remove dead code including orphan pages, unreachable routes, unused exports, mock data blocks, and duplicate workspace systems. Use when cleaning up the codebase, after major refactors, or when the FRONTEND_AUDIT_REPORT.md dead code list needs action. Targets 2,500+ confirmed dead lines plus uncatalogued backend dead code.
pattern: manager-worker
risk_level: medium
category: quality-debt
---

# Dead Code Sweeper

Systematically identifies dead code across frontend and backend layers, verifies it is truly unreachable, and produces safe removal patches with dependency analysis.

## When to Use

- After a major refactor or workspace system migration
- When cleaning up before a release
- When the codebase size seems disproportionate to functionality
- When asked to "remove dead code", "clean up", or "reduce code surface"
- Periodic hygiene sweep (monthly recommended)

## Known Dead Code Inventory (from FRONTEND_AUDIT_REPORT.md)

### Confirmed Dead — Frontend

| Target | File(s) | Lines | Reason | Confidence |
|--------|---------|-------|--------|------------|
| Stage1Discovery | `pages/value-studio/Stage1Discovery.tsx` | ~330 | All Stage routes redirect to new workspace system | HIGH |
| Stage2Mapping | `pages/value-studio/Stage2Mapping.tsx` | ~325 | Same — redirected | HIGH |
| Stage3Modeling | `pages/value-studio/Stage3Modeling.tsx` | ~330 | Same — redirected | HIGH |
| Stage4Validation | `pages/value-studio/Stage4Validation.tsx` | ~325 | Same — redirected | HIGH |
| Stage5Narrative | `pages/value-studio/Stage5Narrative.tsx` | ~330 | Same — redirected | HIGH |
| Stage6Tracking | `pages/value-studio/Stage6Tracking.tsx` | ~315 | Same — redirected | HIGH |
| ValueStudioShell | `pages/value-studio/ValueStudioShell.tsx` | ~200 | Only used by dead Stage pages | HIGH |
| Home | `pages/Home.tsx` | ~100 | Orphan — `/home` renders `ValueNarrativeHome` | HIGH |
| OntologyBrowser | `pages/OntologyBrowser.tsx` | ~200 | Orphan — not imported in App.tsx | MEDIUM |
| Mock data blocks | `pages/SourceConfiguration.tsx` lines ~50-80 | ~30 | `MOCK_SOURCES` array, `alert('coming soon')` | HIGH |
| Mock data blocks | `pages/FormulaBuilder.tsx` lines ~50-70 | ~20 | `// Constants & Mock Data` section | HIGH |

**Total confirmed frontend:** ~2,505 lines

### Suspected Dead — Backend (needs verification)

| Target | Indicator | Verification |
|--------|-----------|--------------|
| Unused tool implementations | Tool exists in `src/tools/` but not in `__init__.py` imports | Check `__init__.py` imports vs files in `src/tools/` |
| Unused service methods | Service method defined but never called from routes | Grep for method name across `src/api/routes/` |
| Stale migration helpers | One-time migration scripts in `scripts/` | Check git log for last modification |

## Workflow Steps

### Step 1: Choose Scope

Accept one of:
- `frontend` — Sweep frontend pages, components, hooks
- `layer1` through `layer6` — Sweep a specific backend layer
- `all` — Full sweep
- A specific file path — Check if that file is dead

### Step 2: Frontend Dead Code Scan

#### 2a. Orphan Pages (not routed)

Check every page file against App.tsx imports:

```bash
# List all page files
find apps/web/src/pages -name "*.tsx" -not -name "*.test.*" | sort

# List all lazy imports in App.tsx
grep "lazy.*import.*pages/" apps/web/src/App.tsx | sort
```

Any page file NOT imported in App.tsx is an orphan candidate.

#### 2b. Unused Exports

Check for exports that have zero import references:

```bash
# For each exported component/hook, check import count
grep -rn "export.*function\|export.*const\|export default" apps/web/src/hooks/*.ts | while read line; do
  export_name=$(echo "$line" | grep -oP "(?:function|const)\s+\K\w+")
  if [ -n "$export_name" ]; then
    count=$(grep -rn "$export_name" apps/web/src/ --include="*.ts" --include="*.tsx" | grep -v "export" | wc -l)
    if [ "$count" -eq 0 ]; then
      echo "UNUSED: $export_name in $line"
    fi
  fi
done
```

#### 2c. Mock Data Blocks

```bash
grep -rn "MOCK_\|mockData\|mock_data\|PLACEHOLDER\|coming soon\|TODO.*remove" apps/web/src/ --include="*.tsx" --include="*.ts"
```

#### 2d. Duplicate Systems

Check for the old Value Studio stages vs new Intelligence/Studio tabs:

```bash
# Old system (should be dead)
find apps/web/src/pages/value-studio -name "*.tsx" 2>/dev/null

# Verify routes redirect
grep "value-studio" apps/web/src/App.tsx
```

### Step 3: Backend Dead Code Scan

#### 3a. Unused Tool Files

```bash
# Files in tools/ directory
ls services/layer4-agents/src/tools/*.py | xargs -I{} basename {}

# Imports in __init__.py
grep "^from \." services/layer4-agents/src/tools/__init__.py
```

Any tool file not imported in `__init__.py` is a dead code candidate.

#### 3b. Unused Service Methods

For each service file, extract public methods and check if they're called from routes:

```bash
# Extract public methods from a service
grep "async def [^_]" services/layer4-agents/src/services/{service}.py

# Check if each method is referenced in routes
grep -rn "{method_name}" services/layer4-agents/src/api/routes/ --include="*.py"
```

#### 3c. Unused Route Files

```bash
# Route files
ls services/layer4-agents/src/api/routes/*.py

# Routes registered in main.py
grep "include_router\|app\.include" services/layer4-agents/src/api/main.py
```

### Step 4: Verify Before Removal

For each dead code candidate, verify it is truly unreachable:

1. **Import check:** `grep -rn "import.*{name}" . --include="*.py" --include="*.ts" --include="*.tsx"`
2. **String reference check:** `grep -rn "{name}" . --include="*.py" --include="*.ts" --include="*.tsx"` (catches dynamic imports)
3. **Test dependency check:** `grep -rn "{name}" tests/ apps/web/src/**/*.test.*` (don't break tests)
4. **Git blame check:** `git log --oneline -5 {file}` (recently modified files may be in-progress, not dead)

**Confidence levels:**
- **HIGH:** Zero import references, zero string references, file not modified in 30+ days
- **MEDIUM:** Zero import references but string references exist (may be dynamic import or config)
- **LOW:** Referenced in tests only — may be intentionally kept for test coverage

### Step 5: Safe Removal

For HIGH confidence candidates only:

1. Delete the file
2. Remove any imports of the deleted file from barrel exports (`index.ts`, `__init__.py`)
3. Remove any route entries in `App.tsx` or `main.py` that reference the deleted page/route
4. Run tests to verify nothing breaks:
   ```bash
   cd frontend && pnpm tsc --noEmit && pnpm test --run
   python -m pytest tests/ -x -q
   ```

For MEDIUM confidence candidates:
1. Add a `// DEAD_CODE_CANDIDATE: {reason}` comment at the top
2. Do NOT delete until a human confirms

### Step 6: Report

Produce a summary:

```markdown
## Dead Code Sweep — {date}

### Removed (HIGH confidence)
| File | Lines | Reason |
|------|-------|--------|

### Flagged for Review (MEDIUM confidence)
| File | Lines | Reason | Blocker |
|------|-------|--------|---------|

### False Positives (verified alive)
| File | Why It's Alive |
|------|---------------|

### Impact
- Lines removed: {N}
- Files deleted: {N}
- Bundle size impact: ~{N}KB (estimated)
```

## Safety Rules

- **Never delete test files** unless the code they test was also deleted
- **Never delete `shared/identity/`** (AGENTS.md P0 rule #2)
- **Never delete migration files** (AGENTS.md P0 rule #3)
- **Never delete `contracts/`** manifests without confirming the tool is also deleted
- **Check git stash/branches** before deleting recently-created files — they may be work-in-progress
- **Prefer commenting over deleting** for MEDIUM confidence candidates

## See Also

- **Skill:** `skills/dead-code-sweeper/SKILL.md` — Programmatic agent skill for dead code identification
- **Related Workflows:**
  - `/facade-page-connector` — Rewire pages from mock data to real backend hooks before removing
  - `/deprecation-migrator` — Fix anti-patterns before removing code
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "dead-code-sweeper-001",
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
