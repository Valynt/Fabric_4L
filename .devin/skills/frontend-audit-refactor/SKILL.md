---
skill_id: frontend-audit-refactor
name: frontend-audit-refactor
version: 1.0.0
description: Audit a React/TypeScript frontend codebase and its backend API connections, then apply iterative refactoring loops to remove dead code and improve code efficiency and runtime performance. Use when asked to audit a frontend, review backend connections, find and remove stale code, or run refactoring loops on a React/Vite/TypeScript project.
side_effects: write
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Frontend Audit & Iterative Refactor Skill

This skill encodes the full process for auditing a React/TypeScript frontend and its backend connections, then applying targeted refactoring loops to improve efficiency and performance.

## Overview

The process runs in three phases:

1. **Audit** — Clone the repo, scan for dead code and backend connection issues, produce a written report.
2. **Backend Connection Audit** — Trace every API call from frontend to backend, verify URL prefixes, auth flows, SSE connections, and OpenAPI contract alignment.
3. **Refactor Loops** — Run iterative loops of 4–5 targeted refactors each, applying changes directly to the codebase.

---

## Phase 1: Frontend Audit

### 1a. Explore the project structure

```bash
find <repo>/frontend -maxdepth 3 -type f | sort
cat <repo>/frontend/package.json
cat <repo>/frontend/vite.config.ts
```

Key things to identify:
- Framework (Vite + React, Next.js, etc.)
- State management (Zustand, Redux, Jotai)
- Data fetching (React Query, SWR, raw fetch)
- Auth mechanism (OIDC, JWT, session cookies)
- Routing library (wouter, react-router)

### 1b. Run the automated scan

```bash
bash /home/ubuntu/skills/frontend-audit-refactor/scripts/scan_frontend.sh <path-to-src>
```

The script checks 10 categories. Save the output — use it to prioritize refactors.

### 1c. Manual audit areas

Beyond the script, manually inspect:
- **Component architecture:** Are there "God Components" (>400 lines) doing data fetching, business logic, and rendering?
- **Store usage:** Are Zustand/Redux stores used consistently, or do some pages bypass them with local state?
- **Error boundaries:** Is there a global `<ErrorBoundary>` wrapping the router? Are individual pages protected?
- **i18n:** Are there hardcoded strings that should be in translation files?
- **Test coverage:** Run `find src/ -name "*.test.*" | wc -l` vs `find src/pages src/hooks -name "*.ts" -o -name "*.tsx" | wc -l`.

### 1d. Produce the audit report

Write a Markdown report covering:
- Executive summary
- Architecture overview (component tree, data flow)
- Dead code inventory
- Backend connection issues (see Phase 2)
- Security findings
- Prioritized recommendations

---

## Phase 2: Backend Connection Audit

Read `references/backend-connection-audit.md` for the full checklist.

Key steps:
1. Locate the API client (`api/client.ts`) and verify all layer prefixes.
2. Compare frontend URL prefixes against backend `APIRouter(prefix=...)` values.
3. Trace the auth flow end-to-end (login → callback → token → refresh → logout).
4. Verify SSE endpoints match backend routes and have proper cleanup.
5. If OpenAPI specs exist, diff frontend calls against the spec paths.
6. Check all `VITE_` env vars are documented.

A `/v1` prefix mismatch between frontend and backend means every call to that layer will 404 in production — this is the most common critical finding.

---

## Phase 3: Refactor Loops

Each loop identifies and applies 4–5 targeted refactors. Run as many loops as needed until the scan produces no new findings.

### Loop workflow

1. Run `scan_frontend.sh` and review all flagged items.
2. Rank by impact: security > bundle size > runtime performance > maintainability.
3. Apply each refactor in order. For each:
   - Read the relevant pattern in `references/refactor-patterns.md`.
   - Apply the change.
   - Verify the file compiles (check for TypeScript errors with `tsc --noEmit`).
4. Write a summary of changes.
5. Re-run the scan to confirm findings are resolved.

### Refactor priority order

**Security (always first):**
- RouteGuard fail-open (Pattern 8) — unauthenticated users can access protected routes.

**Bundle size:**
- Route-level code splitting with `React.lazy` (Pattern 7) — largest single-loop win.
- Dev-only bundle gating for devtools (Pattern 6).

**Runtime performance:**
- Memoize layout components with `React.memo` (AppShell, TieredNav).
- Memoize expensive computations with `useMemo` (nav item filtering, tier derivation).

**Maintainability:**
- Centralize query key factories (Pattern 3).
- Centralize API layer config (Pattern 5).
- Centralize polling intervals (Pattern 9).
- Extract shared QueryState component (Pattern 4).
- Remove dead stores and exports (Patterns 1 & 2).

### Deciding what to refactor in each loop

Select 4–5 items from the scan output that form a coherent theme (e.g., "all configuration centralization" or "all performance memoization"). Avoid mixing unrelated concerns in a single loop — it makes the summary harder to review.

### Patterns reference

See `references/refactor-patterns.md` for implementation details on all nine patterns, including code examples.

---

## Sitemap Generation

To generate a visual sitemap of the routing tree:

1. Read `App.tsx` (or the routing file) and extract all `<Route path="..." component={...}>` entries.
2. Group routes by section (top-level path segment).
3. Note the `requiredTier` prop on each `RouteGuard` wrapper.
4. Render using D2 or matplotlib — see the D2 approach:

```bash
manus-render-diagram sitemap.d2 sitemap.png
```

D2 node syntax for tier colour-coding:
```d2
"/dashboard": { style.fill: "#dbeafe" }  # standard = blue
"/model":     { style.fill: "#ede9fe" }  # advanced = violet
"/admin":     { style.fill: "#fef3c7" }  # admin = amber
```

---

## Deliverables

Each phase should produce a Markdown document:
- `Frontend_Audit_Report.md` — Phase 1 + 2 findings.
- `Refactor_Loop_N_Summary.md` — One per loop, listing each refactor, what changed, and why.
- `Sitemap.md` + `sitemap.png` — If a sitemap was requested.
