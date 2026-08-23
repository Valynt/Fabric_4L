type ClerkOrganizationLike = {
  id?: string | null;
  slug?: string | null;
  publicMetadata?: Record<string, unknown> | null;
} | null | undefined;

function normalizeTenantSlug(value: string | null | undefined): string | null {
  const normalized = value?.trim().toLowerCase();
  return normalized ? normalized : null;
}

export function getClerkTenantRouteSlug(
  organization: ClerkOrganizationLike,
): string | null {
  if (!organization) return null;

  const metadataTenantSlug =
    typeof organization.publicMetadata?.tenantSlug === "string"
      ? organization.publicMetadata.tenantSlug
      : null;

  return (
    normalizeTenantSlug(organization.slug) ??
    normalizeTenantSlug(metadataTenantSlug) ??
    normalizeTenantSlug(organization.id)
  );
}
