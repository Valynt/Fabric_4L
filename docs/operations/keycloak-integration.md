# Keycloak Integration Guide

This document explains how to configure Keycloak as the identity provider for Fabric 4L in local development and production environments.

---

## 1. Overview

Fabric 4L uses **generic OIDC** for authentication. Keycloak is the recommended default identity provider because it offers:

- Self-hosted control (no vendor lock-in)
- OIDC and SAML support
- Identity brokering (Google, Entra ID, Okta, Apple)
- Multi-realm patterns for tenant isolation
- Service accounts for M2M auth
- Token customization with realm/user attributes

The backend does **not** depend on Keycloak-specific APIs. Any OIDC-compliant provider works.

---

## 2. Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Browser   │────▶│  Keycloak   │────▶│  Fabric Layer 4 │
│  (React)    │     │  (OIDC)     │     │  (FastAPI)      │
└─────────────┘     └─────────────┘     └─────────────────┘
       │                   │                    │
       │  Authorization    │  ID Token +        │  JWT validation
       │  Code + PKCE      │  Access Token      │  via JWKS
       │                   │                    │
       └───────────────────┘                    │
                                                │
                              ┌─────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ GovernanceMiddleware
                    │ - Verify signature
                    │ - Extract tenant_id
                    │ - Enforce RBAC
                    └─────────────────┘
```

---

## 3. Local Development Setup

### 3.1 Start Keycloak via Docker Compose

Keycloak is included in `docker-compose.dev.yml`:

```bash
docker compose -f docker-compose.dev.yml up keycloak
```

Access the admin console: http://localhost:8080/admin.  
Bootstrap admin credentials come from `KC_BOOTSTRAP_ADMIN_USERNAME` and
`KC_BOOTSTRAP_ADMIN_PASSWORD` (set via environment/secret management).

### 3.2 Realm Import

The `fabric` realm is automatically imported from `infra/keycloak/fabric-realm.json` on first startup.
A fail-closed preflight (`infra/keycloak/validate-realm-seed.py`) runs before
Keycloak starts and rejects embedded client secrets, placeholder secret
literals, and non-temporary seeded passwords.

Pre-configured clients:

| Client | Type | Purpose |
|--------|------|---------|
| `fabric-frontend` | Public | Browser-based OIDC (PKCE) |
| `fabric-api` | Bearer-only | Backend API token validation |

Pre-configured users:

| User | Password policy in seed | Role | Tenant |
|------|--------------------------|------|--------|
| `admin` | temporary only (or provision at runtime) | `tenant_admin` | `demo-tenant` |
| `analyst` | temporary only (or provision at runtime) | `analyst` | `demo-tenant` |

Credential sourcing requirements:

1. **Client secrets** for confidential/service clients must be injected during runtime provisioning (secret manager, admin API job, or IaC), never committed in realm export JSON.
2. **Seed user passwords** must be temporary (`temporary: true`) when present in realm data, forcing rotation on first login.
3. **Static defaults are prohibited** (`do-not-use-in-production`, `admin/admin`, `analyst/analyst`, or any `temporary: false` password in realm seed data).

### 3.3 Backend Configuration

The Layer 4 service is already configured in `docker-compose.dev.yml`:

```yaml
environment:
  OIDC_ISSUER: http://keycloak:8080/realms/fabric
  OIDC_AUDIENCE: fabric-api
  OIDC_JWKS_URL: http://keycloak:8080/realms/fabric/protocol/openid-connect/certs
