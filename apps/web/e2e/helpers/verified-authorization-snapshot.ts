/** Verified snapshot for VITE_AUTH_PROVIDER=legacy Playwright contract mode. */
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
      tenantSlug: "e2e-test",
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
