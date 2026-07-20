/**
 * Tenant membership hooks — verify the user belongs to the tenant in the URL
 * slug.
 *
 * Phase 2: When Clerk is enabled, membership is derived from the active Clerk
 * organization slug instead of legacy AuthContext metadata.
 *
 * The auth provider flag is stable for the lifetime of the app, and
 * <ClerkProvider> is only mounted in Clerk mode, so the two implementations
 * are exposed as separate hooks instead of a conditional dispatcher: callers
 * select the implementation at the component level (see UnifiedRouteGuard),
 * which keeps every hook call unconditional (rules-of-hooks) and never calls
 * Clerk hooks outside <ClerkProvider>.
 */

import { useMemo } from "react";
import { useOrganization } from "@clerk/react";
import { useAuthContext } from "@/contexts/AuthContext";
import { matchesClerkTenantRouteSlug } from "@/auth/clerkTenant";

export interface TenantMembership {
  isMemberOfTenant: boolean;
  isLoading: boolean;
}

/**
 * Clerk-mode implementation. Membership is derived from the active Clerk
 * organization slug. Only call this hook when Clerk is enabled and
 * <ClerkProvider> is mounted; useOrganization() throws otherwise.
 */
export function useTenantMembershipClerk(tenantSlug: string | undefined): TenantMembership {
  const { organization, isLoaded: orgLoaded } = useOrganization();

  const isMemberOfTenant = useMemo(() => {
    if (!tenantSlug) return false;
    // Under Clerk, membership is determined by active organization slug.
    // The backend is the ultimate authority; this is a UX convenience.
    if (!orgLoaded) return false;
    return matchesClerkTenantRouteSlug(organization, tenantSlug);
  }, [tenantSlug, orgLoaded, organization]);

  return { isMemberOfTenant, isLoading: !orgLoaded };
}

/**
 * Legacy-mode implementation. Never calls Clerk hooks, so it is safe to use
 * when <ClerkProvider> is not mounted.
 */
export function useTenantMembershipLegacy(tenantSlug: string | undefined): TenantMembership {
  const { user, isLoading: legacyLoading } = useAuthContext();

  const isMemberOfTenant = useMemo(() => {
    if (!tenantSlug) return false;
    if (!user) return false;
    return user.tenantSlug === tenantSlug;
  }, [tenantSlug, user]);

  return { isMemberOfTenant, isLoading: legacyLoading };
}
