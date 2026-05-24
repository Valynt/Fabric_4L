/**
 * useTenantMembership — Verify user belongs to the tenant in the URL slug.
 */

import { useMemo } from "react";
import { useAuthContext } from "@/contexts/AuthContext";

export function useTenantMembership(tenantSlug: string | undefined) {
  const { user, isLoading } = useAuthContext();

  const isMemberOfTenant = useMemo(() => {
    if (!tenantSlug || !user) return false;
    // Primary check: user's current tenant slug matches URL slug
    if (user.tenantSlug === tenantSlug) return true;
    // Fallback: if user has multiple tenant memberships (future), check list
    // const accessibleSlugs = user.tenantSlugs ?? [user.tenantSlug];
    // return accessibleSlugs.includes(tenantSlug);
    return false;
  }, [tenantSlug, user]);

  return {
    isMemberOfTenant,
    isLoading,
  };
}
