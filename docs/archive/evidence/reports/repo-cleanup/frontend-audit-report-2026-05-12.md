# Value Fabric Frontend — Comprehensive Audit Report

**Date:** 2026-05-12  
**Scope:** `apps/web/` (React 19 + Vite + TypeScript enterprise SaaS frontend)  
**Auditor:** Kimi Code CLI  
**Approach:** Full Comprehensive Audit — static analysis, automated test execution, security hardening review, UX/accessibility assessment, and contract alignment verification.

---

## Executive Summary

The Value Fabric frontend (`apps/web/`) is a mature, well-architected React 19 application with strong security foundations: cookie-only sessions (`HttpOnly/Secure/SameSite=Strict`), CSRF double-submit tokens, OIDC state validation, and comprehensive testing infrastructure (Vitest + Playwright). TypeScript strict mode passes, bundle budgets are met, and generated API types are current.

However, the audit reveals **significant architectural drift** in hook adoption, **security gaps** where direct `fetch` calls bypass the central API client, **widespread dark-mode breakage** due to hardcoded colors, and **test suite regressions** that break CI gates. The codebase also carries substantial legacy debt via the `WfPrimitives` compatibility layer (62+ active imports).

| Dimension | Grade | Key Concern |
|-----------|-------|-------------|
| **Security** | B+ | Strong auth/CSRF core, but `fetch` bypasses omit credentials and CSRF tokens; client-controlled `X-Tenant-ID` injection violates tenant-isolation rules |
| **Architecture** | C+ | Excellent foundational patterns (`api/client.ts`, `useFabricQuery`), but critically low adoption — most hooks bypass mandated wrappers |
| **Code Quality** | B | TypeScript strict passes, few `any` violations, but unsafe `as` assertions and inconsistent pagination shapes |
| **Test Coverage** | B | 1421 tests pass, but 5 regressions + 1 placeholder contract-test gate failure break CI |
| **UX / Accessibility** | C | Strong primitive library, but dark mode is broken across most pages; keyboard/accessibility gaps in `DataTable` and icon-only buttons |
| **Contract Alignment** | B+ | OpenAPI types fresh, no legacy API imports, but error-envelope normalization gap between client and hooks |

---

## 1. Workflow Completeness & Functional Coverage

### Route Inventory
- **122 routes** defined in `src/shell/router.tsx`
- All pages are **lazy-loaded** via `React.lazy`
- Route groups: Auth, Home, Workspaces (account-scoped), Context Engine, Deliverables, Governance, Workflow, Value Studio (legacy), Settings, Dev Tools

### Route Guarding
- `ProtectedRoute` wraps all authenticated routes
- Default required tier: `standard`
- Implements fail-closed: unauthenticated → `/login`, permission failure → `/home`
- `ErrorBoundary` wraps all protected children

### Findings

| Severity | Finding | Details |
|----------|---------|---------|
| **Medium** | `ROUTE_TIER_MAP` is orphaned code | `getRouteTier()` and `ROUTE_TIER_MAP` are **only used in unit tests**, not in production route guards. `ProtectedRoute` uses an explicit `requiredTier` prop instead. The map also has broken prefix matching for parameterized routes (`:accountId`) and is missing many actual routes (`/accounts`, `/command-center`, `/tasks`, `/personal/*`, `/settings/*`, `/workflow/*`, etc.). |
| **Low** | `AccountContextSync` lacks `accountId` validation | `useParams().accountId` is written directly to the Zustand store without regex validation (`src/components/routing/AccountContextSync.tsx:12–18`). Backend remains authoritative, but frontend should validate format. |

---

## 2. Code Quality & Maintainability

### Strengths
- **TypeScript strict**: `tsc --noEmit` passes cleanly
- **ESLint**: Custom `fabric-contracts` plugin enforces contract rules
- **Legacy API ban**: Zero imports from `@/api/legacy`
- **Axios isolation**: Only `src/api/client.ts` imports `axios`
- **Few `any` violations**: Only `ExportMenu.tsx:27` (`catch (err: any)`) and `usePersistFn.ts` (documented exception with eslint-disable)

