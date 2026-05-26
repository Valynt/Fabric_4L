---
title: "Configure SSO (OIDC)"
category: "how-to-guides"
audience: "intermediate"
last-reviewed: "2026-05-14"
freshness: "current"
related:
  - "../operations/keycloak-integration"
  - "../core-concepts/security-model"
  - "../explanations/adr/ADR-003-authentication-strategy"
  - "../reference/layer4-agents-api"
  - "../troubleshooting/index"
---

# Configure SSO (OIDC)

This guide walks through connecting Value Fabric to an OIDC identity provider.
Keycloak is the recommended default; any OIDC-compliant provider (Google, Okta,
Auth0, Entra ID) works without code changes.

For architecture detail and a full Keycloak deployment walkthrough, see
[Keycloak Integration Guide](../operations/keycloak-integration.md).

---

## Prerequisites

- An OIDC provider is running and reachable from the Layer 4 service.
- A tenant record exists in the database (`tenants` table).
- You have the provider's **issuer URL**, **client ID**, and **client secret**.

---

## Step 1: Configure the Identity Provider

### Keycloak (recommended)

The `fabric` realm is pre-configured in `infra/keycloak/fabric-realm.json`.
Import it on first startup or use it as a reference.

**Required protocol mappers** (already present in the realm JSON):

| Mapper name | Type | Claim name | Purpose |
|---|---|---|---|
| `tenant_id` | `oidc-usermodel-attribute-mapper` | `tenant_id` | Tenant isolation |
| `org_id` | `oidc-usermodel-attribute-mapper` | `org_id` | Organisation context |
| `roles` | `oidc-usermodel-realm-role-mapper` | `roles` | RBAC |

**Required user attributes** for each user:

```
tenant_id = <tenant UUID or slug>
org_id    = <org UUID or slug>   (optional)
```

Set these in Keycloak Admin → Users → Attributes.

**Client configuration** (`fabric-api` client):

- Flow: Authorization Code + PKCE
- Valid redirect URIs: `https://your-app.example.com/login/callback`
- `tenant_id` claim must appear in both the ID token and access token

### Other providers (Google, Okta, Auth0)

Ensure the provider issues a JWT with at minimum:

```json
{
  "sub": "<user-id>",
  "email": "<user@example.com>",
  "tenant_id": "<tenant-uuid-or-slug>",
  "iss": "<issuer-url>",
  "aud": "<client-id>",
  "exp": <unix-timestamp>
}
```

The `tenant_id` claim is required. Configure a custom claim or attribute mapper
in your provider's admin console to include it.

---

## Step 2: Configure Environment Variables

Add the following to your `.env` (copy from `.env.example`):

```bash
# OIDC issuer URL — must match the `iss` claim in tokens exactly
OIDC_ISSUER=https://auth.example.com/realms/fabric

# Audience — must match the `aud` claim in tokens
OIDC_AUDIENCE=fabric-api

# JWKS endpoint — where the backend fetches signing keys
# Option A: explicit URL (any provider)
OIDC_JWKS_URL=https://auth.example.com/realms/fabric/protocol/openid-connect/certs

# Option B: Keycloak auto-construction (used when OIDC_JWKS_URL is not set)
# The backend builds: {KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs
KEYCLOAK_URL=https://auth.example.com
KEYCLOAK_REALM=fabric
```

Only one of `OIDC_JWKS_URL` or `KEYCLOAK_URL`+`KEYCLOAK_REALM` is needed.
`OIDC_JWKS_URL` takes precedence.

**JWKS resolution order** (first match wins):

1. `OIDC_JWKS_JSON` — static JSON string (useful for testing or air-gapped envs)
2. `OIDC_JWKS_URL` — explicit URL
3. Auto-built Keycloak URL from `KEYCLOAK_URL` + `KEYCLOAK_REALM`

---

## Step 3: Configure Tenant OIDC Settings

Each tenant stores its OIDC provider config in the `settings` JSONB column of
the `tenants` table. The shape is validated by `OIDCProviderConfig`.

Minimal example:

```json
{
  "oidc": {
    "provider_name": "keycloak",
    "issuer_url": "https://auth.example.com/realms/fabric",
    "client_id": "fabric-api",
    "client_secret_ref": "OIDC_CLIENT_SECRET_KEYCLOAK",
    "scopes": ["openid", "email", "profile"],
    "auto_provision_users": false,
    "default_role": "read_only",
    "enabled": true
  }
}
```

**`client_secret_ref`** resolves in this order:

1. Vault reference: `"vault:secret/data/oidc#client_secret"`
2. Environment variable name: `"OIDC_CLIENT_SECRET_KEYCLOAK"` → reads `os.getenv("OIDC_CLIENT_SECRET_KEYCLOAK")`
3. Fallback env var: `OIDC_CLIENT_SECRET_{PROVIDER_NAME_UPPER}`

**Role mapping** (optional — maps IdP claims to VF roles):

```json
{
  "oidc": {
    "claim_mapping": {
      "roles=tenant_admin": "tenant_admin",
      "roles=analyst":      "analyst",
      "groups=/^admin.*/":  "tenant_admin"
    },
    "default_role": "read_only"
  }
}
```

Claim mapping key syntax:

| Format | Matches when |
|---|---|
| `claim_path` | Claim is truthy |
| `claim_path=value` | Exact match (case-insensitive) or array membership |
| `claim_path=/regex/` | Regex match against claim value or array elements |

