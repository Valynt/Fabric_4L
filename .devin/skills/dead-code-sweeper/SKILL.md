---
skill_id: dead-code-sweeper
name: dead-code-sweeper
version: 1.0.0
description: Identify and safely remove dead code including orphan pages, unreachable routes, unused exports, mock data blocks, and duplicate workspace systems. Use when cleaning up the codebase, after major refactors, or when the FRONTEND_AUDIT_REPORT.md dead code list needs action. Targets 2,500+ confirmed dead lines plus uncatalogued backend dead code.
side_effects: write
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Dead Code Sweeper

Identifies dead code across frontend and backend, verifies it is unreachable, and produces safe removal patches with dependency analysis.

## When to Use

- After a major refactor or workspace system migration
- When cleaning up before a release
- When codebase size seems disproportionate to functionality
- When asked to "remove dead code", "clean up", or "reduce code surface"
- Periodic hygiene sweep (monthly)

## Known Dead Code Inventory

### Confirmed Dead — Frontend (2,500+ lines)

| Target | File(s) | Lines | Reason | Confidence |
|--------|---------|-------|--------|------------|
| Stage1Discovery | `pages/value-studio/Stage1Discovery.tsx` | ~330 | All Stage routes redirect to new workspace | HIGH |
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

### Suspected Dead — Backend

| Target | Indicator | Verification |
|--------|-----------|--------------|
| Unused tool files | Tool exists in `src/tools/` but not in `__init__.py` | Check imports vs files |
| Unused service methods | Service method defined but never called from routes | Grep for method name in routes |
| Stale migration helpers | One-time scripts in `scripts/` | Check git log for last modification |

## Workflow Steps

### Step 1: Choose Scope

- `frontend` — Sweep pages, components, hooks
- `layer1` through `layer6` — Sweep specific layer
- `all` — Full sweep
- Specific file path — Check if that file is dead

### Step 2: Frontend Dead Code Scan

#### 2a. Orphan Pages (not routed)

```bash
# All page files
find frontend/client/src/pages -name "*.tsx" -not -name "*.test.*" | sort

# Lazy imports in App.tsx
grep "lazy.*import.*pages/" frontend/client/src/App.tsx | sort
```

Any page NOT imported in App.tsx is an orphan candidate.

#### 2b. Unused Exports

```bash
# For each exported component/hook, check import count
grep -rn "export.*function\|export.*const" frontend/client/src/hooks/*.ts | while read line; do
  export_name=$(echo "$line" | grep -oP "(?:function|const)\s+\K\w+")
  count=$(grep -rn "$export_name" frontend/client/src/ --include="*.ts" --include="*.tsx" | grep -v "export" | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "UNUSED: $export_name in $line"
  fi
done
```

#### 2c. Mock Data Blocks

```bash
grep -rn "MOCK_\|mockData\|mock_data\|PLACEHOLDER\|coming soon\|TODO.*remove" frontend/client/src/ --include="*.tsx" --include="*.ts"
```

#### 2d. Duplicate Systems

```bash
# Old system (should be dead)
find frontend/client/src/pages/value-studio -name "*.tsx" 2>/dev/null

# Verify routes redirect
grep "value-studio" frontend/client/src/App.tsx
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

For each service file:
```bash
# Extract public methods
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

For each dead code candidate, verify truly unreachable:

1. **Import check:** `grep -rn "import.*{name}" . --include="*.py" --include="*.ts" --include="*.tsx"`
2. **String reference check:** `grep -rn "{name}" . --include="*.py" --include="*.ts" --include="*.tsx"`
3. **Test dependency check:** `grep -rn "{name}" tests/ frontend/client/src/**/*.test.*`
4. **Git blame check:** `git log --oneline -5 {file}`

**Confidence levels:**
- **HIGH:** Zero import references, zero string references, file not modified in 30+ days
- **MEDIUM:** Zero import references but string references exist
- **LOW:** Referenced in tests only

### Step 5: Safe Removal

**HIGH confidence candidates:**
1. Delete the file
2. Remove imports from barrel exports (`index.ts`, `__init__.py`)
3. Remove route entries in `App.tsx` or `main.py`
4. Run tests to verify:
   ```bash
   cd frontend && pnpm tsc --noEmit && pnpm test --run
   python -m pytest tests/ -x -q
   ```

**MEDIUM confidence candidates:**
1. Add `// DEAD_CODE_CANDIDATE: {reason}` comment at top
2. Do NOT delete until human confirms

### Step 6: Report

```markdown
## Dead Code Sweep — {date}

### Removed (HIGH confidence)
| File | Lines | Reason |
|------|-------|--------|

### Flagged for Review (MEDIUM confidence)
| File | Lines | Reason | Blocker |
|------|-------|--------|---------|

### False Positives
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
- **Check git stash/branches** before deleting recently-created files
- **Prefer commenting over deleting** for MEDIUM confidence candidates
