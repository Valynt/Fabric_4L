# Fabric 4L Authorization Model: Clerk Organizations & Fabric DB

> **Architecture Reference & Governance Specification**  
> Defining the trust boundary between Clerk (Identity Provider) and Fabric 4L (Application & Authorization Authority).

---

## 1. Executive Summary & Core Principle

Fabric 4L employs a **decoupled Identity and Authorization Architecture**:
- **Clerk** is the authoritative **Identity Provider (IdP)**: handles user credentials, MFA, session management, organization lifecycle, and high-level organization membership roles.
- **Fabric 4L Backend & Database** is the authoritative **Authorization & Tenant Boundary**: handles canonical tenant resolution, account scoping, dataset permissions, billing entitlements, and PostgreSQL Row-Level Security (RLS).

```mermaid
flowchart LR
    subgraph Clerk [Clerk IdP]
        U[User] --> O[Organization]
        O --> CR[Clerk Roles: org:admin / org:member]
    end

    subgraph Gateway [API Gateway / Auth Bridge]
        CR --> V[ClerkVerifier + Ed25519 Signer]
        V --> AC[Internal AuthContext]
    end

    subgraph FabricDB [Fabric 4L Authority]
        AC --> TM[Tenant Mapping]
        AC --> AS[/auth/authorization-snapshot]
        AC --> RLS[PostgreSQL RLS: SET LOCAL app.tenant_id]
        AC --> ENT[Tenant Entitlements & Account Policies]
    end
```

---

## 2. Permission Set Allocation: Clerk vs. Fabric DB

| Capability / Entity | Handled in Clerk | Handled in Fabric DB | Authority Reason |
|---|---|---|---|
| **User Authentication & MFA** | ✅ Primary Authority | ❌ No password storage | Security, compliance, passwordless & SSO integration |
| **Active Session & Tokens** | ✅ Issues RS256 JWTs | ❌ Only verifies via JWKS | Clerk session lifecycle & active device tracking |
| **Organization Lifecycle** | ✅ Org creation, invitations, slugs | 🔄 Synced via Webhooks | B2B self-service org switching & invites |
| **Organization Membership Roles** | ✅ `org:admin`, `org:member`, `org:guest` | 🔄 Normalized to Canonical Roles | Coarse-grained group assignment |
| **Canonical Role Mapping** | ❌ None | ✅ `tenant_admin`, `analyst`, `read_only` | Maps Clerk roles to Fabric authorization model |
| **Account-Level Scoping (`X-Account-ID`)**| ❌ No account concept | ✅ Primary Authority (`db.accounts`) | Fine-grained enterprise account isolation |
| **Row-Level Security (RLS)** | ❌ No DB access | ✅ Primary Authority (`SET LOCAL app.tenant_id`) | Non-bypassable kernel-level data isolation |
| **Tenant Entitlements & Tiers** | ❌ None | ✅ Primary Authority (`tenant_entitlements`) | Gating features based on subscription & usage |
| **Authorization Snapshot** | ❌ None | ✅ `/auth/authorization-snapshot` | Single non-cacheable projection authority for UI |

---

## 3. Canonical Role Mapping

Clerk organization roles are mapped strictly into Fabric canonical authorization roles in `app.core.auth_context_builder.normalize_clerk_role`:

```text
Clerk: "org:admin" | "admin"         ==>  Fabric: "tenant_admin"  (Permissions: *, tier:admin:access, tier:advanced:access, tier:standard:access)
Clerk: "org:member" | "basic_member" ==>  Fabric: "analyst"       (Permissions: account:read, intelligence:read, tier:standard:access)
Clerk: "org:guest"  | "guest_member" ==>  Fabric: "read_only"     (Permissions: account:read, tier:standard:access)
```

---

## 4. Authorization Snapshot (`/auth/authorization-snapshot`)

Frontend single-page applications (React / Vite) must **never** make access control decisions based on raw unverified Clerk claims or localStorage. 

Instead, the UI queries `GET /auth/authorization-snapshot`:
1. The request provides a verified Clerk Bearer token + optional `X-Account-ID` header.
2. The backend verifies the Clerk JWT, looks up the active tenant membership in the database/directory, and verifies that the user is authorized for the requested account.
3. Returns an atomic, non-cacheable (`Cache-Control: private, no-store`) `AuthorizationSnapshot` containing:
   - `identity`: Verified Clerk User ID, Fabric User ID, and Session Discriminator (`sid`).
   - `tenant`: Fabric Tenant ID, Clerk Org ID, Slug, Membership ID.
   - `accountScope`: Scope type (`tenant` vs `account`) and validated `accountId`.
   - `roles`: Canonical role list.
   - `permissions`: Granular permission flags.
   - `entitlements`: Active tenant feature flags.
   - `expiresAt`: Minimum of token expiration, membership validity, and snapshot TTL (max 300s).

---

## 5. Non-Bypassable Tenant Isolation

All tenant-scoped database sessions enforce isolation via PostgreSQL session variables:
```sql
SET LOCAL app.tenant_id = 'verified-tenant-id';
```
- `app.tenant_id` is set **only** from the cryptographically verified `AuthContext` (either from the Ed25519 internal envelope or verified Clerk token).
- Any attempt to override tenant context via client-supplied headers (e.g. `X-Tenant-ID`, URL parameters, or body fields) without authorized internal service tokens is rejected with `403 Forbidden`.

---

## 6. Session Revocation & Force-Logout Propagation

1. **Individual Session Revocation (`POST /auth/clerk/sessions/revoke`):**
   - Marks the specific session discriminator (`sid`) as revoked in the directory / distributed store.
   - Subsequent requests presenting JWTs with that `sid` fail with `401 Unauthorized` (`AUTH_TOKEN_INVALID`).
2. **Global Force-Logout (`POST /auth/clerk/sessions/revoke-all`):**
   - Records a `revoked_before` timestamp for the user.
   - Any token issued (`iat`) on or before that cutoff is rejected immediately.