Dot notation resolves nested claims: `resource_access.fabric-api.roles`.

When multiple mappings match, the **highest-privilege role** is selected.

---

## Step 4: Test the Flow

### 1. Initiate login

```bash
curl "https://your-api.example.com/agents/auth/oidc/{tenant_slug}/login?redirect_uri=https://your-app.example.com/login/callback"
```

Response:

```json
{
  "authorization_url": "https://auth.example.com/realms/fabric/protocol/openid-connect/auth?...",
  "state": "<random-state>"
}
```

Redirect the user to `authorization_url`.

### 2. Handle the callback

After the user authenticates, the IdP redirects to:

```
https://your-app.example.com/login/callback?code=<code>&state=<state>
```

The frontend calls:

```
GET /agents/auth/oidc/callback?code=<code>&state=<state>
```

On success, the backend sets the `vf_session` httpOnly cookie and returns:

```json
{
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "<uuid>",
  "email": "user@example.com",
  "role": "analyst"
}
```

### 3. Verify tenant context

Subsequent API calls include the cookie automatically. The `GovernanceMiddleware`
decodes the internal JWT from the cookie and populates `RequestContext` with
`tenant_id`, `user_id`, and `roles`.

---

## Local Development

Keycloak is included in `docker-compose.dev.yml`:

```bash
docker compose -f docker-compose.dev.yml up keycloak
```

Admin console: http://localhost:8080/admin

Credentials are set via `KC_BOOTSTRAP_ADMIN_USERNAME` and
`KC_BOOTSTRAP_ADMIN_PASSWORD` in `docker-compose.dev.yml`. Do not commit
real passwords — use `.env` overrides for local development.

The `fabric` realm is auto-imported from `infra/keycloak/fabric-realm.json`.
The committed realm file must not contain client secrets or permanent seed
passwords. Docker/dev startup runs `infra/keycloak/validate-realm-seed.py` and
fails closed if placeholder literals or embedded secrets are present.

Pre-configured test users (passwords must be provisioned at bootstrap and reset on first login):

| Username | Role | tenant_id attribute |
|---|---|---|
| `admin` | `tenant_admin` | `demo-tenant` |
| `analyst` | `analyst` | `demo-tenant` |

Local bootstrapping expectation:

- Set initial credentials through environment/secret injection (Infisical, `.env.generated`, or CI secrets), not in `infra/keycloak/fabric-realm.json`.
- If password credentials are present in seed data, they must use `temporary: true`.
- Do not commit literal passwords such as `admin`/`analyst` or placeholder secrets containing `do-not-use-in-production`.

Layer 4 is pre-wired in `docker-compose.dev.yml`:

```bash
OIDC_ISSUER=http://keycloak:8080/realms/fabric
OIDC_AUDIENCE=fabric-api
OIDC_JWKS_URL=http://keycloak:8080/realms/fabric/protocol/openid-connect/certs
```

---

## Production Hardening

- **HTTPS required**: Set `KC_HOSTNAME_STRICT_HTTPS=true` and `sslRequired=external` in the realm.
- **Client secrets in Vault**: Use `client_secret_ref: "vault:secret/data/oidc#client_secret"` — never store secrets in the `settings` JSONB column directly.
- **Key rotation**: Set `JWT_REVOKED_KIDS` to the comma-separated list of retired key IDs. The backend rejects tokens signed with revoked keys before signature verification.
- **PKCE required**: All login flows use PKCE (S256) by default. Do not disable `use_pkce` in `oidc_sessions`.
- **Session expiry**: Internal JWTs expire in 1 hour. Use `POST /auth/oidc/refresh` to rotate before expiry.
- **Brute-force protection**: Keycloak's brute-force protection is enabled in `fabric-realm.json` (5 failures → 15-minute lockout). Verify this is active in production.
- **Audit events**: All login successes, failures, and logouts emit `AuditAction.OIDC_LOGIN` / `OIDC_LOGIN_FAILED` events. Ensure your audit log pipeline is consuming these.

---

## Troubleshooting

See [Keycloak Integration — Troubleshooting](../operations/keycloak-integration.md#8-troubleshooting) for a full symptom/cause/fix table.

Common issues:

| Symptom | Likely cause |
|---|---|
| `"OIDC is not enabled for this tenant"` | Tenant `settings.oidc.enabled` is `false` or `settings.oidc` is absent |
| `"Missing tenant_id claim"` | Protocol mapper not configured in Keycloak client |
| `"Invalid or expired state parameter"` | OIDC session expired (10-minute window) or state was replayed |
| `"User not found and auto-provisioning is disabled"` | Set `auto_provision_users: true` or create the user manually |
| `"No JWKS key found for kid=..."` | `OIDC_JWKS_URL` unreachable, or key rotation not yet propagated (backend retries once) |
| `"Invalid issuer"` | `OIDC_ISSUER` env var doesn't match the `iss` claim in the token |

---

## Related

- [Keycloak Integration Guide](../operations/keycloak-integration.md) — architecture, M2M auth, identity brokering
- [ADR-004: JWT + API Key Authentication Strategy](../explanations/adr/ADR-004-jwt-api-key-authentication-strategy.md)
- [Security Model](../core-concepts/security-model.md)
- [Layer 4 Agents API Reference](../reference/layer4-agents-api.md)
- [Troubleshooting](../troubleshooting/index.md)
