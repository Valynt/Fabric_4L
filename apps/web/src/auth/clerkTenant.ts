interface ClerkOrganizationLike {
  id?: string | null;
  slug?: string | null;
}

function normalized(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function getClerkTenantRouteSlug(organization: ClerkOrganizationLike | null | undefined): string | null {
  return normalized(organization?.slug) ?? normalized(organization?.id);
}

export function matchesClerkTenantRouteSlug(
  organization: ClerkOrganizationLike | null | undefined,
  tenantSlug: string | undefined,
): boolean {
  const routeTenant = normalized(tenantSlug);
  if (!routeTenant) return false;

  const orgSlug = normalized(organization?.slug);
  const orgId = normalized(organization?.id);
  return routeTenant === orgSlug || routeTenant === orgId;
}
