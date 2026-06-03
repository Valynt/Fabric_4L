# Frontend Refactoring Patterns Reference

This file documents the nine concrete refactoring patterns used in the Fabric_4L audit. Read this file when deciding which refactors to apply after running `scan_frontend.sh`.

## Table of Contents
1. [Dead Store Removal](#1-dead-store-removal)
2. [Dead Export Pruning](#2-dead-export-pruning)
3. [Centralized Query Key Registry](#3-centralized-query-key-registry)
4. [Shared QueryState Component](#4-shared-querystate-component)
5. [Centralized API Layer Config](#5-centralized-api-layer-config)
6. [Dev-Only Bundle Gating](#6-dev-only-bundle-gating)
7. [Route-Level Code Splitting](#7-route-level-code-splitting)
8. [RouteGuard Auth Check](#8-routeguard-auth-check)
9. [Centralized Polling Hook](#9-centralized-polling-hook)

---

## 1. Dead Store Removal

**Signal:** Zustand store file with zero imports outside `stores/` directory.

**Fix:** Delete the store file and remove its re-export from `stores/index.ts`.

**Risk:** Low — verify no dynamic `useStore` calls reference it by name string.

---

## 2. Dead Export Pruning

**Signal:** `scan_frontend.sh [10]` reports an exported symbol with zero external imports.

**Fix:** Remove the export keyword (or delete the function/const entirely if it is truly unreachable). For hooks, check if the symbol is re-exported via an index barrel before deleting.

**Common false positives:** test utilities (`test-utils.tsx`), barrel re-exports (`index.ts`).

---

## 3. Centralized Query Key Registry

**Signal:** Multiple hooks define their own `const FOO_KEYS = { ... }` objects.

**Fix:** Create `hooks/queryKeys.ts` with a single `QK` namespace:

```ts
export const QK = {
  ingestion: {
    all: () => ['ingestion'] as const,
    jobs: () => [...QK.ingestion.all(), 'jobs'] as const,
    job: (id: string) => [...QK.ingestion.jobs(), id] as const,
  },
  // ... other domains
};
```

Replace each local `FOO_KEYS` with `QK.foo`. This enables global cache invalidation: `queryClient.invalidateQueries({ queryKey: QK.ingestion.all() })`.

---

## 4. Shared QueryState Component

**Signal:** Multiple page components repeat the same `if (isLoading) return <Spinner>` / `if (error) return <ErrorBanner>` pattern.

**Fix:** Create `components/QueryState.tsx`:

```tsx
interface QueryStateProps {
  isLoading?: boolean;
  error?: Error | null;
  isEmpty?: boolean;
  emptyMessage?: string;
  children: React.ReactNode;
}

export function QueryState({ isLoading, error, isEmpty, emptyMessage, children }: QueryStateProps) {
  if (isLoading) return <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>;
  if (error) return <div className="p-4 text-red-600 bg-red-50 rounded">{error.message}</div>;
  if (isEmpty) return <div className="p-8 text-center text-neutral-400">{emptyMessage ?? 'No data found.'}</div>;
  return <>{children}</>;
}
```

Wrap page content: `<QueryState isLoading={isLoading} error={error}>{/* page body */}</QueryState>`.

---

## 5. Centralized API Layer Config

**Signal:** `scan_frontend.sh [5]` finds `import.meta.env.VITE_L[N]_PREFIX` reads outside a central config file.

**Fix:** Create `lib/apiConfig.ts`:

```ts
export const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';
export const L1_PREFIX = import.meta.env.VITE_L1_PREFIX || '/ingest';
export const L2_PREFIX = import.meta.env.VITE_L2_PREFIX || '/extract';
export const L3_PREFIX = import.meta.env.VITE_L3_PREFIX || '/graph';
export const L4_PREFIX = import.meta.env.VITE_L4_PREFIX || '/agents';
export function apiUrl(prefix: string, path: string) { return `${API_BASE}${prefix}${path}`; }
```

Update all callers to import from `@/lib/apiConfig`. The `api/client.ts` layer-map is the canonical consumer; other files should import from `apiConfig`, not re-read env vars.

---

## 6. Dev-Only Bundle Gating

**Signal:** `scan_frontend.sh [6]` finds a static `import { ReactQueryDevtools }` not gated on `import.meta.env.DEV`.

**Fix:** Replace static import with a dynamic lazy import:

```tsx
// In main.tsx
const ReactQueryDevtools = import.meta.env.DEV
  ? React.lazy(() =>
      import('@tanstack/react-query-devtools').then(m => ({
        default: m.ReactQueryDevtools,
      }))
    )
  : null;

// In JSX
{import.meta.env.DEV && ReactQueryDevtools && (
  <Suspense fallback={null}>
    <ReactQueryDevtools initialIsOpen={false} />
  </Suspense>
)}
```

This eliminates the ~40 kB devtools chunk from production bundles.

---

## 7. Route-Level Code Splitting

**Signal:** `scan_frontend.sh [7]` finds eager `import PageName from './pages/PageName'` in the routing file.

**Fix:** Convert all page imports to `React.lazy` and wrap routes in `<Suspense>`:

```tsx
// Before
import Dashboard from './pages/Dashboard';

// After
const Dashboard = React.lazy(() => import('./pages/Dashboard'));

// In router
<Suspense fallback={<div className="flex h-full items-center justify-center"><Loader2 className="animate-spin" /></div>}>
  <Route path="/dashboard" component={Dashboard} />
</Suspense>
```

Each page now becomes a separate chunk. Initial bundle drops to only the routing shell + auth context.

---

## 8. RouteGuard Auth Check

**Signal:** `scan_frontend.sh [8]` reports no auth check in the routing guard, or the guard only checks tier/role without verifying `isAuthenticated`.

**Fix:** Always check authentication before tier:

```tsx
function RouteGuard({ requiredTier, children }: RouteGuardProps) {
  const { isAuthenticated } = useAuth();
  const { tier } = useUserTierStore();

  // 1. Auth check first — redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Redirect to="/login" />;
  }

  // 2. Tier check — redirect to upgrade/home if insufficient tier
  if (requiredTier && !hasSufficientTier(tier, requiredTier)) {
    return <Redirect to="/" />;
  }

  return <>{children}</>;
}
```

**Critical:** Skipping the auth check creates a "Fail-Open" vulnerability where unauthenticated users can access any route that has a matching tier in local storage.

---

## 9. Centralized Polling Hook

**Signal:** Multiple hooks define `const POLL_INTERVAL_MS = <number>` and manage `setInterval` / `clearInterval` manually with `useRef`.

**Fix:** Create `hooks/usePolling.ts`:

```ts
export const POLL_INTERVALS = {
  jobStream:    2_000,
  exportStatus: 2_000,
  workflows:    5_000,
  ingestion:    5_000,
} as const;

export function usePolling({ enabled, intervalMs, onTick }: UsePollingOptions): void {
  const callbackRef = useRef(onTick);
  useEffect(() => { callbackRef.current = onTick; }, [onTick]);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => callbackRef.current(), intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs]);
}
```

Replace `setInterval(fn, 5000)` with `usePolling({ enabled: isRunning, intervalMs: POLL_INTERVALS.workflows, onTick: refetch })`. The callback ref pattern prevents stale closures.
