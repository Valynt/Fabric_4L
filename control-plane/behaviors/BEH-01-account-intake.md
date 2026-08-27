# BEH-01: Account intake & analysis launch

```yaml
id: BEH-01
name: account-intake
journey_stage: J-1            # Start or resume the case; launches J-2 analysis run
stories: [VP-01, VP-02, VP-14]
closes_gaps: [GAP-01, GAP-02]
rules: [R-2, R-6]
boundary: web -> api -> L1 -> L4
components:
  - ProspectSetupPage
  - AccountsPage
  - OnboardingFlow
  - AccountsRouter
  - AuthRouter
  - AnalysisRunLauncher
primary_gates: [AG-04, AG-05]
```

## Product

An authorized value engineer creates or resumes an account, submits business context, and gets one durable, tenant-scoped Analysis Case plus an observable L1–L4 analysis run — without the system pretending missing facts are known (VP-01, VP-02; jobs 1–2).

Correct behavior, normatively:
- Identity, tenant, and account scope come from the **backend authorization snapshot**, never from frontend claims (R-6; source-of-truth hierarchy §5.3.1). Scope uncertainty fails closed.
- Every read and write verifies tenant, permitted account scope, and parent-case ownership; tenant participates in relational uniqueness (closes GAP-01).
- Intake persists the complete intake contract and starts an observable analysis run with durable progress, retries, and partial-failure detail — not "save a few fields and navigate to Signals" (closes GAP-02).
- Resuming a case restores existing work and shows freshness, lifecycle, blockers, and the next valid action.
- All state is server-persisted, tenant-scoped, account-scoped, versioned, recoverable (R-2). Browser storage holds presentation preferences only.

## Architecture

```
 apps/web                          services/api                    layers
 ┌──────────────────────┐   HTTPS   ┌────────────────────┐
 │ ProspectSetup.tsx     │ ───────▶  │ routers/accounts.py │──▶ L1 ingestion run (durable, tenant-bound)
 │ Accounts.tsx          │           │ routers/auth.py     │──▶ L4 orchestration (observable workflow run)
 │ Onboarding.tsx        │ ◀───────  │ routers/clerk_auth  │    run id, input version, source ids,
 │ AcceptInvite.tsx      │  snapshot │ clerk_webhooks.py   │    execution tier recorded
 │ SelectOrganization.tsx│           └────────────────────┘
 └──────────────────────┘                    │
                              authorization snapshot = sole
                              authority for tenant/account scope
```

The gateway (`services/api`) is the only public ingress. The frontend bootstraps identity via Clerk; the backend derives and enforces scope. The intake command creates the Account + Analysis Case identity that every later behavior references.

## Implementation

### Verified anchors

| Path | What it is | Role in this behavior |
|---|---|---|
| `apps/web/src/pages/ProspectSetup.tsx` | Prospect/account setup page | Intake form; MUST persist full intake contract and trigger analysis launch (GAP-02) |
| `apps/web/src/pages/Accounts.tsx` | Account list page | Create/select account within permitted scope |
| `apps/web/src/pages/Onboarding.tsx` | Onboarding flow | First-run account + context capture |
| `apps/web/src/pages/AcceptInvite.tsx` | Invite acceptance | Tenant membership entry; authorization snapshot establishment |
| `apps/web/src/pages/SelectOrganization.tsx` | Org selection | Tenant selection; prior-session credentials rejected on switch |
| `apps/web/src/pages/ForbiddenPage.tsx` | Denied state page | Fail-closed render when scope is denied/expired (R-6) |
| `services/api/app/routers/accounts.py` | Accounts HTTP router | Account + case CRUD; tenant-inclusive keys and parent-ownership checks (GAP-01) |
| `services/api/app/routers/auth.py` | Auth router | Backend authorization snapshot issuance |
| `services/api/app/routers/clerk_auth.py` | Clerk auth integration | Identity bootstrap; claims are not scope authority |
| `services/api/app/routers/clerk_webhooks.py` | Clerk webhook receiver | Org/membership lifecycle events |
| `services/api/app/routers/jobs.py` | Jobs router | Observable analysis-run status, progress, retries, failure detail |
| `services/api/app/main.py` | API entry | Router composition, auth middleware, fail-closed defaults |
| `services/api/migrations/` | API DB migrations | Tenant-scoped constraints and uniqueness for account/case tables |

### Inputs / outputs
- **In**: authenticated request context; account fields + business context (intake contract); analysis-start command (one versioned contract).
- **Out**: durable Account + canonical Analysis Case ID; observable workflow run ID with input version, source IDs, tenant, account, case, execution tier; current readiness and next prerequisite.

### State transitions
- Access: `verifying -> allowed | denied | expired`; protected content renders only in `allowed`.
- Content: `loading -> empty | ready | degraded | error`; resume restores last persisted state.
- Operation: `idle -> generating -> idle | retrying`; the analysis run survives navigation and page reload (job identity exposed).

### Failure modes
- Missing, malformed, expired, or conflicting authorization → deny before business logic; render `ForbiddenPage`, preserve attempted route (R-6).
- Tenant/account mismatch on an existing case ID → denial indistinguishable from absence; no existence leak (GAP-01 hostility).
- Analysis provider/worker failure → run shows `degraded`/`failed` with partial-failure detail and retry; last good state preserved. No fabricated "complete" state.
- Duplicate intake submission → idempotent command; one case per (tenant, account) identity.

## Verification

**Tests**
- Unit: intake contract validation, idempotency keys, scope-derivation logic, denied/expired rendering.
- Contract: accounts/auth route schemas against `contracts/openapi/fabric-4l-api.json`; consumer-driven contract tests (controls under AG-03).
- Integration (container env, real PostgreSQL): tenant-inclusive uniqueness; parent-case ownership on read/write; run creation with recorded input version.
- Browser journeys (Playwright): fresh-account intake through analysis-start; resume mid-journey; denied and expired states render no protected data; keyboard-complete.

**Tenant-isolation assertions** (hostile suite, ≥ 2 seeded tenants, known foreign resources)
- Tenant B's account/case IDs confirmed to exist, then read/write attempts by Tenant A denied before data load.
- Same-ID collision and cross-ID parent-child mismatch rejected (GAP-01 hostile tests).
- Prior-session and tenant-switch credentials rejected; denial before business logic; audit event names the acting tenant without leaking foreign data.

**Release gates**
- **AG-04 security-gates** — route authentication/authorization checks, production mock-mode prohibition, role-based security journeys.
- **AG-05 tenant-isolation-and-behavior** — authorization-snapshot validation, account-scope enforcement, frontend fail-closed tests, tenant-switch rejection.
- **AG-06 production-readiness** — migration safety for tenant-scoped account/case constraints; golden-path certification entry point (GAP-12).

**Required evidence**
- EV: junit-and-json test-run evidence, candidate-SHA-bound (test-run field set: source_sha, artifact_digest, environment, counts).
- EV: Playwright HTML report + failure traces for the intake journey.
- EV: migration-safety report (fresh install, upgrade, tenant-scoped constraints) bound to the candidate.
