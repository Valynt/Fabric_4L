# API Key Lifecycle & Security Model

## Overview

API keys are long-lived credentials used for service-to-service and automation access to the Value Fabric platform. They are scoped to a single tenant, carry a fixed role, and are governed by the same RBAC and tenant-isolation rules as interactive users.

## Security model

### Storage

- **Raw API keys are never stored.** When a key is created, the backend generates a random token and stores only:
  - `key_hash` — `HMAC-SHA256(API_KEY_HMAC_SECRET, raw_key)` as a 64-character hex digest.
  - `prefix` — the first 12 characters of the raw key, used to identify the key in the UI and logs without exposing the secret.
- The `API_KEY_HMAC_SECRET` environment variable is the server-side pepper. It must be at least 32 random characters in production and must never be committed to source control.
- Database rows contain **no plaintext secret**, **no reversible encryption**, and **no key derivation parameters**.

### One-time reveal

- The raw key is returned **exactly once** in the `api_key` field of the `POST /v1/api-keys` response.
- After creation, the raw key cannot be retrieved by any API, database query, or UI action.
- Admins must copy the key during creation. Losing the raw key requires creating a new key or rotating the existing one.

### Tenant isolation

- Every API key belongs to exactly one `tenant_id`.
- `GET /v1/api-keys` returns only keys for the caller's active tenant.
- `DELETE /v1/api-keys/{key_id}` matches on `(key_id, tenant_id)`; a caller from Tenant A receives `404 Not Found` when trying to revoke a Tenant B key.
- The `lookup_api_key_by_hash` resolver used by `GovernanceMiddleware` returns the key's `tenant_id`; the middleware rejects the request if the key's tenant does not match the request context.

### Role constraints

- Only callers with `tenant_admin` or `super_admin` role can create or revoke API keys.
- A caller may create a key with a role **strictly lower** than their own effective role:
  - `tenant_admin` can create `content_admin`, `analyst`, and `read_only` keys.
  - `content_admin` can create `analyst` and `read_only` keys.
  - `analyst` and `read_only` cannot create keys.
- `super_admin` and `system` roles cannot be granted to API keys.

### Expiry and revocation

- `expires_at` is optional. When set, the key cannot authenticate after that timestamp.
- `revoked_at` is immutable. Once set, the key cannot authenticate or be re-enabled.
- Revocation is idempotent: revoking an already-revoked key returns `204 No Content`.
- Revoked and expired keys remain visible in the UI when **Show all keys** is selected so audit history is preserved.

## API endpoints

### Create a key

```http
POST /v1/api-keys
Content-Type: application/json

{
  "name": "CI deployment",
  "role": "analyst",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

Response (`201 Created`):

```json
{
  "key_id": "vf_0191b2c3d4e5f678901234567890abcd",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "CI deployment",
  "api_key": "vf_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890",
  "prefix": "vf_aBcDeFgHiJ",
  "role": "analyst",
  "permissions": ["read:health", "read:metrics"],
  "expires_at": "2026-12-31T23:59:59Z",
  "created_at": "2026-06-17T09:00:00Z"
}
```

**Important:** store `api_key` securely. It is shown only once.

### List keys

```http
GET /v1/api-keys?active_only=true
```

Response:

```json
[
  {
    "key_id": "vf_0191b2c3d4e5f678901234567890abcd",
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "CI deployment",
    "prefix": "vf_aBcDeFgHiJ",
    "role": "analyst",
    "enabled": true,
    "created_at": "2026-06-17T09:00:00Z",
    "expires_at": "2026-12-31T23:59:59Z",
    "last_used_at": "2026-06-17T10:30:00Z"
  }
]
```

The list endpoint never returns `api_key` or `key_hash`.

### Revoke a key

```http
DELETE /v1/api-keys/vf_0191b2c3d4e5f678901234567890abcd
```

Response: `204 No Content`

## Authentication

Include the raw key in the `X-API-Key` header:

```http
GET /v1/some-resource
X-API-Key: vf_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890
```

The middleware hashes the header value and looks up the matching row. Authentication fails closed (401) if:

- the key is not found,
- the key is revoked,
- the key is expired,
- the key's tenant does not match the request context.

On a successful lookup, the backend updates `last_used_at` and emits an `api_key.used` audit event.

## Audit events

| Event | When | Payload highlights |
|---|---|---|
| `api_key.created` | After successful `POST /v1/api-keys` | `key_id`, `tenant_id`, `actor_id`, requested `role`, `expires_at` |
| `api_key.revoked` | After successful `DELETE /v1/api-keys/{key_id}` | `key_id`, `tenant_id`, `actor_id` |
| `api_key.used` | After successful `X-API-Key` authentication | `key_id`, `tenant_id`, `last_used_at` |

## Frontend workflow

Navigate to **Settings → Permissions & Access → API Keys**.

- The table lists key name, prefix, role, status, created date, expiry, and last used time.
- Status is computed as `active`, `expired`, or `revoked`.
- Click **New API Key** to open the creation modal, choose a name and role, and optionally set an expiry.
- After creation, the modal shows the raw key once with a **Copy** button. Closing the modal clears the raw key from memory.
- Click the trash icon to revoke a key. A tenant-scoped confirmation dialog appears before the action is sent.

## Rotation guidance

There is no automatic rotation endpoint in this slice. To rotate:

1. Create a new key with the same or narrower role.
2. Update the consuming service to use the new raw key.
3. Revoke the old key.

Rotate keys on any suspicion of compromise, role change, or before the expiry date.

## Environment requirements

| Variable | Purpose | Production requirement |
|---|---|---|
| `API_KEY_HMAC_SECRET` | Server-side pepper for key hashing | Required, ≥32 random characters, injected via secret manager |
| `CREDENTIALS_MASTER_KEY` | Used for encrypted columns (e.g., user email) | Required, separate from `API_KEY_HMAC_SECRET` |

## See also

- [Design spec](../superpowers/specs/2026-06-17-api-key-hardening-design.md)
- [ADR-004: JWT/API-Key authentication strategy](../explanations/adr/ADR-004-jwt-api-key-authentication-strategy.md)
- [ADR-017: JWT/API-Key hybrid authentication](../explanations/adr/ADR-017-jwt-api-key-hybrid-authentication.md)
- Backend tests: `services/layer4-agents/tests/test_api_keys_route.py`
- Frontend tests: `apps/web/src/pages/admin/AdminPages.test.tsx`
