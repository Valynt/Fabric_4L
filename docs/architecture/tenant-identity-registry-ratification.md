# Tenant Identity Registry Ratification

> **Status:** Ratified for the v1 release program (pending owner countersignature)
> **Date:** 2026-08-10 · **Baseline SHA:** `954c255f01ecf1c9b2cc9ee880e6dcb9c04d865f`
> **Refs:** V1-DISCOVERY-000 finding D-1 · issue #1255 (V1-IDENTITY-001) ·
> `docs/architecture/source-of-truth-ratification.md` (D2) · `release/v1/launch-contract.yaml`

## Decision

**D-ID1 — Canonical internal tenant directory:** the API gateway's
Clerk-mirrored directory (`services/api`, `db=ingestion`: `tenants`, `users`,
`tenant_memberships`, `account_memberships`, `tenant_entitlements`) is the
single internal authority for tenant identity, membership, and entitlement
state. Clerk remains the external identity authority (IdP); the gateway
directory is its durable internal mirror, kept current by Svix-signed webhooks
(`clerk_webhooks.py`, idempotent).

**D-ID2 — Layer 4 registry is scoped legacy:** the Layer 4 `tenants`/`users`
tables (UUID PKs, `db=layer4_agents`) are **not** an identity authority. They
survive only as domain-local reference targets inside Layer 4's own schema
until converged. Convergence path: L4 tables become either (a) a rebuildable
projection of the canonical directory, or (b) removed with references re-pointed
to canonical directory IDs. Owner: Platform Engineering + Data Platform.
Target: before final candidate certification. No third tenant/user registry
may be introduced (enforced by review; a static guard is follow-up work).

**D-ID3 — RLS fail-closed, no GUC bypass:** tenant isolation policies fail
closed on the exact `app.tenant_id` GUC. Reserved sentinel values
(`admin`/`internal`/`system`) are never an escape hatch; privileged
maintenance uses `SET LOCAL app.tenant_id` to the explicit tenant. Guarded by
`tests/security/test_fabric_api_records_rls_policy.py`.

**D-ID4 — Migration-target ownership:** Alembic environments fail closed
without an explicit service DSN. `CHECKPOINT_DATABASE_URL` (Layer 5's
`ground_truth` database, LangGraph checkpoint storage) is never a migration
fallback. The Layer 4 checkpoint-store placement itself (checkpoints in L5's
database) is **tracked debt**: checkpoints belong in `layer4_agents`; migration
path and owner recorded in issue #1255.

## Rationale

Two divergent tenant/user registries with incompatible schemas (TEXT-PK Clerk
mirror vs UUID-PK L4 registry) and no designated authority make every
downstream tenancy claim unauditable: hostile tests can prove isolation within
one registry while identity itself is split-brain. The gateway directory is
chosen because (a) it is the Clerk-mirrored record the auth middleware already
resolves against, (b) it owns memberships and entitlements, and (c) it is the
registry the gateway — the canonical public API (D1) — enforces.

## What this document does not do

- It does not migrate data between registries (convergence is #1255 follow-up).
- It does not change Clerk integration or the IdP.
- It does not authorize weakening any RLS policy, migration gate, or tenant
  boundary check.
