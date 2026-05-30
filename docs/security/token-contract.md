# JWT Token Contract

This document specifies the JWT token claims supported by Fabric 4L's identity system.

## Overview

Fabric 4L accepts JWT tokens for authentication and tenant context resolution. Tokens must be signed with the configured secret or trusted OIDC key material and must pass strict claim validation before any service treats the caller as authenticated.

## Validation Contract

All maintained services must fail closed on JWT parse or claim errors.

- Signature verification is mandatory.
- Header `alg` must match the configured algorithm for internal tokens.
- `iss` must match `JWT_ISSUER` for internal tokens or `OIDC_ISSUER` for external tokens.
- `aud` must match `JWT_AUDIENCE` for internal tokens or `OIDC_AUDIENCE` for external tokens.
- `exp` is required and enforced.
- `iat` and `nbf` are verified when present; service-local API auth requires both claims.
- Malformed compact-JWS payloads are rejected before business routing.
- Decode failures must return contract-safe 401 auth errors and must not fall through to anonymous authorization.

## Token Structure

### Header

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### Required Claims

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | UUID | User identifier (subject) |
| `tenant_id` | UUID | Tenant identifier for RLS |

**Minimum viable token:**

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "iat": 1713801600,
  "exp": 1713805200
}
```

### Extended Claims

| Claim | Type | Description | Default |
|-------|------|-------------|---------|
| `org_id` | UUID | Organization hierarchy ID | None |
| `tenant_role` | string | User's role within tenant | None |
| `isolation_tier` | string | Tenant isolation level | "shared" |
| `roles` | string[] | System-wide roles | [] |
| `scp` | string[] | OAuth-style scopes | [] |
| `impersonated_by` | UUID | Original support/admin actor when token is an impersonation token | None |
| `impersonation_session_id` | UUID | Immutable session identifier for impersonation lifecycle audit | None |
| `impersonation_reason` | string | Operator-provided justification for support impersonation | None |

**Extended token example:**

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "org_id": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
  "tenant_role": "value_consultant",
  "isolation_tier": "shared",
  "roles": ["tenant_admin"],
  "scp": ["accounts:read", "accounts:write", "kg:query"],
  "iat": 1713801600,
  "exp": 1713805200
}
```

### Service Account Claims

For programmatic access via service accounts:

| Claim | Type | Description |
|-------|------|-------------|
| `service_account_id` | UUID | Service account identifier |
| `scopes` | string[] | Granted service account scopes |
| `auth_source` | string | Always "service_account" |

**Service account token:**

```json
{
  "service_account_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tenant_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "scopes": ["ingestion:read", "extraction:write", "kg:query"],
  "auth_source": "service_account",
  "iat": 1713801600,
  "exp": 1713888000
}
```

## Claim Specifications

### `sub` (Subject)

- **Type:** UUID string
- **Required:** Yes (for user tokens)
- **Description:** Unique identifier of the authenticated user
- **Validation:** Must be valid UUID format

### `tenant_id`

- **Type:** UUID string
- **Required:** Yes
- **Description:** Tenant identifier used for RLS enforcement
- **Validation:** Must be valid UUID format
- **Effect:** Sets `app.tenant_id` in PostgreSQL session

### `org_id`

- **Type:** UUID string
- **Required:** No
- **Description:** Organization hierarchy identifier for enterprise features
- **Use Case:** Multi-org enterprises with nested tenant structures

### `tenant_role`

- **Type:** String
- **Required:** No
- **Description:** User's functional role within the tenant context
- **Examples:** `"value_consultant"`, `"data_engineer"`, `"viewer"`
- **Note:** Distinct from system `roles` array

### `isolation_tier`

- **Type:** String
- **Required:** No
- **Default:** `"shared"`
- **Values:** `"shared"`, `"schema"`, `"database"`
- **Description:** Requested tenant isolation level
- **Effect:** Determines database session routing (future implementation)

### `roles`

- **Type:** Array of strings
- **Required:** No
- **Default:** `[]`
- **Description:** System-wide roles for permission derivation
- **Values:** `"super_admin"`, `"tenant_admin"`, `"user"`, `"readonly"`, etc.
- **Effect:** Used to derive `permissions` array in RequestContext

### `scp` (Scopes)

- **Type:** Array of strings
- **Required:** No
- **Default:** `[]`
- **Description:** OAuth 2.0 style fine-grained permissions
- **Format:** `"resource:action"`
- **Examples:** `"accounts:read"`, `"kg:query"`, `"formulas:write"`

### `service_account_id`

- **Type:** UUID string
- **Required:** No (mutually exclusive with `sub`)
- **Description:** Identifies service account for programmatic access
- **Effect:** Sets `auth_source` to `"service_account"`

### `scopes`

- **Type:** Array of strings
- **Required:** No
- **Description:** Service account specific scopes
- **Note:** Preferred over `scp` for service accounts

### `auth_source`

- **Type:** String
- **Required:** No
- **Default:** `"jwt_claim"`
- **Description:** Indicates how authentication was performed
- **Values:** `"jwt_claim"`, `"service_account"`
- **Effect:** Populates `RequestContext.auth_source`

## Token Generation

### Python Example

