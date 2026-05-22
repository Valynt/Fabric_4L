# Dead Code Sweep Report — 2026-04-28

## Summary

Successfully removed **2,592 lines** of confirmed dead code from the frontend codebase.

## Removed (HIGH Confidence)

| File | Lines | Reason |
|------|-------|--------|
| `pages/value-studio/_deprecated/Stage1Discovery.tsx` | 252 | Superseded by new workspace system (redirects to `/intelligence/:id/signals`) |
| `pages/value-studio/_deprecated/Stage2Mapping.tsx` | 308 | Superseded by `studio/ActionPlanTab.tsx` |
| `pages/value-studio/_deprecated/Stage3Modeling.tsx` | 271 | Superseded by `studio/ValueModelTab.tsx` |
| `pages/value-studio/_deprecated/Stage4Validation.tsx` | 309 | Superseded by `studio/ValueModelTab.tsx` |
| `pages/value-studio/_deprecated/Stage5Narrative.tsx` | 282 | Superseded by `studio/NarrativeTab.tsx` |
| `pages/value-studio/_deprecated/Stage6Tracking.tsx` | 357 | Superseded by `studio/NarrativeTab.tsx` |
| `pages/value-studio/_deprecated/ValueStudio.test.tsx` | 112 | Tests for dead Stage components |
| `pages/value-studio/_deprecated/README.md` | 21 | Documentation for dead code |
| `pages/value-studio/ValueStudioShell.tsx` | 237 | Only used by dead Stage pages (superseded by `components/workspace/ValueStudioShell.tsx`) |
| `pages/Home.tsx` | 321 | Orphan page — `/home` route uses `ValueNarrativeHome.tsx` instead |
| `pages/OntologyBrowser.tsx` | 122 | Orphan page — not imported in App.tsx routes |

**Total Files Deleted:** 11  
**Total Lines Removed:** ~2,592

## Verification

### Import References Check
- Zero import references to deleted files across the codebase
- No route entries in App.tsx reference the deleted pages
- No test files import the deleted components (except the test file that was also deleted)

### Git History Check
- All deleted files last modified 30+ days ago (deprecated in Sprint 3)
- `_deprecated` folder was explicitly created to house dead code per commit `afec877`

### Build Verification
```bash
# TypeScript check: Pre-existing errors only (unrelated to deletions)
pnpm tsc --noEmit

# Test suite: No failures related to deleted files
# Failures are pre-existing (missing API mocks in ValuePacks.test.tsx)
pnpm test --run
```

## Impact

- **Bundle Size:** ~75-100KB estimated reduction (unminified)
- **Maintenance Surface:** Reduced confusion between old/new Value Studio systems
- **Code Clarity:** Orphan pages removed, routing intent clearer

## Safety Rules Followed

- [x] No test files deleted unless testing dead code (ValueStudio.test.tsx deleted together with its components)
- [x] `shared/identity/` untouched (AGENTS.md P0 rule #2)
- [x] No migration files modified (AGENTS.md P0 rule #3)
- [x] No contracts modified
- [x] All deletions verified with git history check
