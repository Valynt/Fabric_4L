/**
 * useAccountAccess — Verify user has access to the account in the URL.
 *
 * In the current architecture, account access is implicitly granted if the
 * user is a member of the tenant (account ownership is tenant-scoped).
 * This hook provides an explicit hook point for future fine-grained ACL.
 */

import { useMemo } from "react";
import { useTenantMembership } from "./useTenantMembership";

export function useAccountAccess(accountId: string | undefined) {
  const { isMemberOfTenant, isLoading: tenantLoading } = useTenantMembership(
    // In practice we need the tenant slug from URL; this hook should be
    // called in a component that has access to useParams().tenantSlug
    // For now, we rely on the caller having validated tenant membership first.
    undefined
  );

  const hasAccountAccess = useMemo(() => {
    if (!accountId) return false;
    // Future: call backend to verify account exists and user can access it
    // For now, tenant membership implies account access within that tenant
    return true;
  }, [accountId]);

  return {
    hasAccountAccess,
    isLoading: tenantLoading,
  };
}
