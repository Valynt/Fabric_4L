import { MOCK_TENANT_SLUG } from "../../src/contexts/AuthContextCompat";

/**
 * Verified snapshot for VITE_AUTH_PROVIDER=legacy Playwright contract mode.
 *
 * tenantSlug must be MOCK_TENANT_SLUG ("demo"). UnifiedRouteGuard
 * hasTenantMembership compares the path slug to this value, and
 * tenantScopedPath / LegacyFlatRedirect / LegacyIntelligenceRedirect
 * all emit /t/demo/... in contract mode. A different slug fail-closes
 * every tenant- or account-scoped journey page.
 */
export function verifiedLegacyAuthorizationSnapshot(
  now = new Date(),
  accountId: string | null = null
) {
  const issued = new Date(now.getTime());
  const expires = new Date(now.getTime() + 240_000);
  return {
    schemaVersion: "1",
    source: "backend",
    identity: {
      clerkUserId: "legacy",
      fabricUserId: "legacy",
      sessionDiscriminator: "legacy",
    },
    tenant: {
      fabricTenantId: "legacy",
      clerkOrganizationId: "legacy",
      tenantSlug: MOCK_TENANT_SLUG,
      membershipId: "legacy-membership",
      membershipStatus: "active",
    },
    accountScope: accountId
      ? { scopeType: "account" as const, accountId }
      : { scopeType: "tenant" as const, accountId: null },
    roles: ["tenant_admin", "content_admin", "analyst"],
    permissions: ["*"],
    entitlements: ["billing.manage", "exports.enabled"],
    issuedAt: issued.toISOString(),
    expiresAt: expires.toISOString(),
  };
}
