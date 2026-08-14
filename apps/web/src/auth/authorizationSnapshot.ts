export interface AuthorizationSnapshot {
  tenantId: string;
  tenantSlug: string;
  role: string;
  expiresAt: string;
  permissions: string[];
  entitlements: string[];
  tenantMember: true;
  accountIds: string[];
}

type EmptyGrants = { permissions: []; entitlements: [] };
export type AuthorizationResolution =
  | ({ status: "loading" } & EmptyGrants)
  | ({ status: "denied" } & EmptyGrants)
  | ({ status: "expired" } & EmptyGrants)
  | {
      status: "verified";
      snapshot: AuthorizationSnapshot;
      permissions: string[];
      entitlements: string[];
    };

export type AuthorizationDecision =
  | { status: "loading"; allowed: false }
  | { status: "allowed"; allowed: true }
  | { status: "denied"; allowed: false }
  | { status: "expired"; allowed: false };

export interface AuthorizationRequirements {
  permissions?: string[];
  entitlements?: string[];
  tenantMember?: boolean;
  accountId?: string;
}

export const loadingAuthorization: AuthorizationResolution = {
  status: "loading",
  permissions: [],
  entitlements: [],
};
export const deniedAuthorization: AuthorizationResolution = {
  status: "denied",
  permissions: [],
  entitlements: [],
};
export const expiredAuthorization: AuthorizationResolution = {
  status: "expired",
  permissions: [],
  entitlements: [],
};

function strings(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.every(item => typeof item === "string" && item.trim().length > 0)
  );
}

export function parseAuthorizationSnapshot(
  payload: unknown,
  expectedTenantSlug: string | undefined,
  now = Date.now()
): AuthorizationResolution {
  if (!payload || typeof payload !== "object") return deniedAuthorization;
  const value = payload as Record<string, unknown>;
  if (
    typeof value.tenantId !== "string" ||
    !value.tenantId.trim() ||
    typeof value.tenantSlug !== "string" ||
    !value.tenantSlug.trim() ||
    value.tenantSlug !== expectedTenantSlug ||
    typeof value.role !== "string" ||
    typeof value.expiresAt !== "string" ||
    !strings(value.permissions) ||
    !strings(value.entitlements) ||
    !strings(value.accountIds) ||
    value.tenantMember !== true
  )
    return deniedAuthorization;
  const expiresAt = Date.parse(value.expiresAt);
  if (!Number.isFinite(expiresAt)) return deniedAuthorization;
  if (expiresAt <= now) return expiredAuthorization;
  const snapshot = value as unknown as AuthorizationSnapshot;
  return {
    status: "verified",
    snapshot,
    permissions: snapshot.permissions,
    entitlements: snapshot.entitlements,
  };
}

export function decideAuthorization(
  resolution: AuthorizationResolution,
  requirements: AuthorizationRequirements,
  featureEnabled = true
): AuthorizationDecision {
  if (resolution.status === "loading")
    return { status: "loading", allowed: false };
  if (resolution.status === "expired")
    return { status: "expired", allowed: false };
  if (resolution.status !== "verified")
    return { status: "denied", allowed: false };
  const { snapshot } = resolution;
  const allowed =
    featureEnabled &&
    (requirements.tenantMember !== true || snapshot.tenantMember === true) &&
    (!requirements.accountId ||
      snapshot.accountIds.includes(requirements.accountId)) &&
    (requirements.permissions ?? []).every(permission =>
      snapshot.permissions.includes(permission)
    ) &&
    (requirements.entitlements ?? []).every(entitlement =>
      snapshot.entitlements.includes(entitlement)
    );
  return allowed
    ? { status: "allowed", allowed: true }
    : { status: "denied", allowed: false };
}
