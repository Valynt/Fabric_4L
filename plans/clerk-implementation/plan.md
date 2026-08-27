# Clerk Implementation — Complete & Verify

**Branch:** `feat/clerk-implementation`
**Description:** Close the remaining gaps in the existing Clerk auth integration (org/tenant provisioning, webhooks, env alignment) and verify the full frontend → gateway → layer auth chain end-to-end.

## Goal
The repo already has the Clerk integration largely wired (frontend `@clerk/react` + gateway JWT verification + internal auth envelope + tenant resolution). This plan completes the remaining gaps — org/tenant provisioning, user provisioning, webhook handling, environment alignment — and proves the whole chain works with behavior tests and validation, so the integration is production-ready rather than "wired but unproven."

## Implementation Steps

### Step 1: Baseline & contract audit
**Files:** `.env.example`, `packages/platform-contract/src/clerk_defaults.json`, `services/api/app/core/clerk_config.py`, `apps/web/src/auth/clerkConfig.ts`
**What:** Lock the current state. Confirm which env vars are set vs documented, capture the exact set of Clerk env vars matched between frontend, gateway, and platform-contract defaults. Establish the source-of-truth config and note drift (e.g., `CLERK_JWT_TEMPLATE=valuepact-api` in env vs `fabric4l-api` in platform-contract; `CLERK_WEBHOOK_SECRET` naming vs canonical `CLERK_WEBHOOK_SIGNING_SECRET`).
**Testing:** `pnpm run check:contract-compliance`; targeted config unit tests.

