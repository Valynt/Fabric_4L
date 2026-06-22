# Sprint 1 — Code-Health Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove confirmed dead/duplicate code and close ownership gaps identified in the Repowise analysis, while keeping all CI gates green.

**Architecture:** This sprint performs safe, validated deletions only. We remove legacy duplicate adapter files, the broken legacy compliance package, one unreferenced frontend re-export wrapper, and tighten CODEOWNERS coverage for auth/routing files. No risky refactoring of live code.

**Tech Stack:** Python, TypeScript, Git, GitHub CODEOWNERS, pnpm, pytest.

---

## File Structure

| File | Responsibility |
|---|---|
| `services/layer1-ingestion/src/adapters/sec_edgar.py` | Legacy duplicate of canonical adapter — **delete**. |
| `services/layer1-ingestion/src/adapters/xbrl_parser.py` | Legacy duplicate of canonical adapter — **delete**. |
| `services/layer1-ingestion/src/compliance/__init__.py` | Broken legacy package init referencing deleted files — **delete**. |
| `services/layer1-ingestion/src/compliance/url_safety.py` | Legacy copy of canonical compliance helper — **delete**. |
| `apps/web/src/features/intelligence-workspace/tabs/value-model/ValueModelTab.tsx` | Unreferenced re-export wrapper — **delete**. |
| `.github/CODEOWNERS` | Add explicit security-team coverage for 3 auth/routing files — **modify**. |

---

## Prerequisite: Working Tree Baseline

Before starting Sprint 1 tasks, ensure the working tree is in a known-good state:

- [ ] **Step 1: Check git status**

```bash
git status --short
```

Expected: No unexpected uncommitted changes in the files listed above. If there is unrelated drift (docker-compose relocations, CI scripts, s2s-auth work), it should already be committed or reverted per Phase 0 of the design spec.

- [ ] **Step 2: Confirm the frontend typecheck baseline**

```bash
cd apps/web
pnpm run typecheck
```

Expected: Passes except for any pre-existing, unrelated errors documented in `docs/superpowers/specs/2026-06-22-production-readiness-top5-design.md`.

- [ ] **Step 3: Confirm the backend test baseline**

```bash
cd services/layer1-ingestion
python -m pytest tests/unit/test_canonical_imports.py tests/compliance/ tests/unit/test_robots_checker_modes.py -v
```

Expected: All selected tests pass.

---

## Task 1: Remove Legacy Duplicate Adapter Files

**Files:**
- Delete: `services/layer1-ingestion/src/adapters/sec_edgar.py`
- Delete: `services/layer1-ingestion/src/adapters/xbrl_parser.py`
- Keep: `services/layer1-ingestion/src/layer1_ingestion/adapters/sec_edgar.py`
- Keep: `services/layer1-ingestion/src/layer1_ingestion/adapters/xbrl_parser.py`

These two legacy files are content-identical duplicates of the canonical adapters under `layer1_ingestion/adapters/`. No code imports from the legacy `src/adapters/` path.

- [ ] **Step 1: Verify no imports from the legacy adapter path**

```bash
cd C:/Users/BBB/Fabric_4L
grep -R "from adapters\|import adapters\|from \\.\\.adapters\|from src\.adapters\|from services\.layer1_ingestion\.src\.adapters" services/layer1-ingestion/src services/layer1-ingestion/tests --include='*.py'
```

Expected: No output.

- [ ] **Step 2: Verify the canonical copies exist and differ only by line endings**

```bash
diff -qw services/layer1-ingestion/src/adapters/sec_edgar.py services/layer1-ingestion/src/layer1_ingestion/adapters/sec_edgar.py
diff -qw services/layer1-ingestion/src/adapters/xbrl_parser.py services/layer1-ingestion/src/layer1_ingestion/adapters/xbrl_parser.py
```

Expected: Both commands report `Files ... are identical`.

- [ ] **Step 3: Delete the legacy duplicate files**

```bash
git rm services/layer1-ingestion/src/adapters/sec_edgar.py services/layer1-ingestion/src/adapters/xbrl_parser.py
```

Expected: Files staged for deletion.

- [ ] **Step 4: Check if the legacy adapters directory is now empty of source files**

```bash
ls -la services/layer1-ingestion/src/adapters/
```

