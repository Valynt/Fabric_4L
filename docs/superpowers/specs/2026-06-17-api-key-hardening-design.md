# API Key Hardening & Auditability — Design

> **Implementation status:** Implemented. Backend routes, service logic, middleware resolver, audit events, frontend UI, backend integration tests, and frontend tests are in place. See `docs/auth/api-keys.md` for the operator-facing lifecycle guide.

## Problem statement

The Settings → Permissions → API Keys workflow already stores secrets as HMAC-SHA256 hashes and returns the raw key only once, but several production blockers and gaps exist:

1. **API-key authentication is broken in Layer 4**: `GovernanceMiddleware` expects a single-argument resolver, but `lookup_api_key_by_hash` requires `(db, raw_key)`. All `X-API-Key` requests fail closed with a signature mismatch.
2. **API-key creation is broken**: the route queries a non-existent `tenants.tier_id` column, causing `ProgrammingError` on every `POST /v1/api-keys`.
3. **Audit events use wrong enum names**: `API_KEY_CREATE` / `API_KEY_REVOKE` instead of `API_KEY_CREATED` / `API_KEY_REVOKED`.
4. **No `api_key.used` audit event** and `last_used_at` persistence is fragile.
5. **No dedicated backend integration tests** for create/list/revoke, tenant isolation, role enforcement, expiry, or one-time reveal.
6. **Frontend tests do not specifically cover** API key create/list/reveal/copy/revoke states.

## Goals / acceptance criteria

- Raw API key returned only once at creation.
- Database stores only hashed secrets plus a short prefix.
- List endpoint never returns secrets.
- Tenant A cannot create, read, revoke, or use Tenant B keys.
- Role constraints prevent low-privilege users from creating admin-scoped keys.
- Expired and revoked keys cannot authenticate.
- `api_key.created`, `api_key.revoked`, and `api_key.used` audit events are emitted.
- Settings UI lists keys safely and supports revoke with confirmation.
- Backend and frontend tests cover the above behaviors.

## Scope

### In scope

- `services/layer4-agents/src/layer4_agents/tenants/api/routes/api_keys.py`
- `services/layer4-agents/src/layer4_agents/tenants/service.py`
- `services/layer4-agents/src/layer4_agents/api/middleware.py`
- `services/layer4-agents/src/layer4_agents/tenants/models/api_key.py`
- `packages/shared/src/value_fabric/shared/identity/middleware.py`
- `packages/shared/src/value_fabric/shared/audit/models.py`
- `apps/web/src/pages/admin/PermissionsAdmin.tsx`
- `apps/web/src/hooks/useGovernance.ts`
- New backend tests under `services/layer4-agents/tests/`
- New/updated frontend tests under `apps/web/src/pages/admin/`
- Doc update: `docs/auth/api-keys.md` or equivalent

### Out of scope

- Removing the legacy in-memory `APIKeyManager` (tracked separately as tech debt).
- Changing the hashing algorithm (keep HMAC-SHA256 with `API_KEY_HMAC_SECRET`).
- Billing/entitlement enforcement for key count limits (tier check is repaired but not expanded).

## Current data model

Table `api_keys`:

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| tenant_id | UUID | FK, RLS |
| name | String | user-facing label |
| key_hash | String(64) | HMAC-SHA256 hex, unique |
| prefix | String(16) | first 12 chars of raw key |
| role | String | `tenant_admin`, `analyst`, `content_admin`, `read_only` |
| permissions | JSONB | optional permission set |
| enabled | Boolean | acts as revoked flag |
| expires_at | DateTime | nullable |
| last_used_at | DateTime | nullable |
| created_at | DateTime | auto |
| created_by | UUID | nullable today, to be enforced |

### Proposed data-model changes

- Rename `enabled` → `revoked_at` (DateTime, nullable) to match acceptance criteria and emit a proper revocation timestamp. Keep a hybrid: add `revoked_at` and expose `is_revoked` as a computed property; continue to support `enabled=False` for backward compatibility during migration.
- Add `creator_user_id` NOT NULL going forward. Backfill existing rows with a sentinel system user or allow NULL via migration with a follow-up ticket.
- Ensure `last_used_at` updates are committed reliably.

For this focused slice, we will:
- Add `revoked_at` column and `is_revoked` property.
- Keep `enabled` for one migration cycle, treating `enabled=False` and `revoked_at IS NOT NULL` as equivalent.
- Add `creator_user_id` enforcement at the API layer; migration allows NULL and backfills where possible.

## API design

### `POST /v1/api-keys`

Request:
```json
{
  "name": "CI deployment",
  "role": "analyst",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

Response (one-time only):
```json
{
  "id": "uuid",
  "name": "CI deployment",
  "api_key": "vfak_...",
  "prefix": "vfak_abc123",
  "role": "analyst",
  "expires_at": "2026-12-31T23:59:59Z",
  "created_at": "2026-06-17T..."
}
```

Rules:
- Caller must have `tenant_admin` or `SUPER_ADMIN` for the active tenant.
- Caller cannot create a key with a role higher than their own effective role.
- `tenant_admin` cannot create `super_admin` keys (none exist).
- `analyst`/`content_admin`/`read_only` cannot create keys at all.
- Enforce tier limit via `get_tier_api_key_limit`.

### `GET /v1/api-keys`

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "CI deployment",
      "prefix": "vfak_abc123",
      "role": "analyst",
      "status": "active",
      "created_at": "...",
      "expires_at": "...",
      "last_used_at": "...",
      "revoked_at": null
    }
  ]
}
```