**Step 1 audit - baseline findings (recorded, no source changes):**
- **JWT template drift confirmed:** `.env.example`/`.env.dev.example` set `VITE_CLERK_JWT_TEMPLATE=valuepact-api` while `packages/platform-contract/src/clerk_defaults.json` (source of truth) declares `jwtTemplate:"fabric4l-api"` and `jwtAudience:"fabric4l-api"`. Drift in `.env.example`, `.env.dev.example`, and `docs/auth/clerk-configuration.md`. Fix at Step 2.
- **Webhook secret naming drift:** `CLERK_WEBHOOK_SECRET` is used in 34 sites (runtime `clerk_config.py`, webhook router, replay script, compose files, k8s external-secrets, CI/env allowlist, security tests, docs). Canonical is `CLERK_WEBHOOK_SIGNING_SECRET`. Renamed atomically at Step 2.
- **Webhook route is internal, not `/v1`:** the existing route is mounted at `/internal/webhooks/clerk` (`services/api/app/main.py` mounts `clerk_webhooks.router` with prefix `/internal/webhooks`), declared intentional + network-policy protected, returns 503 when secret unset. Step 3 hardens this route; it is **not** a public `/v1` route. Plan text updated to match reality.
- **Svix verification already implemented manually** (HMAC-SHA256 over `"{svix_id}.{svix_timestamp}.{body}"`, base64 `whsec_` decode, ±300s skew, missing/non-v1 → 401). Step 3 rationalizes this (dedicated verify path) and adds the missing hostile raw-body tests, without depending on the `svix` package (keeps the package optional — already handled).
- **Idempotency/replay baseline:** `AuthDirectory._processed_events` set dedupes by `svix-id`; replay script already preserves original event IDs (AC#3 satisfied); ordering gaps return 409 (Clerk retried); DOS-like catch-all lands in DLQ. Pending-event lifecycle (AC#4) and rate-limit-vs-retry (AC#6) are built at Step 4.

### Step 2: Environment/JWT alignment — authoritative token contract
**Files:** `.env.example`, `packages/platform-contract/src/clerk_defaults.json`, `apps/web/src/auth/clerkConfig.ts`, `services/api/app/core/clerk_config.py`, `apps/web/src/auth/clerkSession.ts`
**What:** Establish one authoritative token contract before building provisioning tests. Pin, in platform-contract as source of truth: issuer (`CLERK_ISSUER`), audience (`CLERK_JWT_AUDIENCE`), the organization/tenant claim used by the gateway, JWKS URL vs pinned PEM (`CLERK_PINNED_JWT_PEM`), the frontend JWT-template name, and authorized parties. Reconcile the `valuepact-api` vs `fabric4l-api` template drift so frontend, gateway, and platform-contract agree. Rename the webhook secret to the canonical `CLERK_WEBHOOK_SIGNING_SECRET` repo-wide — env files, `services/api/app/core/clerk_config.py`, webhook router, `scripts/replay_clerk_webhooks.py`, CI/compose checks, docs, and security tests — since this is the canonical name in current Clerk docs.
**Testing:** Contract/config drift check; typecheck; `pnpm check:api-types`; grep-assert no residual `CLERK_WEBHOOK_SECRET`.

### Step 3: Webhook transport & Svix signature verification (security boundary)
**Files:** `services/api/app/routers/clerk_webhooks.py` (exists — harden), `services/api/app/core/clerk_config.py`, `docs/contract.md`, `.env.example`
**What:** Harden the existing internal `POST /internal/webhooks/clerk` route (network-policy protected — NOT a public `/v1` route). Add a dedicated signature-verification helper implementing the Svix wire format (HMAC-SHA256 over `{svix_id}.{svix_timestamp}.{raw_body}`, base64 `whsec_` secret) against the **raw request body** and the Svix headers — never a re-serialized body. Explicitly handle/reject as specified below. This step is the independently-reviewable security boundary, separate from delivery semantics. The pinned-PEM/mock-JWKS path stays test-only (AC#8).
**Testing:** Contract tests for signature verification; hostile tests (bad/missing signature → 401, replay outside tolerance → 401, oversize → 413, malformed Svix → 400).

**Step 3 must explicitly cover:**
- Public `POST /v1/webhooks/clerk` route.
- Raw-body verification (read raw body once; verify before parsing).
- Svix `svix-id`, `svix-timestamp`, and `svix-signature` headers.
- Timestamp/replay tolerance (reject stale timestamps beyond skew window).
- Invalid or missing signature → 401 rejection.
- Payload-size limit (reject oversized bodies → 413).
- Rate limiting (`CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE`) that does **not** break legitimate Clerk automatic retries.

### Step 4: Webhook idempotency, replay, and ordering controls (delivery semantics)
**Files:** `services/api/app/core/clerk_webhook_idempotency.py` (exists, may consolidate), `scripts/replay_clerk_webhooks.py`, existing `test_clerk_webhook_idempotency.py`, migrations (`services/api/.../alembic/`)
**What:** Make delivery semantics resilient and idempotent **by webhook event ID** so a correctly signed duplicate never creates duplicate Fabric users or tenants. Partition from endpoint security: transport verification (Step 3) is separate from delivery semantics (here). Deduplicate consumed event IDs; tolerate retries, duplicates, and out-of-order `organization`, `organizationMembership`, `user.created/updated/deleted` events. Events whose dependencies aren't yet available go to a recoverable pending state and are retried, not dropped.
**Testing:** Unit tests for dedupe, out-of-order, and pending-retry; hostile test that a correctly signed duplicate does not produce duplicate Fabric rows.

**Step 4 implementation notes (committed):**
- **New `services/api/app/core/clerk_webhook_delivery.py`** owns delivery state (dedup `processed` set + `pending` lifecycle + terminal/dead), deliberately separate from the Step 3 security boundary. Removed the old `AuthDirectory._processed_events` dedup (moved here; only the router used it).
- **Pending-event lifecycle (AC#4):** events whose dependency hasn't arrived are registered pending and the handler returns non-2xx (409) so the sender retries (Svix/Clerk retry every non-2xx). Bounds: `MAX_PENDING_ATTEMPTS=20` or `MAX_PENDING_AGE_SECONDS=86400` (24h). On exhaustion the event is terminal and dead-lettered exactly once (`DLQ_REASON_PENDING_EXHAUSTED`) for operator recovery + observability (`pending_retry`/`pending_dead` telemetry). Operator recovery = `scripts/replay_clerk_webhooks.py`, which preserves the original event id (AC#3), so a replayed/dead event re-enters the same dedup path and can recover if the dependency has since arrived (dead events are *not* hard-blocked).
- **Rate limiting vs retries (AC#6):** the 429 from `IPRateLimitDependency` is a transient non-2xx; Svix/Clerk retry it, and the handler never commits, applies, or dead-letters a rate-limited event. Verified by test.
- **IDEMPOTENT delivery.** Dedup by `svix-id` even when the body differs; role-change membership events update, never duplicate.
- **Pre-existing fix (same file):** `auth_directory.py` used an undefined `logger` in its Redis session-revocation path (CI-ruff F821, would have blocked this commit); added a module logger. Unrelated but unblocking.

Step 4 tests (`services/api/app/tests/test_clerk_webhook_delivery.py`, 8 cases): duplicate id no-duplicate-rows, dedup by id not body, out-of-order recovery, role-update-not-duplicate, attempt-bound dead-letter-once, age-bound terminal, 429 transient/not-dropped, snapshot observability.

### Step 5: Organization/tenant & user provisioning
**Files:** `services/api/app/core/auth_context_builder.py`, `services/api/app/core/auth_directory.py` [confirm], `services/api/app/core/clerk_provisioner.py` (new)
**What:** Consume de-duplicated events from Step 4 de-duped store and map:
- Clerk organization ID → immutable Fabric tenant ID
- Clerk user ID → immutable Fabric user identity
- Organization membership → tenant-scoped role assignment
- **No** tenant inferred from email domain or client-supplied metadata — only verified Clerk org identity.
- Events referencing unavailable dependencies are retried or placed into a recoverable pending state.
- Deletes are **soft/deactivation** operations unless permanent deletion is explicitly required.
Ensure members are provisioned before their first API call instead of erroring with `UserNotProvisionedError`.
**Testing:** Unit tests for mapping + provisioning; membership/role assignment tests; soft-deactivation tests; pending-dependency retry tests.

**Step 5 implementation notes (committed):**
- **New `services/api/app/core/clerk_provisioner.py`** is the provisioning policy boundary: `fabric_tenant_id_for(clerk_org_id)` → deterministic immutable `"t_<org_id>"` and `fabric_user_id_for(clerk_user_id)` → stable user identity (Clerk id passthrough). `AuthDirectory` now derives ids from these helpers instead of `uuid4().hex` / raw id, so re-provisioning the same Clerk identity never changes the tenant/user id.
- **No tenant from email/metadata (AC rule):** `upsert_user` never creates a tenant; only `organization.*` events provision a tenant via `fabric_tenant_id_for`. Verified by negative test (user event with plausible email domain provisions no tenant; claims for an unprovisioned org fail closed with `TenantResolutionError`).
- **Soft deletes (AC#5):** `delete_user`/`delete_tenant`/`revoke_membership` replaced with `deactivate_user`/`deactivate_tenant`/`deactivate_membership` (retain the record, set `status="deactivated"`, deny immediately). `build_auth_context` now denies when `user.status != "active"`; `get_active_membership` already ignored non-active memberships. A `user.updated`/`org.updated` profile event preserves the deactivated status (no silent reactivation); only a fresh `user.created`/`org.created` (Clerk re-creation) reactivates, mapping back to the same immutable id.
- **Pending deps:** membership events still return non-2xx (409) until the user/org dependency arrives, using the Step 4 recoverable pending state (unchanged).

Step 5 tests (`services/api/app/tests/test_clerk_provisioning.py`, 11 cases): immutable/deterministic tenant id, stable user identity, idempotent same-identity provisioning, no-tenant-from-email, unprovisioned-org deny, org/user/membership soft-delete deny immediately, profile-update-does-not-reactivate, recreated-user active+same identity, cross-tenant membership isolation/role assignment.

### Step 6: Frontend redirect verification
**Files:** `apps/web/src/auth/clerkTenant.ts`, `apps/web/src/components/routing/RequireClerkAuth.tsx`, `apps/web/src/... route/onboarding`, `DESIGN.md`-governed components
**Goal:** Verify (not rebuild) the after-sign-up `/onboarding` flow and after-sign-in `/home` redirect wiring: org routing/slug mapping, `afterSignInUrl`/`afterSignUpUrl` endpoints against the real router, and add loading/empty/error states for auth-guard sync if missing.
**Testing:** `pnpm run test:critical-behaviors`; component tests for the auth guard.

**Step 6 implementation notes (committed):**
- **Verified** redirect wiring end-to-end: `apps/web/src/auth/clerkConfig.ts` `getClerkUrls()` returns `afterSignInUrl="/home"` + `afterSignUpUrl="/onboarding"` (via `@fabric/platform-contract/clerk-defaults`, the single source of truth). `apps/web/src/main.tsx` wires both into `ClerkProvider` (`signInUrl`/`signUpUrl`/`signInFallbackRedirectUrl`/`signUpFallbackRedirectUrl`). `apps/web/src/shell/router.tsx` defines `/home` → `ValueNarrativeHome` (requiresAuth) and `/onboarding` → `OnboardingPage` (`RequireClerkAuth requireOrganization={false}`), so `/sign-up → /onboarding` and `/sign-in → /home` resolve to real routes.
- **Fixed doc drift:** `clerkConfig.ts` docstring claimed `VITE_CLERK_AFTER_SIGN_UP_URL default: "/home"`; corrected to `/onboarding` (matches code + contract). No logic change — the wiring was already correct and covered by existing tests.
- **Verified via component tests:** ran `clerkConfig.test.ts`, `RequireClerkAuth.test.tsx`, `ClerkSignIn.test.tsx`, `SelectOrganization.test.tsx`, `router.behavior.test.tsx` — 121 tests pass (auth-guard redirects to sign-in, org-picker redirect when org required, safe redirect-target sanitization, `/home`/`/onboarding` route resolution, sign-in/up URL defaults).
- `RequireClerkAuth` already provides loading (`null` while Clerk loads), not-signed-in → sign-in redirect with preserved location, and org-picker redirect when `requireOrganization` and no active org — matches the "add loading/empty/error states if missing" goal (already present, verified, not rebuilt).

### Step 7: Security/contract validation & final gate
**Files:** `apps/web/src/api/__tests__/contract/tenant-context.contract.test.ts`, `tests/security/`, `services/api` tests
**What:** Expand contract + security tests over the whole chain against the pinned PEM + mock JWKS path (no live Clerk): invalid JWT → 401, cross-tenant org → 403, missing tenant fails closed, unprovisioned user → structured error, bad webhook signature → 401, duplicate event → no duplicate rows. Add hostile "(tenant A cannot read tenant B)" tests where missing. Run the full validation gate: frontend build, `pnpm` contract checks, `pytest tests/security tests/contract`, `make verify`.
**Testing:** `pytest tests/security tests/contract`; `pnpm run test:prod-auth-bypass`; `pnpm --dir apps/web build`; `pnpm run verify:frontend`; `make contract-tests`; report the validation matrix and residual risk.

## Locked Acceptance Criteria
These are binding and must hold for the final PR. Any decision elsewhere in the plan that contradicts them is superseded.

1. **One canonical JWT template name.** Choose exactly one template value as canonical (e.g. `fabric4l-api`); treat any other value (`valuepact-api`) strictly as migration drift, never as a supported alias or fallback.
2. **Atomic `CLERK_WEBHOOK_SIGNING_SECRET` rename.** The rename to `CLERK_WEBHOOK_SIGNING_SECRET` is atomic across runtime config, examples, CI, replay tooling, and tests. No silent fallback to `CLERK_WEBHOOK_SECRET` is retained.
3. **Preserve event IDs on replay.** `scripts/replay_clerk_webhooks.py` must preserve original webhook event IDs so replayed events exercise the same deduplication path (duplicates are correctly no-oped).
4. **Pending-event lifecycle defined.** Define retry trigger, max age/attempts, terminal state, observability, and operator recovery for events whose dependencies are unavailable.
5. **Soft-deleted users/memberships deny immediately.** Specify that soft-deleted users and memberships deny access immediately (fail closed), not lazily.
6. **Rate limiting must not drop legitimate Clerk retries.** Rate limiting is applied without turning legitimate Clerk automatic retries into permanently dropped events.
7. **Negative tests required.** Cover: altered raw bodies, missing/invalid Svix headers, stale timestamps, duplicate event IDs, cross-tenant membership changes, and out-of-order events.
8. **Pinned-PEM/mock-JWKS stays test-only.** The pinned-PEM/mock-JWKS path is test-only and fails closed if reachable in production-like environments (enforced by `ProductionSafetyValidator`).

## Decisions (confirmed with user)
- **Provisioning:** Included in this PR — org/tenant + user provisioning via Clerk webhooks (Steps 3–5).
- **Auth target for validation:** Local/pinned PEM + mock JWKS for CI (no live Clerk dependency required).
- **Onboarding:** The `/onboarding` post-sign-up flow already exists — Step 6 only wires/verifies redirects, it does not build the flow.
- **Security semantics:** Use Clerk `verifyWebhook()` / Svix; canonical secret name is `CLERK_WEBHOOK_SIGNING_SECRET`.
- **Commit granularity:** One commit per step. Webhook security (Step 3) and delivery semantics (Step 4) are separate commits so the security boundary is reviewable independently of provisioning behavior.