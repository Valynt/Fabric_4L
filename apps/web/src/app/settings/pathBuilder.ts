/**
 * Settings route path builder.
 *
 * The settings surface supports two route families:
 *   1. Global personal/admin routes: `/personal/*` and `/settings/*`
 *   2. Tenant-scoped routes: `/t/:tenantSlug/settings/*`
 *
 * The tenant-scoped paths do not mirror the global template exactly (e.g.
 * `/settings/team` maps to `/t/:tenantSlug/settings/users`). This module
 * centralises the bidirectional mapping so the layout can compute active
 * states and links without hard-coding router internals.
 */

const GLOBAL_TO_TENANT_SUFFIX: Record<string, string> = {
  "/settings/workspace": "/settings/workspace",
  "/settings/billing": "/settings/billing",
  "/settings/team": "/settings/users",
  "/settings/data": "/settings/data-sources",
  "/settings/governance": "/settings/governance/policies",
  "/settings/billing/subscription": "/settings/billing/subscription",
  "/settings/billing/usage": "/settings/billing/usage",
  "/settings/billing/payment-methods": "/settings/billing/payment-methods",
  "/settings/billing/invoices": "/settings/billing/invoices",
  "/settings/team/invitations": "/settings/invitations",
  "/settings/team/roles": "/settings/roles",
  "/settings/team/permissions": "/settings/permissions",
  "/settings/team/api-keys": "/settings/api-keys",
  "/settings/data/sources": "/settings/data-sources",
  "/settings/data/integrations": "/settings/integrations",
  "/settings/data/variables": "/settings/variables",
  "/settings/data/value-packs": "/settings/value-packs",
  "/settings/data/ingestion-rules": "/settings/ingestion-rules",
  "/settings/governance/policies": "/settings/governance/policies",
  "/settings/governance/compliance": "/settings/governance/compliance",
  "/settings/governance/health": "/settings/governance/health",
  "/settings/governance/audit-trail": "/settings/governance/audit",
  "/settings/governance/admin-controls": "/settings/governance/admin",
};

const TENANT_SUFFIX_TO_GLOBAL: Record<string, string> = Object.fromEntries(
  Object.entries(GLOBAL_TO_TENANT_SUFFIX).map(([globalPath, tenantSuffix]) => [
    tenantSuffix,
    globalPath,
  ])
);

/**
 * Convert a canonical global settings path to its tenant-scoped equivalent.
 * Personal paths and unknown paths are returned unchanged.
 */
export function globalToTenantPath(
  path: string,
  tenantSlug: string | null
): string {
  if (!tenantSlug) return path;
  if (path.startsWith("/t/")) return path;
  const suffix = GLOBAL_TO_TENANT_SUFFIX[path];
  return suffix ? `/t/${tenantSlug}${suffix}` : path;
}

/**
 * Convert a tenant-scoped pathname back to its canonical global equivalent.
 * Used for active-state detection against the global route schema.
 */
export function tenantToGlobalPath(pathname: string): string {
  const match = pathname.match(/^\/t\/[^/]+(\/.*)$/);
  if (!match) return pathname;
  const suffix = match[1] ?? "";
  return TENANT_SUFFIX_TO_GLOBAL[suffix] ?? pathname;
}

/**
 * Returns `true` if the supplied pathname is inside the tenant-scoped settings
 * surface.
 */
export function isTenantSettingsPath(pathname: string): boolean {
  return /^\/t\/[^/]+\/settings/.test(pathname);
}
