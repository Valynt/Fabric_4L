# NAV-CONTRACT-001: Canonical Navigation Contract Closure

> Status: **Closed** — PR 2 (Workspace Consolidation)  
> Date: 2026-05-24  
> Owner: Frontend Routing Workstream  

---

## 1. Canonical 7-Domain Navigation Structure

The left-rail navigation is governed by a single source of truth: **`NAV_SCHEMA`** (`apps/web/src/navigation/navSchema.ts`).

| # | Domain | ID | Canonical Path | Tier |
|---|---|---|---|---|
| 1 | Home | `home` | `/home` | standard |
| 2 | Accounts | `accounts` | `/t/:tenantSlug/accounts` | standard |
| 3 | Intelligence | `intelligence` | `/t/:tenantSlug/accounts/:accountId/intelligence` | standard |
| 4 | Value Studio | `studio` | `/t/:tenantSlug/accounts/:accountId/studio` | standard |
| 5 | Context Engine | `context-engine` | `/t/:tenantSlug/context` | standard |
| 6 | Deliverables | `deliverables` | `/t/:tenantSlug/accounts/:accountId/deliverables` | standard |
| 7 | Governance | `governance` | `/t/:tenantSlug/governance` | standard |
| — | Settings | `settings` | `/settings` | **admin** |

### Child tabs (workspace shells)
Intelligence and Value Studio are **collapsible parent domains** whose child tabs are rendered by workspace shells, not the left rail. Child paths use the same `:tenantSlug` / `:accountId` placeholder policy (§4).

---

## 2. Source-of-Truth Rule

All navigation consumers MUST derive from `NAV_SCHEMA` or validate against it:

| Consumer | Rule |
|---|---|
| `LeftNavigation.tsx` (desktop sidebar) | MUST filter `NAV_SCHEMA` by tier and resolve placeholders. Hardcoded item lists are prohibited. |
| `TieredNav.tsx` / `NAV_SPINE` (mobile) | MUST stay in sync with `NAV_SCHEMA` labels, paths, and tier values. Drift is a contract violation. |
| Route definitions (`shell/router.tsx`) | MUST use canonical paths matching `NAV_SCHEMA`. Legacy aliases may redirect but must not be primary. |
| E2E tests | MUST assert sidebar visibility using `NAV_SCHEMA` labels, not stale hardcoded strings. |

> **Enforcement**: `LeftNavigation` was rebuilt to consume `NAV_SCHEMA` directly with `isItemVisible()` tier filtering. The old hardcoded flat list (Signals, Opportunities, Drivers, Evidence, Scenarios, Business Case, Realization) was removed.

---

## 3. Tier Policy

### Domain-level gating
- **Standard tier** sees: Home, Accounts, Intelligence, Value Studio, Context Engine, Deliverables, Governance.
- **Advanced tier** sees: same as standard (no additional domains hidden).
- **Admin tier** sees: all domains + Settings.

### Feature-level gating (preferred model)
Advanced and admin capabilities should be gated **inside** domains, not by hiding the domain itself:

- **Value Studio domain**: standard (discoverable by all users)
- **Advanced modeling tools** (e.g., whitespace analysis, deep scenario modeling): advanced capability gates
- **Admin template/governance controls** (e.g., tenant-wide formula governance): admin capability gates

This preserves workflow discoverability while maintaining monetization and permission boundaries.

> **Rationale**: Hiding an entire domain like Value Studio from standard users breaks the progressive-disclosure UX model. Users should see the domain, understand its purpose, and encounter tier gates only when attempting advanced actions.

---

## 4. Route Placeholder Policy

All canonical workspace routes use two path parameters:

- `:tenantSlug` — resolved from `useParams()` or derived from authenticated user context
- `:accountId` — resolved from `useParams()` or `useAccountContextStore().selectedAccountId`

Sidebar items MUST resolve these placeholders before rendering `NavLink` `to` values. When parameters are absent (e.g., on `/home`), the unresolved path string is retained; the label remains visible for discovery.

Example resolved path:
```
/t/e2e-test/accounts/acc-123/intelligence/signals
```

---

## 5. Clerk-Disabled Test / Development Mode Policy

The application supports two auth providers: **legacy** (default) and **Clerk**.

When `VITE_AUTH_PROVIDER` is unset or not `"clerk"`:
- `ClerkProvider` MUST NOT wrap the app.
- Components importing `@clerk/react` hooks (`useAuth`, `useOrganization`, `useUser`) MUST be gated by `isClerkAuthEnabled()` before hook invocation.
- React Router error boundaries MUST NOT catch Clerk provider errors in legacy mode.

> **Remediation applied**: `App.tsx`, `AppHeader.tsx`, and `RequireClerkAuth.tsx` were all hardened with `isClerkAuthEnabled()` guards. `RequireClerkAuth` was restructured into a wrapper + inner component to satisfy React hook rules while avoiding unconditional Clerk hook calls.

---

## 6. Validation Evidence

| Check | Result | Evidence |
|---|---|---|
| Unit tests | ✅ 1,896 passing | `vitest run` — 157/157 files |
| E2E contract tests | ✅ 15/15 passing | `playwright test --project=contracts e2e/contracts/tier-gated-navigation.spec.ts` |
| TypeScript | ✅ Clean | `tsc --noEmit` |
| Tier-gated visibility | ✅ Verified | Standard: 7 domains visible, Settings hidden. Admin: 8 domains visible. |
| Tenant redirect | ✅ Verified | `/t/wrong-tenant/...` redirects to `/home` |
| Context Engine access | ✅ Verified | Advanced tier navigates to `/t/:tenantSlug/context/ontology/graph` without redirect |
| Settings access | ✅ Verified | Admin tier navigates to `/settings/profile` without redirect |

---

## 7. Remaining Follow-Up Tasks

These tasks are **queued, not in scope** for this closure note:

- [ ] **Drift guard test**: Add a unit test that fails if `NAV_SCHEMA` and `shell/router.tsx` route registry diverge (missing routes or path mismatches).
- [ ] **Hardcode guard test**: Add a test that fails if `LeftNavigation` reintroduces hardcoded nav item arrays instead of consuming `NAV_SCHEMA`.
- [ ] **Child-route tier test**: Add tests for advanced/admin child routes under standard parent domains (e.g., Value Studio whitespace analysis requires advanced tier).
- [ ] **Settings snapshot test**: Add a snapshot or contract test asserting Settings is admin-only across all nav render paths.
- [ ] **ADR for Value Studio tier**: Confirm the "standard domain + advanced feature gates" policy in an Architecture Decision Record.
- [ ] **Clerk guard audit**: Review all `@clerk/react` imports to ensure no unconditional hook calls remain outside `isClerkAuthEnabled()` branches.

---

## Sign-Off

- Navigation contract aligned across `NAV_SCHEMA`, `LeftNavigation`, `TieredNav`, route definitions, and E2E tests.
- Tier policy documented: domains are standard by default; feature gates live inside domains.
- Build and runtime verified in both legacy-auth and mocked-auth E2E modes.

**Closed by**: Frontend Routing Workstream (PR 2 — Workspace Consolidation)