```python
import jwt
from datetime import datetime, timedelta, UTC
from uuid import uuid4

def generate_user_token(
    jwt_secret: str,
    user_id: str,
    tenant_id: str,
    roles: list[str] = None,
    ttl_minutes: int = 60,
) -> str:
    """Generate a user JWT token for Fabric 4L."""
    now = datetime.now(UTC)

    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "org_id": None,  # Optional
        "tenant_role": "user",
        "isolation_tier": "shared",
        "roles": roles or ["user"],
        "scp": ["read"],
        "auth_source": "jwt_claim",
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }

    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def generate_service_account_token(
    jwt_secret: str,
    service_account_id: str,
    tenant_id: str,
    scopes: list[str],
    ttl_hours: int = 24,
) -> str:
    """Generate a service account JWT token."""
    now = datetime.now(UTC)

    payload = {
        "service_account_id": service_account_id,
        "tenant_id": tenant_id,
        "scopes": scopes,
        "auth_source": "service_account",
        "isolation_tier": "shared",
        "iat": now,
        "exp": now + timedelta(hours=ttl_hours),
    }

    return jwt.encode(payload, jwt_secret, algorithm="HS256")
```

### Node.js Example

```javascript
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');

function generateUserToken(jwtSecret, userId, tenantId, options = {}) {
    const now = Math.floor(Date.now() / 1000);
    const ttlSeconds = (options.ttlMinutes || 60) * 60;

    const payload = {
        sub: userId,
        tenant_id: tenantId,
        org_id: options.orgId || null,
        tenant_role: options.tenantRole || 'user',
        isolation_tier: options.isolationTier || 'shared',
        roles: options.roles || ['user'],
        scp: options.scopes || ['read'],
        auth_source: 'jwt_claim',
        iat: now,
        exp: now + ttlSeconds,
    };

    return jwt.sign(payload, jwtSecret, { algorithm: 'HS256' });
}

function generateServiceAccountToken(jwtSecret, serviceAccountId, tenantId, scopes, options = {}) {
    const now = Math.floor(Date.now() / 1000);
    const ttlSeconds = (options.ttlHours || 24) * 3600;

    const payload = {
        service_account_id: serviceAccountId,
        tenant_id: tenantId,
        scopes: scopes,
        auth_source: 'service_account',
        isolation_tier: options.isolationTier || 'shared',
        iat: now,
        exp: now + ttlSeconds,
    };

    return jwt.sign(payload, jwtSecret, { algorithm: 'HS256' });
}
```

## Validation Rules

### GovernanceMiddleware Validation

1. **Token signature** must be valid (HS256)
2. **`tenant_id`** must be valid UUID format
3. **`exp`** claim must be in the future (not expired)
4. **`isolation_tier`** must be one of: `shared`, `schema`, `database`

### RequestContext Population

```python
# From JWT payload:
context.user_id = UUID(payload["sub"]) if "sub" in payload else None
context.tenant_id = UUID(payload["tenant_id"]) if "tenant_id" in payload else None
context.org_id = UUID(payload["org_id"]) if "org_id" in payload else None
context.tenant_role = payload.get("tenant_role")
context.isolation_tier = payload.get("isolation_tier", "shared")
context.roles = payload.get("roles", [])
context.service_account_id = UUID(payload["service_account_id"]) if "service_account_id" in payload else None
context.service_account_scopes = payload.get("scopes", [])
context.auth_source = payload.get("auth_source", "jwt_claim")

# From service_account_id presence:
if context.service_account_id:
    context.auth_source = "service_account"
```

## Error Handling

### Invalid Token

```json
{
  "detail": "Invalid token",
  "status_code": 401
}
```

### Missing tenant_id

```json
{
  "detail": "Tenant context required. Include X-Tenant-ID header or valid tenant claim.",
  "status_code": 400
}
```

### Invalid isolation_tier

```json
{
  "detail": "Unknown isolation tier: invalid_tier",
  "status_code": 400
}
```

### Unimplemented Tier

```json
{
  "detail": "Schema-per-tenant isolation tier not yet implemented",
  "status_code": 501
}
```

## API Key Alternative

For service-to-service communication, API keys are also supported:

```
Authorization: ApiKey vf_xxxxxxxxxxxxxxxx
```

API keys are tied to a specific tenant and bypass JWT processing. The tenant_id is resolved from the API key record.

See `shared/identity/middleware.py` for implementation details.

## References

- [Multi-Tenancy Architecture](./multi-tenancy.md)
- `shared/identity/context.py` - RequestContext
- `shared/identity/middleware.py` - Token validation
- `services/layer4-agents/src/layer4_agents/tenants/models/` - Tenant resolution

## Migration Note (May 2026): Cookie-Based Session Transport

Frontend and OIDC auth flows now use cookie-based session transport rather than reading or writing bearer tokens from browser storage.

- Session token is issued as `vf_session` cookie with `HttpOnly`, `Secure`, and `SameSite=Strict` flags.
- CSRF uses double-submit token: backend issues `vf_csrf_token` cookie and mutating requests must send matching `X-CSRF-Token` header.
- Legacy `localStorage` accessors for access tokens are deprecated and removed from the API client request path.
