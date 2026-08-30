# AC8 Evidence — p0-e2e-gate: single deterministic root cause, fixed repo-reproducibly

## Classification summary

On the exact head `c858e01222d22ebd8d490b350c177752592fef38`, PR Checks run
`#33325357235` has **exactly one failing job**: `p0-e2e-gate`
(databaseId `99294441435`). Every other job succeeded or was skipped. The gate
fails **40/41** Playwright backend-integrated tests, all from a **single
deterministic root cause**: the frontend unconditionally requests
`GET /auth/authorization-snapshot`, and the deterministic e2e backend stack does
not include `services/api` (the auth gateway), so the snapshot 404s. Under the
legacy mock-auth contract, the app treats that 404 as a deny and the
`assertClean()` audit fails the test fail-closed.

Because the defect is **repo-reproducible** (it re-produces from the repo's own
harness + compose files + env contract), AC8's "fixed if repo-reproducible" arm
applies and the fix is implemented below.

## Evidence citations

| Evidence | Value |
|---|---|
| PR Checks run | `#33325357235` on head `c858e01222d22ebd8d490b350c177752592fef38` |
| Failing job | `p0-e2e-gate`, databaseId `99294441435` |
| Playwright summary | 40 failed / 1 passed (backend-integrated project) |
| Console-error evidence | 656 total console errors = exactly 328 pairs of `GET /api/v1/auth/authorization-snapshot` 404 + paired `QueryClient`/`Query` failure logged by the frontend |
| Historical passes | 0 — full PR Checks history scan (shell 266) found no prior successful `p0-e2e-gate`; the gate has never been green. Failure is pre-existing, not a regression introduced on this head. |

## Root cause chain (code)

1. `apps/web/e2e/helpers/journey-fixture.ts` — `authedPage` (60–109) calls
   `installApiHarness(page)` (live mode), `seedAuthState`, then
   `audit.assertClean()` (92), which fail-closes on any console error.
2. `apps/web/e2e/helpers/api-harness.ts` — in live mode (`PLAYWRIGHT_BACKEND_URL`
   set) `installApiHarness` previously returned a no-op: all requests go to the
   real backend.
3. `apps/web/src/auth/AuthorizationProvider.tsx` —
   `LegacyAuthorizationProvider` (209–257) **unconditionally** calls
   `apiGet("api", "/auth/authorization-snapshot")`.
4. `infra/compose/docker-compose.e2e.yml` — the deterministic stack
   (postgres/redis/neo4j/layer1/layer4/migrate) **omits `services/api`**, the
   auth gateway that would serve the snapshot. No real gateway HTTP call can
   succeed → deterministic 404.
5. On 404 the provider returns `{status:"denied", reason:"unavailable"}` **and**
   logs a console error → `audit.assertClean()` throws → test fails.

## p0 job env contract (from `.github/workflows/pr-checks.yml`)

The gate is **"live backend + mocked auth"**: `PLAYWRIGHT_LIVE_MODE=true`,
`PLAYWRIGHT_BACKEND_URL=http://localhost:8004`, `SERVICE_AUTH_SECRET=…1234567890`,
`VITE_AUTH_PROVIDER=legacy`, `VITE_ENABLE_MOCK_AUTH=true`, `VITE_USE_MOCKS=false`,
`VITE_ENABLE_MOCK_FALLBACK=false`, `VITE_PROXY_L1_URL=:8001`,
`VITE_PROXY_L4_URL=:8004`, `VITE_PROXY_API_GATEWAY_URL=:8004`.

The app only treats the authorization snapshot as mock-auth when
`VITE_ENABLE_MOCK_AUTH==='true'`
(`src/contexts/AuthContextCompat.ts:63`:
`import.meta.env.DEV && VITE_ENABLE_MOCK_AUTH === 'true' && !clerkMode`), and the
p0 job sets exactly that. So intercepting only the snapshot is **semantically
consistent** with the gate's own declared mock-auth contract — it is not a
weakening of auth or tenant isolation.

## Fix implemented

`apps/web/e2e/helpers/api-harness.ts` — `installApiHarness`:

- Extracted `AUTH_SNAPSHOT_PATTERN` (`/.*\/(?:api\/)?v1\/auth\/authorization-snapshot.*/`)
  shared by the contract-mode `DEFAULT_MOCKS` entry and the new live-mode branch.
- Added `isLegacyMockAuthMode()` — true only when `VITE_AUTH_PROVIDER==='legacy'`
  AND `VITE_ENABLE_MOCK_AUTH==='true'`.
- In live mode, when `isLegacyMockAuthMode()`, `page.route()` the snapshot
  pattern and fulfill `verifiedLegacyAuthorizationSnapshot(new Date(), accountId)`
  where `accountId` comes from the `X-Account-ID` header (same minted snapshot
  shape used in contract mode, TTL-insensitive per-request). Teardown unroutes.
- When the gate is not legacy-mock-auth (e.g. a genuine Clerk run), behavior is
  **unchanged**: all requests still go to the real backend, exactly one request
  type is intercepted, nothing else.

This preserves the live-mode "real backend" contract for every other request and
the p0 job's own `VITE_ENABLE_MOCK_AUTH=true` semantics, and only ever applies
when the job itself declares mock auth.

## Local validation (Docker unavailable)

Docker daemon is **not running** on this machine, so the full
`docker-compose.e2e.yml` stack and the actual Playwright p0 run cannot be
re-executed locally. Executed instead:

- `git diff --check` — clean.
- `pnpm --dir apps/web run typecheck` (`tsc --noEmit`) — passed.
- `pnpm --dir apps/web run test` (vitest) — **202 files / 2078 tests passed**.

The only full validation of the gate is a fresh CI run on a head carrying this
fix; that is the residual risk and the required confirmation step.

## Recommendation / residual risk

- Repo side fixed; a fresh PR Checks run is required to confirm the gate turns
  green. No GitHub org/package/role configuration was changed (out of scope).
- Full e2e cannot be validated locally (Docker daemon down); the CI run is the
  authoritative check.
- The 1/41 passing test is a negative-path test (deep-link tenant isolation)
  tolerant of denial; it must keep passing (no behavior change for non-mock-auth).