Expected: Only `__init__.py`, `base.py`, `pdf_adapter.py`, `registry.py`, `value_fabric_api.py`, and `__pycache__` remain. Do not delete the directory or the remaining files in this sprint.

- [ ] **Step 5: Run Layer 1 tests to confirm nothing breaks**

```bash
cd services/layer1-ingestion
python -m pytest tests/unit/test_canonical_imports.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the deletion**

```bash
git commit -m "chore(layer1): remove legacy duplicate adapter files

- Deletes services/layer1-ingestion/src/adapters/sec_edgar.py
- Deletes services/layer1-ingestion/src/adapters/xbrl_parser.py
- Canonical copies remain under layer1_ingestion/adapters/"
```

---

## Task 2: Remove the Broken Legacy Compliance Package

**Files:**
- Delete: `services/layer1-ingestion/src/compliance/__init__.py`
- Delete: `services/layer1-ingestion/src/compliance/url_safety.py`
- Keep: `services/layer1-ingestion/src/layer1_ingestion/compliance/`

The legacy `src/compliance/` package is no longer imported anywhere. Its `__init__.py` references `pii_scanner` and `robots_checker` at legacy paths that no longer exist, causing a broken package.

- [ ] **Step 1: Verify no imports from the legacy compliance package**

```bash
cd C:/Users/BBB/Fabric_4L
grep -R "from compliance\|import compliance\|from \\.\\.compliance\|from src\.compliance\|from services\.layer1_ingestion\.src\.compliance" services/layer1-ingestion/src services/layer1-ingestion/tests --include='*.py'
```

Expected: No output.

- [ ] **Step 2: Confirm the canonical compliance package exists**

```bash
ls services/layer1-ingestion/src/layer1_ingestion/compliance/
```

Expected: `__init__.py`, `pii_scanner.py`, `robots_checker.py`, `url_safety.py`.

- [ ] **Step 3: Delete the legacy compliance files**

```bash
git rm services/layer1-ingestion/src/compliance/__init__.py services/layer1-ingestion/src/compliance/url_safety.py
rmdir services/layer1-ingestion/src/compliance
```

Expected: Directory removed; git stages the deletions.

- [ ] **Step 4: Run compliance-related tests**

```bash
cd services/layer1-ingestion
python -m pytest tests/compliance/ tests/unit/test_robots_checker_modes.py tests/security/test_global_robots_cache_isolation_postgres.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the deletion**

```bash
git commit -m "chore(layer1): remove broken legacy compliance package

- Deletes services/layer1-ingestion/src/compliance/__init__.py
- Deletes services/layer1-ingestion/src/compliance/url_safety.py
- Canonical package remains under layer1_ingestion/compliance/"
```

---

## Task 3: Remove the Unreferenced Frontend Re-export Wrapper

**Files:**
- Delete: `apps/web/src/features/intelligence-workspace/tabs/value-model/ValueModelTab.tsx`

This file is a one-line re-export wrapper that is not imported by `workspaceTabRegistry.ts` or any other consumer. The studio tab registry imports directly from `@/pages/studio/ValueModelTab`.

- [ ] **Step 1: Verify the wrapper is unreferenced**

```bash
cd C:/Users/BBB/Fabric_4L
grep -R "tabs/value-model/ValueModelTab\|features/intelligence-workspace/tabs/value-model" apps/web/src --include='*.ts' --include='*.tsx'
```

Expected: Only the file itself matches (or no matches if the grep excludes the file).

- [ ] **Step 2: Delete the wrapper**

```bash
git rm apps/web/src/features/intelligence-workspace/tabs/value-model/ValueModelTab.tsx
```

Expected: File staged for deletion.

- [ ] **Step 3: Run frontend typecheck**

```bash
cd apps/web
pnpm run typecheck
```

Expected: No new errors caused by the deletion.

- [ ] **Step 4: Run frontend unit tests**

```bash
cd apps/web
pnpm test --run
```

Expected: PASS (or only pre-existing failures).

- [ ] **Step 5: Commit the deletion**

```bash
git commit -m "chore(web): remove unreferenced value-model tab wrapper

- Deletes apps/web/src/features/intelligence-workspace/tabs/value-model/ValueModelTab.tsx
- Consumers import directly from @/pages/studio/ValueModelTab"
```

---

## Task 4: Confirm ExecutionMetrics Is Already Removed

