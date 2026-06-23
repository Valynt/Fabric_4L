/**
 * useTenantMembership — Verify user belongs to the tenant in the URL slug.
 *
 * Phase 2: When Clerk is enabled, derives membership from the active Clerk
 * organization slug instead of legacy AuthContext metadata.
 */

import { useMemo } from "react";
import { useOrganization } from "@clerk/react";
import { useAuthContext } from "@/contexts/AuthContext";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { matchesClerkTenantRouteSlug } from "@/auth/clerkTenant";

interface TenantMembership {
  isMemberOfTenant: boolean;
  isLoading: boolean;
}

/**
 * Clerk-mode implementation. Membership is derived from the active Clerk
 * organization slug. useOrganization() is called unconditionally because this
 * hook is only selected when Clerk is enabled and <ClerkProvider> is mounted.
 */
function useTenantMembershipClerk(tenantSlug: string | undefined): TenantMembership {
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
function useTenantMembershipLegacy(tenantSlug: string | undefined): TenantMembership {
  const { user, isLoading: legacyLoading } = useAuthContext();

  const isMemberOfTenant = useMemo(() => {
    if (!tenantSlug) return false;
    if (!user) return false;
    return user.tenantSlug === tenantSlug;
  }, [tenantSlug, user]);

  return { isMemberOfTenant, isLoading: legacyLoading };
}

/**
 * Resolve tenant membership at render time based on the active auth provider.
 *
 * The auth provider flag is stable for the lifetime of the app, so the hook
 * branch is effectively fixed once the app mounts. This pattern is used by
 * other auth-aware components (e.g., UnifiedRouteGuard, RootAuthStateAdapter)
 * and allows tests to switch providers without re-importing the module.
 */
export function useTenantMembership(tenantSlug: string | undefined): TenantMembership {
  // Auth-provider is stable at runtime; branch once per render.
  if (isClerkAuthEnabled()) {
    return useTenantMembershipClerk(tenantSlug);
  }
  return useTenantMembershipLegacy(tenantSlug);
}