```

For local development without Docker, set these in `.env.dev`:

```bash
OIDC_ISSUER=http://localhost:8080/realms/fabric
OIDC_AUDIENCE=fabric-api
OIDC_JWKS_URL=http://localhost:8080/realms/fabric/protocol/openid-connect/certs
```

### 3.4 Frontend Configuration

The frontend uses the existing OIDC flow via `/auth/oidc/{tenant}/login`. To use Keycloak directly from the frontend (optional), configure a Keycloak adapter:

```typescript
// apps/web/src/config/keycloak.ts
export const KEYCLOAK_CONFIG = {
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'fabric',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'fabric-frontend',
};
```

> **Note:** The frontend currently uses the backend BFF pattern (`AuthClient` → `/auth/oidc/{tenant}/login`). To switch to direct Keycloak login, you would replace `authClient.initiateLogin()` with a Keycloak JS adapter. This is optional — the BFF pattern is more secure because tokens never touch the browser.

---

## 4. Production Configuration

### 4.1 Keycloak Deployment

Deploy Keycloak to your Kubernetes cluster or managed service:

```yaml
# Example: External Keycloak URL
OIDC_ISSUER=https://auth.fabric.example.com/realms/fabric
OIDC_AUDIENCE=fabric-api
OIDC_JWKS_URL=https://auth.fabric.example.com/realms/fabric/protocol/openid-connect/certs
```

### 4.2 Realm Configuration

1. Create a realm named `fabric`
2. Create clients:
   - `fabric-frontend` (public, standard flow, PKCE)
   - `fabric-api` (bearer-only)
3. Add protocol mappers for `tenant_id` and `org_id`:
   - Mapper type: `User Attribute`
   - User Attribute: `tenant_id`
   - Token Claim Name: `tenant_id`
   - Claim JSON Type: String
   - Add to ID token: ON
   - Add to access token: ON
   - Add to userinfo: ON

4. Create realm roles: `super_admin`, `tenant_admin`, `content_admin`, `analyst`, `read_only`

### 4.3 Tenant Mapping

Each user must have a `tenant_id` attribute in Keycloak. This is extracted by `GovernanceMiddleware` and used for:

- Database query scoping (RLS)
- Graph/vector query filtering
- Resource access control

Example user attribute in Keycloak:
```
tenant_id: acme-corp
org_id: acme-org-123
```

---

## 5. Identity Brokering (External IdPs)

Keycloak can broker external identity providers so users can log in with Google, Entra ID, Okta, etc.

### 5.1 Configure Google Identity Provider

1. In Keycloak admin → Identity Providers → Add provider → Google
2. Set Client ID and Client Secret from Google Cloud Console
3. Set `Default Scopes`: `openid profile email`
4. Add a mapper to copy Google claims to Keycloak attributes:
   - Mapper type: `Attribute Importer`
   - Social Profile JSON Field Path: `email`
   - User Attribute Name: `email`

### 5.2 Configure Apple Sign In

1. In Keycloak admin → Identity Providers → Add provider → Apple
2. Set Team ID, Key ID, and private key from Apple Developer Portal
3. Set Client ID (Services ID)

### 5.3 First Login / Auto-Provisioning

When a user logs in via an external IdP for the first time, Keycloak creates a local account. You can configure a **First Login Flow** to:

1. Create the user in Keycloak
2. Copy `tenant_id` from the IdP claim (if available)
3. Trigger a webhook to Fabric to create the tenant/user record

---

## 6. Service-to-Service (M2M) Authentication

For internal service communication (e.g., Layer 4 → Layer 2):

### 6.1 Client Credentials Flow

1. In Keycloak, create a confidential client (e.g., `layer4-service`)
2. Enable **Service Accounts**
3. Assign realm roles or client roles for the service

### 6.2 Token Exchange

The calling service requests a token:

```bash
curl -X POST https://auth.fabric.example.com/realms/fabric/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=layer4-service" \
  -d "client_secret=SERVICE_SECRET"
```

The returned access token includes a `service_role` claim that Fabric's middleware validates.

### 6.3 Internal Service Tokens

For simplicity in local dev, Fabric also supports `X-Tenant-ID` + `X-Service-Auth-Secret` headers for internal calls. See `GovernanceMiddleware` for details.

---

## 7. Token Claim Shape

A typical Keycloak-issued JWT for Fabric:

```json
{
  "sub": "user-admin-001",
  "email": "admin@fabric.local",
  "tenant_id": "demo-tenant",
  "org_id": "demo-org",
  "roles": ["tenant_admin"],
  "iss": "https://auth.fabric.example.com/realms/fabric",
  "aud": "fabric-api",
  "exp": 1715500000,
  "iat": 1715496400
}
```

The `GovernanceMiddleware` extracts these claims and creates a `TenantContext` that downstream layers use for authorization.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Token has expired" | Clock skew between Keycloak and API | Sync NTP on all nodes |
| "Invalid issuer" | `OIDC_ISSUER` env var mismatch | Verify issuer URL matches Keycloak realm |
| "No JWKS key found" | `OIDC_JWKS_URL` unreachable | Check network connectivity; verify URL |
| "Missing tenant_id claim" | Protocol mapper missing | Add `tenant_id` mapper to client |
| "User not found" after login | Auto-provisioning disabled | Enable `auto_provision_users` in tenant settings |

---

## 9. Security Checklist

- [ ] Keycloak admin password is strong and rotated
- [ ] Client secrets are stored in Vault/Infisical, not in code
- [ ] HTTPS is enforced in production (`sslRequired=external`)
- [ ] Brute force protection is enabled
- [ ] `tenant_id` claim is present on all tokens
- [ ] Dev auth bypass (`DEV_AUTH_BYPASS`) is disabled in production
- [ ] Service account tokens have minimal scopes
- [ ] Keycloak events are logged to centralized audit system