**Files:**
- Verify: `services/layer1-ingestion/src/layer1_ingestion/crawler/telemetry.py`

Repowise flagged `ExecutionMetrics` as dead code, but it is no longer present in the codebase.

- [ ] **Step 1: Search for ExecutionMetrics**

```bash
cd C:/Users/BBB/Fabric_4L
grep -R "ExecutionMetrics" services/layer1-ingestion --include='*.py'
```

Expected: No output.

- [ ] **Step 2: Verify telemetry.py is still imported and tests pass**

```bash
cd services/layer1-ingestion
python -m pytest tests/unit/test_celery_tasks.py -v -k telemetry
```

Expected: Tests pass (or no tests match the filter, which is also acceptable).

No commit is needed for this task.

---

## Task 5: Close CODEOWNERS Security-Review Gap

**Files:**
- Modify: `.github/CODEOWNERS`

Three auth/routing files are covered by the broad `apps/web/` pattern but not by the security-focused `**/*auth*` pattern:

- `apps/web/src/components/routing/RequireClerkAuth.tsx`
- `apps/web/src/components/routing/UnifiedRouteGuard.tsx`
- `apps/web/src/pages/ClerkSignIn.tsx`

- [ ] **Step 1: Confirm the files exist and lack security-team coverage**

```bash
ls apps/web/src/components/routing/RequireClerkAuth.tsx apps/web/src/components/routing/UnifiedRouteGuard.tsx apps/web/src/pages/ClerkSignIn.tsx
grep -n "RequireClerkAuth\|UnifiedRouteGuard\|ClerkSignIn" .github/CODEOWNERS || true
```

Expected: Files exist; no explicit entries for them in CODEOWNERS.

- [ ] **Step 2: Add explicit auth/routing patterns**

Edit `.github/CODEOWNERS` and add the following block immediately after the existing `**/*auth*` line (around line 15):

```text
# Frontend auth/routing components that do not match **/*auth* but require security review
apps/web/src/components/routing/RequireClerkAuth.tsx @value-fabric/security-leads @value-fabric/frontend-leads
apps/web/src/components/routing/UnifiedRouteGuard.tsx @value-fabric/security-leads @value-fabric/frontend-leads
apps/web/src/pages/ClerkSignIn.tsx @value-fabric/security-leads @value-fabric/frontend-leads
```

- [ ] **Step 3: Validate CODEOWNERS syntax**

```bash
cd C:/Users/BBB/Fabric_4L
git check-attr -a .github/CODEOWNERS
```

Expected: No errors.

- [ ] **Step 4: Commit the change**

```bash
git add .github/CODEOWNERS
git commit -m "chore(ownership): add security coverage for frontend auth/routing files

- Require security-leads + frontend-leads review for RequireClerkAuth, UnifiedRouteGuard, and ClerkSignIn"
```

---

## Task 6: Sprint Verification

- [ ] **Step 1: Run the frontend verification gate**

```bash
cd apps/web
pnpm run verify:frontend
```

Expected: PASS.

- [ ] **Step 2: Run Layer 1 tests**

```bash
cd services/layer1-ingestion
python -m pytest tests/unit/test_canonical_imports.py tests/compliance/ tests/unit/test_robots_checker_modes.py tests/security/test_global_robots_cache_isolation_postgres.py -v
```

Expected: PASS.

- [ ] **Step 3: Run structural preflight**

```bash
cd C:/Users/BBB/Fabric_4L
python scripts/ci/structural_preflight.py
```

Expected: PASS.

- [ ] **Step 4: Run contract tests**

```bash
cd C:/Users/BBB/Fabric_4L
make contract-tests
```

Expected: PASS.

- [ ] **Step 5: Report removed lines**

```bash
git diff --stat HEAD~4..HEAD
```

Expected: Shows net deletion of ≥200 lines from the files removed in Tasks 1–3.

---

## Self-Review

1. **Spec coverage:** Each validated Sprint 1 item from the design spec has a task: duplicate adapters, legacy compliance package, unreferenced wrapper, CODEOWNERS gap, ExecutionMetrics verification.
2. **Placeholder scan:** No TBD/TODO placeholders; every step has an exact command or file edit.
3. **Type consistency:** CODEOWNERS usernames match existing entries; deleted files are not referenced elsewhere.
4. **Risk check:** No live code is modified except CODEOWNERS; all deletions are preceded by import/reference verification.
