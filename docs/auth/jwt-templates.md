# Clerk JWT Template & Claims Specification

This document defines the canonical JSON Web Token (JWT) claims template required by Value Fabric when validating external identity tokens issued by Clerk.

---

## 1. Overview & Architecture Boundary

Clerk acts as the external Identity Provider (IdP) for human and organization authentication in Value Fabric. 

When a user authenticates in the frontend, Clerk issues a session JWT containing both standard OIDC claims and custom organization claims. 

The API Gateway (`services/api`) validates this Clerk JWT via `ClerkVerifier` and exchanges it for a short-lived (5-minute), Ed25519-signed internal trust envelope (`AuthContext`). Downstream services (Layers 1–6) **only** accept this internal envelope, maintaining a clean trust boundary.

```
┌─────────────────┐       ┌──────────────────────┐       ┌────────────────────────┐
│  React Frontend │ ───>  │  API Gateway         │ ───>  │  Downstream Services   │
│  (Clerk SDK)    │       │  (services/api)      │       │  (Layers 1 - 6)        │
└─────────────────┘       └──────────────────────┘       └────────────────────────┘
        │                            │                               │
        │ Clerk Session JWT          │ Validates JWKS                │
        │ (Bearer <clerk_jwt>)       │ Issues Ed25519 Envelope       │ X-Fabric-Auth-Context
        └───────────────────────────>│ (AuthContext)                 │ (Ed25519 Signed)
                                     └──────────────────────────────>│
```

---

## 2. Clerk JWT Template Configuration

In the Clerk Dashboard under **JWT Templates**, create a template named `value-fabric` (or customize the default session token):

```json
{
  "sub": "{{user.id}}",
  "email": "{{user.primary_email_address}}",
  "email_verified": "{{user.primary_email_address_verified}}",
  "first_name": "{{user.first_name}}",
  "last_name": "{{user.last_name}}",
  "org_id": "{{org.id}}",
  "org_slug": "{{org.slug}}",
  "org_role": "{{org.role}}",
  "org_permissions": "{{org.permissions}}",
  "org_metadata": "{{org.public_metadata}}",
  "user_metadata": "{{user.public_metadata}}",
  "azp": "{{session.azp}}",
  "sid": "{{session.id}}"
}
```

---

## 3. Claim Definitions & Rationale

| Claim | Type | Required | Purpose & Verification Rationale |
|---|---|---|---|
| `iss` | `string` | Yes | Issuer URL matching `CLERK_ISSUER` or `https://<instance>.clerk.accounts.dev`. Gateway rejects any token whose issuer does not match configuration. |
| `sub` | `string` | Yes | Subject identifier (Clerk User ID: `user_...`). Mapped to `actor_id` and used to look up local user record in Fabric DB. |
| `aud` | `string \| list` | Optional / Configurable | Audience restriction. Validated if `CLERK_AUDIENCE` is configured on the gateway. |
| `azp` | `string` | Yes (if configured) | Authorized Party (e.g. `http://localhost:3001` or `https://app.valuepact.ai`). Prevents cross-client token injection. |
| `exp` | `int` | Yes | Expiration UNIX timestamp. Short lifespan (default 60s in Clerk). Gateway allows a ±60s clock skew leeway. |
| `nbf` / `iat` | `int` | Yes | Issued-at / Not-before timestamps. Used for revocation verification (`user_revoked_before` watermark checks). |
| `sid` | `string` | Yes | Session ID (`sess_...`). Used by gateway for targeted session revocation checks in the in-memory denylist. |
| `org_id` | `string` | Conditionally | Active Clerk Organization ID (`org_...`). Mapped 1:1 to Fabric `tenant_id`. Required for all tenant-scoped API requests. |
| `org_slug` | `string` | Optional | URL-safe workspace slug (e.g. `acme-corp`). Useful for debugging and audit logs. |
| `org_role` | `string` | Conditionally | Organization membership role (e.g. `org:admin`, `org:member`). Mapped to coarse platform role (`tenant_admin`, `tenant_member`). Fine-grained resource permissions remain in Fabric DB. |
| `org_permissions` | `list[string]` | Optional | List of Clerk Organization Permissions if configured in Clerk B2B settings. |
| `email` | `string` | Yes | User's primary email address for notifications and audit trail attribution. |
| `email_verified` | `bool` | Recommended | Must be `true` for production user activation. |

---

## 4. Tenant Mapping Strategy

Value Fabric establishes a strict 1:1 relationship between a Clerk Organization and a Fabric Tenant:

```
Clerk Organization (`org_2abc...`)  <══════>  Fabric Tenant (`tenant_id: org_2abc...`)
Clerk User (`user_2xyz...`)          <══════>  Fabric User (`user_id: user_2xyz...`)
Clerk Role `org:admin`               <══════>  Fabric Role `tenant_admin`
Clerk Role `org:member`              <══════>  Fabric Role `tenant_member`
```

### Personal Workspaces vs B2B Workspaces
Value Fabric is a B2B SaaS platform. When a user is not in an organization (`org_id` is null or omitted), requests to tenant-scoped endpoints are rejected with `403 Forbidden` (`TENANT_SELECTION_REQUIRED`), prompting the user to select or create an organization via `<FabricOrganizationSwitcher />`.

---

## 5. Security Invariants

1. **Cryptographic Signature:** Tokens must be signed by an active RSA key in Clerk's JWKS.
2. **Key Rotation Leeway:** The gateway refreshes JWKS on unfamiliar `kid`s with rate-limiting and cache fallbacks.
3. **Internal Boundary:** No downstream layer (L1–L6) ever receives or verifies raw Clerk JWTs; they only accept the short-lived Ed25519 internal envelope (`AuthContext`).
4. **Non-Bypassable Account Scoping:** While Clerk provides `org_id` (Tenant), fine-grained Account IDs (`X-Account-ID`) must be validated against Fabric DB repository relationships in `/auth/authorization-snapshot`.
