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

export function useTenantMembership(tenantSlug: string | undefined) {
  const { user, isLoading: legacyLoading } = useAuthContext();
  const { organization, isLoaded: orgLoaded } = useOrganization();
  const clerkEnabled = isClerkAuthEnabled();

  const isMemberOfTenant = useMemo(() => {
    if (!tenantSlug) return false;

    if (clerkEnabled) {
      // Under Clerk, membership is determined by active organization slug.
      // The backend is the ultimate authority; this is a UX convenience.
      if (!orgLoaded) return false;
      return organization?.slug === tenantSlug;
    }

    // Legacy path: user's current tenant slug matches URL slug
    if (!user) return false;
    if (user.tenantSlug === tenantSlug) return true;
    return false;
  }, [tenantSlug, user, clerkEnabled, orgLoaded, organization?.slug]);

  const isLoading = clerkEnabled ? !orgLoaded : legacyLoading;

  return {
    isMemberOfTenant,
    isLoading,
  };
}