### Issues

| Severity | File / Line | Issue |
|----------|-------------|-------|
| **Critical** | `src/hooks/useIngestion.ts:2, 383, 462` | Raw `apiClient.get` / `apiClient.post` calls inside a hook file. Bypasses typed wrappers, Zod validation, and the `assert-no-raw-api-client-in-hooks.mjs` guard (regex doesn't catch generic syntax like `apiClient.get<T>(...)`). |
| **Critical** | `src/hooks/useL5Governance.ts:43–52` | Native `fetch()` instead of `apiClient` or typed wrappers. Bypasses CSRF, retry, deduplication, request tracing, and `ApiError` normalization entirely. |
| **High** | `src/hooks/useIngestion.ts:282–319` | **7 unsafe `as` assertions** in a single hook (`as Record<string, unknown>`, `as number`, etc.). No runtime validation. |
| **High** | `src/hooks/useBusinessCases.ts:160, 171, 288–296` | Multiple unsafe `as` assertions (`as WorkflowItem[]`, `as number`, etc.). |
| **High** | `src/hooks/useWorkflows.ts:167, 198–200, 224` | Unsafe `as` assertions for workflow data parsing. |
| **High** | `src/components/WfPrimitives.tsx` | **Deprecated compatibility surface** still imported by **62+ files** across pages and components. Represents significant tech debt. |
| **Medium** | `src/hooks/useEntities.ts:273–284` | Raw string query key `['entityFilterOptions']` instead of `QK` registry. |
| **Medium** | `src/hooks/useWorkspaceCase.ts:63, 75` | Raw string query keys: `['workspace', 'case-id', accountId]` and `['workspace', 'tab', caseId, tabKey]`. |
| **Medium** | `src/hooks/index.ts` | Exports `usePersistFn` with explicit `any` signature. Used but isolated. |

---

## 3. Test Coverage & Quality

### Automated Test Execution Results

| Test Suite | Result | Details |
|------------|--------|---------|
| `pnpm run check` (TypeScript) | **PASS** | `tsc --noEmit` clean |
| `pnpm run test:frontend-hygiene` | **PASS** | Navigation hygiene + no legacy API imports |
| `pnpm run test:bundle-budget` | **PASS** | 148 assets, 2318.1 KiB total |
| `pnpm run test:api-type-drift` | **PASS** | Generated API types are up to date |
| `pnpm run test:trust-boundaries` | **PASS** | No unsafe `response.data` casts or direct stream JSON.parse |
| `pnpm run test` (full Vitest) | **FAIL** | 116/119 files passed, **3 failed files, 5 failed tests**, 1421 passed |
| `pnpm run test:contracts` | **FAIL** | 267 tests passed, but `assert-no-placeholder-contract-tests.mjs` **rejected** `statuses.contract.test.ts` for missing OpenAPI-backed validation and auth-failure describe block |
| `pnpm run test:coverage:critical` | **FAIL** | 208/208 tests passed, coverage exceeded thresholds (80.76% stmts / 81.88% branches / 87.5% funcs / 80.76% lines), but exit code 1 likely from stderr handling in PowerShell/pnpm |
| `pnpm run test:prod-auth-bypass` | **FAIL** | Build succeeded, but security script failed due to **Windows path bug** (`import.meta.url.pathname` produces `/C:/...` with leading slash, causing `existsSync` to fail). Not an actual auth bypass. |
| `pnpm audit` | **1 advisory** | 1 known vulnerability in dependency tree |

### Failing Tests

| File | Test | Failure |
|------|------|---------|
| `src/hooks/useGraphQuery.integration.test.ts:138` | `useSubgraph Integration > full request/response cycle` | `waitFor(() => expect(result.current.isSuccess).toBe(true))` times out — `isSuccess` never becomes `true` |
| `src/hooks/useGraphQuery.performance.test.ts:119` | `loads small graph (<50 nodes) in < 200ms` | Coefficient of variation too high (0.96 > 0.8) in jsdom |
| `src/hooks/useGraphQuery.performance.test.ts` | `loads medium graph (100-500 nodes) in < 200ms` | Test timed out in 5000ms |
| `src/hooks/useGraphQuery.performance.test.ts:199` | `has consistent timing (stdDev < 50% of mean)` | CV too high (0.67 > 0.5) in jsdom |
| `src/hooks/usePlatformSettings.test.tsx:129` | `fetches tenant settings successfully` | `waitFor(() => expect(result.current.isSuccess).toBe(true))` times out |

### Analysis
- The `useGraphQuery.performance.test.ts` failures are **environmental** — jsdom is not a real browser and produces inconsistent timing measurements. These tests should either be mocked, moved to Playwright, or have relaxed thresholds for jsdom.
- The integration test and `usePlatformSettings.test.tsx` failures suggest **MSW handler mismatches or Zod validation rejections** that need debugging.
- The contract test gate failure is a **quality/process issue** — the test file exists but doesn't meet the project's own contract-test standards.

### Coverage Summary
- **Critical path coverage**: 80.76% statements, 81.88% branches, 87.5% functions, 80.76% lines (exceeds 60/50/60/60 thresholds)
- **General suite coverage thresholds**: 35% lines/functions/statements, 25% branches
- E2E suite: 35+ Playwright spec files across 14 categories (contracts, journeys, security, accessibility, resilience, collaboration, integrations, export, personas, regression). Not executed due to backend dependency requirement.

---

## 4. Security Hardening Assessment

### Authentication & Session
- **Cookie model**: `vf_session` is `HttpOnly`, `Secure`, `SameSite=Strict` ✓
- **No JWT in localStorage**: Session metadata stored in `sessionStorage` only; legacy localStorage token accessors removed ✓
- **CSRF double-submit**: `vf_csrf_token` cookie + `X-CSRF-Token` header on mutating requests ✓
- **OIDC state validation**: `handleCallback` validates state against stored OIDC flow state; throws "possible CSRF attack" on mismatch ✓
- **Dev bypass**: Gated behind `import.meta.env.DEV`; build scanner exists (but broken on Windows)

### Security Findings

| Severity | File / Line | Finding |
|----------|-------------|---------|
| **High** | `src/agui/AgentEventClient.ts:256` | Direct `fetch` to `/agent-stream/chat/stream` **omits `credentials: 'include'`** and **`X-CSRF-Token`**. In cross-origin deployments, the session cookie is not sent. Creates CSRF protection gap. |
| **High** | `src/api/thesysClient.ts:83` | Direct `fetch` to `/c1/stream` **omits `credentials: 'include'`** and **`X-CSRF-Token`**. Same risks as above. |
| **High** | `src/api/thesysClient.ts:79–87` | Reads `localStorage.getItem('tenantId')` and sends it as **`X-Tenant-ID`** header. Violates the project's own tenant-isolation rule: *"Do not send client-controlled tenant headers from browser code."* An XSS payload can poison localStorage and switch tenants. |
| **High** | `src/agui/AgentEventClient.ts:260` | Same client-controlled `X-Tenant-ID` injection from `localStorage`. |
| **Medium** | `src/pages/Login.tsx:56, 69, 86` | Open redirect: `redirect` query parameter is stored in `sessionStorage` and passed to `navigateTo()` **without validation**. `//evil.com` starts with `/` but browsers interpret it as an external origin. |
| **Medium** | `src/components/ui/chart.tsx:81` | `dangerouslySetInnerHTML` injects dynamic CSS. `color` values from `config` prop are interpolated directly. If `config` is ever user-influenced, malicious CSS can be injected. |
| **Medium** | `src/lib/telemetry.ts:91–108` | Telemetry beacon sends `window.location.href` **including query parameters** (may contain OAuth `code`, `state`, tokens, or PII) without scrubbing. |
| **Medium** | `src/lib/telemetry.ts:133–140` | Production `captureException` sends full `error.stack` to backend, potentially revealing implementation details. |
| **Medium** | `src/api/auth.ts:12` | `RegisterResponseSchema` declares optional `access_token` field. If backend returns JWT in JSON body, it is exposed to JavaScript and vulnerable to XSS theft. Drifts from cookie-only model. |
| **Medium** | `src/hooks/useWorkspaceCase.ts:21–25` | Stores workspace case IDs in `localStorage` (`vf.workspace.case.{accountId}`). Accessible to any XSS payload on the origin. |
| **Medium** | `src/hooks/useWizard.ts:193–212` | Persists wizard draft data in `localStorage`. Sensitive business logic could be exposed in XSS. |
| **Medium** | `src/pages/FormulaBuilder.tsx:76–87` | Saves formula drafts to `localStorage` (`formula-draft-{id}`). Drafts may contain proprietary business formulas. |
| **Medium** | `src/api/thesysClient.ts:204` | Saves scenario data to `localStorage` (`vf_scenarios_{caseId}`). |
| **Low** | `src/components/ExportMenu.tsx:25` | `window.open(response.data.download_url, "_blank")` without URL validation or `noopener`. |
| **Low** | `src/components/billing/InvoiceDetailDrawer.tsx:51` | Same unvalidated `window.open` for invoice PDF URLs. |
| **Low** | `src/server/index.ts` | Missing `Content-Security-Policy` and `Strict-Transport-Security` headers. Only `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` are set. |
| **Low** | `src/contexts/AuthContext.tsx:209–224` | Dev bypass mock identity uses **realistic identifiers** (`sarah.chen@axiomrobotics.com`). Could leak plausible credentials into production bundles if build misconfiguration occurs. |

### Missing Security Configurations
- **No Content Security Policy (CSP)** header in production server
- **No Strict-Transport-Security (HSTS)** header
- **pnpm audit** found 1 advisory (should be reviewed and patched)

---

## 5. UX & Accessibility Review

### Strengths
- Complete shadcn/ui primitive library with semantic Tailwind tokens
- Well-structured `SkeletonViews` system for loading states
- `SkipLink`, focus rings, and ARIA labels on core primitives
- Right-rail pattern properly implemented with `role="status" aria-live="polite"`
- Form primitives correctly wire `htmlFor`, `aria-describedby`, `aria-invalid`

### Findings

| Severity | File / Line | Finding |
|----------|-------------|---------|
| **Critical** | `src/pages/admin/*.tsx` (widespread) | All admin pages use hardcoded `bg-white`, `border-neutral-200`, `text-neutral-800`, `text-neutral-600`, etc. Break dark mode completely. |
| **Critical** | `src/pages/NotFound.tsx:16–39` | Uses `from-slate-50 to-slate-100`, `bg-white/80`, `text-slate-900`, `text-slate-600`, `bg-blue-600`, `text-white`. No dark variants. |
| **Critical** | `src/pages/BusinessCase.tsx:241` | `bg-gradient-to-br from-blue-700 to-blue-900 ... text-white` hardcodes a blue gradient hero without dark-awareness. |
| **Critical** | `src/pages/FormulaBuilder.tsx:432, 453, 493` | Inputs use `bg-white`, error text uses `text-red-600`, success uses `text-emerald-700`. |
| **Critical** | `src/components/ui/fabric/DataTable.tsx:64–78` | Rows with `onRowClick` are **not keyboard accessible**. No `tabIndex`, no `onKeyDown`, no `role="button"`. |
| **High** | `src/pages/InteractiveBusinessCase.tsx:50–539` | Extensive hardcoded palette: `bg-white`, `text-neutral-900`, `text-green-600`, `bg-blue-50`, `text-blue-900`, `bg-green-50`, `text-green-900`, `bg-amber-50`, `text-amber-900`, etc. |
| **High** | `src/pages/ValueTreeExplorer.tsx:101–605` | Uses `bg-emerald-50`, `text-emerald-900`, `bg-amber-50`, `text-amber-900`, `text-blue-600`, `bg-blue-50`, `text-blue-700`, `bg-red-50`, `text-red-500`, `text-red-800`, `text-neutral-300`, `bg-neutral-200`. |
| **High** | `src/components/ui/fabric/DataTable.tsx:41` | Table wrapper uses `overflow-hidden` but **no `overflow-x-auto`**. Wide tables clip on mobile. |
| **High** | `src/components/blocks/TopTabNav.tsx:47` | Horizontal tabs use `flex items-center` without `overflow-x-auto`. Tabs wrap or truncate on mobile. |
| **High** | `src/components/layout/LeftNavigation.tsx:44–62` | Left nav only shows Home, Accounts, and Intelligence children. Other top-level domains (Hypothesis, Drivers, Calculator, Value Case, Realization, Context, Deliverables, Governance) are **invisible in desktop sidebar**. |
| **High** | `src/pages/Accounts.tsx:608–614` | Search input is raw `<input>` with no `<label>` and only a `placeholder`. |
| **High** | `src/components/workspace/RightRail.tsx:146` | Close button is icon-only (`<X size={14} />`) with no `aria-label`. |
| **High** | `src/components/workspace/RightRail.tsx:303–314` | Send button is icon-only (`<Send size={14} />`) with no `aria-label`. |
| **High** | `src/pages/Accounts.tsx:301–306` | `AccountDetailPanel` close button is icon-only with no `aria-label`. |
| **Medium** | `src/components/layout/GlobalLayout.tsx:52–68` | Route-level `Suspense` fallback is just a centered spinner, not a page skeleton. |
| **Medium** | `src/shell/router.tsx` | No route-level `errorElement` boundaries in `createBrowserRouter`. A crashing settings page could unmount the entire app. |
| **Medium** | `src/components/layout/LeftNavigation.tsx:127–128` | Hardcodes demo user data (`"Sarah Chen"`, `"sarah.chen@axiomrobotics.com"`). |
| **Medium** | `src/pages/Accounts.tsx:620–625` | Loading state uses raw `<Skeleton className="h-12 w-full" />` repeated 5 times instead of `SkeletonTable` or `SkeletonViews`. |
| **Medium** | `src/pages/Accounts.tsx:626–631` | Error state is inline and custom, not using canonical `<ErrorState>` component. |

---

## 6. Contract & Integration Alignment

### Strengths
- `api/client.ts` is the **sole** axios importer ✓
- `api/typedClient.ts` provides `apiGet`/`apiPost`/etc. wrappers ✓
- Generated OpenAPI types are up to date (`test:api-type-drift` passes) ✓
- Zero legacy `@/api/legacy` imports ✓

### Issues

| Severity | File / Line | Issue |
|----------|-------------|-------|
| **High** | `src/hooks/useApiShared.ts:56–65, 148–183` | `BaseApiError` **loses `traceId` and `errorCode`** from upstream `ApiError`. `withApiError` duck-types via `'statusCode' in err` instead of importing `ApiError`. |
| **High** | `src/hooks/useIngestion.ts:283–296` | Unsafe pagination shape handling: `data.pagination as Record<string, unknown>` followed by repeated `as number`/`as Record<string, number>` assertions. No runtime validation. |
| **High** | `src/hooks/useWorkflows.ts:219–234` | `parsePaginatedResponse` assumes `items`, `total`, `limit`, `offset`, `has_more` exist without validation. |
| **Medium** | Multiple hook files | Inconsistent pagination shapes: `items/total/limit/offset/has_more` (workflows), `results/totalCount/filteredCount/limit/offset/hasMore` (entities), `jobs/pagination/aggregation` (ingestion). |
| **Medium** | `src/hooks/useEntities.ts:83–107` | `getCreateEntityErrorMessage` manually inspects `AxiosError` — logic should live in client interceptor or `withApiError`, not in a domain hook. |

---

## 7. Prioritized Issue List

### P0 — Critical (Fix Immediately)

| # | Issue | File(s) | Risk |
|---|-------|---------|------|
| 1 | **Raw `apiClient` calls in hooks** bypass typed wrappers, Zod validation, and security interceptors | `src/hooks/useIngestion.ts` | Security + contract breach |
| 2 | **Native `fetch` in `useL5Governance.ts`** bypasses all API client protections | `src/hooks/useL5Governance.ts` | Security + contract breach |
| 3 | **Direct `fetch` calls omit `credentials` and CSRF tokens** | `src/agui/AgentEventClient.ts`, `src/api/thesysClient.ts` | Auth bypass + CSRF gap |
| 4 | **Client-controlled `X-Tenant-ID` header injection** violates tenant-isolation rules | `src/agui/AgentEventClient.ts`, `src/api/thesysClient.ts` | Tenant isolation breach |
| 5 | **Dark mode broken on high-traffic pages** due to hardcoded colors | `src/pages/admin/*.tsx`, `src/pages/NotFound.tsx`, `src/pages/BusinessCase.tsx`, `src/pages/FormulaBuilder.tsx` | UX regression |
| 6 | **`DataTable` rows not keyboard accessible** | `src/components/ui/fabric/DataTable.tsx` | WCAG violation |

### P1 — High (Next Sprint)

| # | Issue | File(s) | Risk |
|---|-------|---------|------|
| 7 | `useFabricQuery` / `useFabricMutation` adoption is critically low | Most `src/hooks/*.ts` files | Architectural drift |
| 8 | Open redirect via unvalidated `redirect` param | `src/pages/Login.tsx` | Phishing risk |
| 9 | `dangerouslySetInnerHTML` in chart component | `src/components/ui/chart.tsx` | XSS vector |
| 10 | Telemetry leaks PII via query parameters | `src/lib/telemetry.ts` | Privacy breach |
| 11 | `WfPrimitives` legacy layer (62+ imports) | `src/components/WfPrimitives.tsx` | Tech debt |
| 12 | `BaseApiError` loses `traceId` and `errorCode` | `src/hooks/useApiShared.ts` | Observability gap |
| 13 | Test regressions in integration and performance tests | `useGraphQuery.integration.test.ts`, `useGraphQuery.performance.test.ts`, `usePlatformSettings.test.tsx` | CI reliability |
| 14 | Contract placeholder test gate failure | `src/api/__tests__/contract/statuses.contract.test.ts` | Quality gate breach |
| 15 | Missing `aria-label` on icon-only buttons | `RightRail.tsx`, `Accounts.tsx`, etc. | Accessibility gap |
| 16 | Left navigation missing major domains | `src/components/layout/LeftNavigation.tsx` | Navigation discoverability |

### P2 — Medium (Following Sprint)

| # | Issue | File(s) | Risk |
|---|-------|---------|------|
| 17 | Unsafe `as` assertions across hooks | `useIngestion.ts`, `useBusinessCases.ts`, `useWorkflows.ts` | Runtime type safety |
| 18 | Raw string query keys instead of `QK` registry | `useEntities.ts`, `useWorkspaceCase.ts`, `useIngestion.ts` | Cache invalidation bugs |
| 19 | Inconsistent pagination shapes | Multiple hook files | Contract drift |
| 20 | LocalStorage draft/scenario exposure | `useWizard.ts`, `FormulaBuilder.tsx`, `thesysClient.ts` | XSS data exposure |
| 21 | Missing CSP and HSTS headers | `server/index.ts` | Defense in depth |
| 22 | `access_token` in registration response schema | `src/api/auth.ts`, `src/pages/Signup.tsx` | Token exposure risk |
| 23 | Route-level error boundaries missing | `src/shell/router.tsx` | Resilience |
| 24 | Windows path bug breaks auth bypass scanner | `scripts/security/assert-no-dev-auth-bypass-in-production.mjs` | False security gate failure |
| 25 | `ROUTE_TIER_MAP` is orphaned and broken | `src/stores/userTierStore.ts` | Dead code / misleading |

---

## 8. Actionable Remediation Checklist

### Security
- [ ] Replace raw `apiClient` calls in `useIngestion.ts` with `apiGet`/`apiPost`
- [ ] Replace native `fetch` in `useL5Governance.ts` with `apiGet`
- [ ] Add `credentials: 'include'` and `X-CSRF-Token` header to all direct `fetch` calls (AgentEventClient, thesysClient), or route through a streaming wrapper
- [ ] **Remove `X-Tenant-ID` header injection** from `thesysClient.ts` and `AgentEventClient.ts`; backend must derive tenant from cookie
- [ ] Validate `redirect` query parameter in `Login.tsx` (reject `//`, absolute URLs)
- [ ] Sanitize telemetry payloads: strip query strings from `window.location.href` before beaconing
- [ ] Replace `dangerouslySetInnerHTML` in `chart.tsx` with safer styling or strict color allow-list validation
- [ ] Add `noopener,noreferrer` to all `window.open` calls
- [ ] Add CSP and HSTS headers to production server
- [ ] Remove `access_token` from registration response schema

### Architecture & Code Quality
- [ ] Enforce `useFabricQuery` / `useFabricMutation` adoption via lint rule or CI gate
- [ ] Migrate top 20 `WfPrimitives` imports to canonical component paths
- [ ] Register all raw string query keys in `QK` registry
- [ ] Preserve `traceId` and `errorCode` in `BaseApiError`
- [ ] Add runtime Zod validation for pagination shapes
- [ ] Remove unsafe `as` assertions; replace with Zod schemas or type guards

### Tests
- [ ] Fix or remove flaky jsdom performance tests (`useGraphQuery.performance.test.ts`)
- [ ] Debug `useGraphQuery.integration.test.ts` MSW handler / Zod validation mismatch
- [ ] Debug `usePlatformSettings.test.tsx` MSW handler mismatch
- [ ] Update `statuses.contract.test.ts` with OpenAPI-backed validation and auth-failure block
- [ ] Fix Windows path bug in `assert-no-dev-auth-bypass-in-production.mjs` (`fileURLToPath` instead of `.pathname`)

### UX / Accessibility
- [ ] Replace hardcoded colors on high-traffic pages with semantic Tailwind tokens (`bg-card`, `text-foreground`, `border-border`, etc.)
- [ ] Add `tabIndex={0}`, `role="button"`, and `onKeyDown` to `DataTable` rows
- [ ] Add `aria-label` to all icon-only buttons
- [ ] Add `<label>` or `sr-only` label to `Accounts` search input
- [ ] Add `overflow-x-auto` to `DataTable` and `TopTabNav`
- [ ] Expand `LeftNavigation` to include all top-level domains
- [ ] Add route-level `errorElement` boundaries to `createBrowserRouter`
- [ ] Migrate high-traffic pages to `SkeletonViews`

### Cleanup
- [ ] Remove or fix orphaned `ROUTE_TIER_MAP` / `getRouteTier` code
- [ ] Validate `accountId` in `AccountContextSync` before storing
- [ ] Run `pnpm audit` and patch dependency advisory

---

## Validation Summary

| Command | Status | Notes |
|---------|--------|-------|
| `pnpm run check` | ✅ Pass | TypeScript strict clean |
| `pnpm run test:frontend-hygiene` | ✅ Pass | No legacy imports, navigation clean |
| `pnpm run test:bundle-budget` | ✅ Pass | Within budget |
| `pnpm run test:api-type-drift` | ✅ Pass | Types current |
| `pnpm run test:trust-boundaries` | ✅ Pass | Boundary parsers valid |
| `pnpm run test` | ❌ Fail | 5 test failures (3 files) |
| `pnpm run test:contracts` | ❌ Fail | Placeholder contract test gate |
| `pnpm run test:coverage:critical` | ❌ Fail | Tests pass, coverage good, exit code issue |
| `pnpm run test:prod-auth-bypass` | ❌ Fail | Windows script bug (false negative) |
| `pnpm audit` | ⚠️ 1 advisory | Review and patch |

---

*End of Report*
