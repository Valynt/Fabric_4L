/** Canonical authorization contract for GET /auth/authorization-snapshot. */
export const AUTHORIZATION_SNAPSHOT_ENDPOINT =
  "/auth/authorization-snapshot" as const;

/** Closed role vocabulary. Unknown roles invalidate the complete snapshot. */
export type AuthorizationRole =
  | "member"
  | "analyst"
  | "account_admin"
  | "tenant_admin"
  | "platform_admin";

export interface AuthorizationTenantIdentity {
  id: string;
  slug: string;
}

/** Scope is an exact identity echo, never a list of implicitly accessible accounts. */
export type AuthorizationAccountScope =
  | { kind: "tenant" }
  | { kind: "account"; accountId: string };

export interface AuthorizationEntitlement {
  key: string;
  expiresAt?: string;
}

/**
 * Backend-issued, immutable authorization facts bound to one authenticated
 * principal, session, tenant, and account scope.
 */
export interface AuthorizationSnapshot {
  principalId: string;
  sessionDiscriminator: string;
  tenant: AuthorizationTenantIdentity;
  accountScope: AuthorizationAccountScope;
  roles: AuthorizationRole[];
  permissions: string[];
  entitlements: AuthorizationEntitlement[];
  source: "backend";
  issuedAt: string;
  expiresAt: string;
}

export type AuthorizationDenialReason =
  | "unauthenticated"
  | "policy_denied"
  | "identity_mismatch"
  | "tenant_mismatch"
  | "account_mismatch"
  | "unknown_role"
  | "malformed_response"
  | "transport_failure";

/**
 * Only `verified` carries a usable snapshot. Every unresolved or unsuccessful
 * status has `snapshot: null`, making the contract fail closed by construction.
 */
export type AuthorizationResolution =
  | { status: "loading"; snapshot: null }
  | { status: "verified"; snapshot: AuthorizationSnapshot }
  | {
      status: "denied";
      snapshot: null;
      reason: AuthorizationDenialReason;
    }
  | { status: "expired"; snapshot: null; reason: "expired" };
