# Fix `usePersistFn` TypeScript Build Error — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the TypeScript error in `apps/web/src/hooks/usePersistFn.ts` so `pnpm run verify:frontend` passes, and add a regression test for the hook.

**Architecture:** This is a single-file type-cast fix plus a focused unit test. The hook creates a stable function reference via `useRef`; the cast from the internal `unknown` return to the generic `ReturnType<T>` was placed on the wrong expression.

**Tech Stack:** React, TypeScript, Vitest, `@testing-library/react`.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `apps/web/src/hooks/usePersistFn.ts` | The hook to fix (line 20). |
| `apps/web/src/hooks/usePersistFn.test.ts` | New regression tests for stability and latest-function behavior. |

---

### Task 1: Reproduce the TypeScript failure

**Files:**
- Read: `apps/web/src/hooks/usePersistFn.ts`

- [ ] **Step 1: Run the frontend type check**

```bash
cd apps/web
pnpm run check
```

- [ ] **Step 2: Confirm the expected failure**

Expected output contains:

```text
src/hooks/usePersistFn.ts(20,49): error TS2322: Type 'unknown' is not assignable to type 'ReturnType<T>'.
```

---

### Task 2: Write the regression test

**Files:**
- Create: `apps/web/src/hooks/usePersistFn.test.ts`

- [ ] **Step 1: Create the test file with the following content**

```typescript
import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { usePersistFn } from './usePersistFn';

describe('usePersistFn', () => {
  it('returns a stable function reference across renders', () => {
    const { result, rerender } = renderHook(
      ({ fn }) => usePersistFn(fn),
      { initialProps: { fn: () => 1 } }
    );

    const firstRef = result.current;
    rerender({ fn: () => 2 });

    expect(result.current).toBe(firstRef);
  });

  it('always calls the latest function', () => {
    const fnA = vi.fn().mockReturnValue('a');
    const fnB = vi.fn().mockReturnValue('b');

    const { result, rerender } = renderHook(
      ({ fn }) => usePersistFn(fn),
      { initialProps: { fn: fnA } }
    );

    expect(result.current()).toBe('a');

    rerender({ fn: fnB });

    expect(result.current()).toBe('b');
    expect(fnA).toHaveBeenCalledTimes(1);
    expect(fnB).toHaveBeenCalledTimes(1);
  });

  it('preserves arguments and return value', () => {
    const fn = (prefix: string, suffix: number) => `${prefix}-${suffix}`;
    const { result } = renderHook(() => usePersistFn(fn));

    expect(result.current('answer', 42)).toBe('answer-42');
  });
});
```

- [ ] **Step 2: Run the new test to verify it passes**

```bash
cd apps/web
pnpm test src/hooks/usePersistFn.test.ts
```

Expected: 3 tests pass.

---

### Task 3: Fix the type cast in the hook

**Files:**
- Modify: `apps/web/src/hooks/usePersistFn.ts:20`

- [ ] **Step 1: Update line 20**

Replace:

```typescript
  const persistFn = useRef<T>(
    ((...args: Parameters<T>): ReturnType<T> => fnRef.current(...args)) as T
  );
```

With:

```typescript
  const persistFn = useRef<T>(
    ((...args: Parameters<T>): ReturnType<T> =>
      fnRef.current(...args) as ReturnType<T>) as T
  );
```

- [ ] **Step 2: Run the type check again**

```bash
cd apps/web
pnpm run check
```

Expected: no errors.

- [ ] **Step 3: Re-run the unit test**

```bash
cd apps/web
pnpm test src/hooks/usePersistFn.test.ts
```

Expected: 3 tests pass.

---

### Task 4: Verify the full frontend gate

**Files:**
- None (validation only)

- [ ] **Step 1: Run the full frontend verification**

```bash
cd apps/web
pnpm run verify:frontend
```

Expected: passes (exit code 0).

---

### Task 5: Commit

- [ ] **Step 1: Stage the changed files**

```bash
git add apps/web/src/hooks/usePersistFn.ts apps/web/src/hooks/usePersistFn.test.ts
```

- [ ] **Step 2: Commit**

```bash
git commit -m "fix(web): cast persisted fn return to ReturnType<T> and add regression tests

- Fixes TS2322 in usePersistFn under tsc --noEmit
- Adds tests for reference stability, latest-fn dispatch, and arg/return preservation"
```

---

## Self-Review

1. **Spec coverage:** Implements Task 1 of the production-readiness design (frontend TypeScript build error).
2. **Placeholder scan:** No TBD/TODO/"add error handling" placeholders; all code and commands are explicit.
3. **Type consistency:** `ReturnType<T>` cast matches the generic signature in the hook; test types match the hook's `PersistableFunction` constraint.