Rules:
- Filtered by caller's `ctx.tenant_id`.
- Never includes `key_hash` or raw secret.

### `DELETE /v1/api-keys/{key_id}`

Response: `204 No Content`

Rules:
- Caller must be `tenant_admin` or `SUPER_ADMIN` for the key's tenant.
- Idempotent: deleting an already-revoked key returns 204.
- Sets `revoked_at = now()` and `enabled = False`.
- Emits `api_key.revoked` audit event.

### Authentication path

`X-API-Key` header resolution:
- Middleware calls a wrapped resolver that opens a DB session and invokes `lookup_api_key_by_hash(db, raw_key)`.
- Resolver returns `None` if key not found, revoked, expired, or wrong tenant.
- On successful resolution, emit `api_key.used` audit event asynchronously and update `last_used_at`.
- Commit the session or use a dedicated short-lived session for the usage update.

## Security rules

### Tenant isolation

- All repository queries include `tenant_id = :tenant_id`.
- `DELETE` looks up the key by `(id, tenant_id)`; 404 if missing or cross-tenant.
- Middleware rejects a key whose `tenant_id` does not match any explicit `X-Tenant-ID` header (already enforced by governance middleware, keep it).

### Role constraints

Role hierarchy (highest to lowest):
1. `super_admin` (platform, cannot be granted via API key)
2. `tenant_admin`
3. `content_admin`
4. `analyst`
5. `read_only`

Rules:
- Only `tenant_admin` or `super_admin` may call create/revoke.
- A caller may create a key with role `<=` their own role.
- `tenant_admin` cannot escalate to a non-existent super-admin role.
- `analyst`/`read_only` calling create/revoke receives `403 Forbidden`.

### Expiry & revocation

- Expired keys: resolver returns `None`; authentication fails with 401.
- Revoked keys: resolver returns `None`; authentication fails with 401.
- UI shows status badges: `active`, `expired`, `revoked`.

## Audit events

Use existing `emit_audit_event` helper.

| Event | When | Payload |
|---|---|---|
| `api_key.created` | After successful `POST` | key_id, tenant_id, creator_user_id, role, expires_at |
| `api_key.revoked` | After successful `DELETE` | key_id, tenant_id, revoker_user_id |
| `api_key.used` | After successful auth resolution | key_id, tenant_id, request_id (best effort) |
| `api_key.expired_auth_attempt` | When resolver finds an expired key | key_id, tenant_id (optional, can be combined with logging) |

## Frontend changes

- Reuse `PermissionsAdmin` API Keys tab.
- Ensure list renders `prefix`, `role`, `created_at`, `expires_at`, `last_used_at`, status badge.
- Create flow: modal already exists; ensure one-time reveal has a Copy button and a dismiss action that clears the raw key from component state.
- Revoke flow: confirmation dialog with tenant-aware warning, then call `useRevokeApiKey`.
- Status: compute from `revoked_at` and `expires_at`.
- Add unit tests for:
  - rendering list with statuses
  - create modal → reveal → copy
  - revoke confirmation → success state
  - cross-tenant route context

## Backend tests

New file: `services/layer4-agents/tests/test_api_key_hardening.py`

Tests:
1. `test_create_api_key_returns_secret_once` — raw key in response, list does not contain it.
2. `test_create_api_key_stores_hash_not_plaintext` — DB row has `key_hash` and `prefix`, no raw secret.
3. `test_list_api_keys_filters_by_tenant` — hostile cross-tenant access returns empty/404.
4. `test_revoke_api_key_prevents_auth` — after revoke, `X-API-Key` returns 401.
5. `test_expired_api_key_cannot_authenticate` — past `expires_at` blocks auth.
6. `test_low_privilege_user_cannot_create_admin_key` — analyst gets 403.
7. `test_audit_event_emitted_on_create_and_revoke` — verify audit mock/capture.
8. `test_api_key_used_updates_last_used_and_emits_audit` — auth path smoke.

## Migration plan

1. Alembic migration:
   - Add `api_keys.revoked_at` (timestamptz, nullable).
   - Add `api_keys.creator_user_id` (UUID, nullable initially).
   - Backfill `revoked_at` from `enabled = False` rows where `revoked_at IS NULL`.
2. Code change reads both `enabled` and `revoked_at` for backward compatibility.
3. Follow-up migration (future slice) makes `creator_user_id` NOT NULL and drops `enabled`.

## Risks and follow-up work

- The legacy in-memory `APIKeyManager` still exists; removal is out of scope.
- Billing tier limits are checked but not hardened in this slice.
- `creator_user_id` backfill may leave historical rows with NULL; enforce going forward.

## Implementation order

1. Fix broken resolver wiring in Layer 4 middleware.
2. Fix broken `_get_tenant_tier` in create route.
3. Fix audit enum names.
4. Add `revoked_at` migration and model changes.
5. Harden service logic (creator, role constraint, expiry check, revoke idempotency).
6. Emit `api_key.used` and update `last_used_at` reliably.
7. Update frontend status/revoke UI.
8. Add backend and frontend tests.
9. Update API key lifecycle docs.
