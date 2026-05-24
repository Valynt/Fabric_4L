/**
 * useAccountAccess — Verify user has access to the account in the URL.
 *
 * SECURITY WARNING: This hook currently returns true for any account ID
 * within a tenant the user is a member of. This is a TEMPORARY placeholder
 * until backend account ACL verification is implemented.
 *
 * TODO: Implement backend verification to check:
 *   1. Account exists
 *   2. User has explicit access to this account
 *   3. Account belongs to the user's tenant
 *
 * In the current architecture, account access is implicitly granted if the
 * user is a member of the tenant (account ownership is tenant-scoped).
 * This hook provides an explicit hook point for future fine-grained ACL.
 */

import { useMemo } from "react";
import { logWarn } from "@/lib/telemetry";
import { useTenantMembership } from "./useTenantMembership";

export function useAccountAccess(accountId: string | undefined, tenantSlug: string | undefined) {
  const { isMemberOfTenant, isLoading: tenantLoading } = useTenantMembership(tenantSlug);

  const hasAccountAccess = useMemo(() => {
    if (!accountId) return false;
    // SECURITY: Placeholder implementation - tenant membership implies account access
    // This MUST be replaced with backend verification before production use
    // Future: call backend to verify account exists and user can access it
    logWarn('useAccountAccess: Using placeholder implementation - no actual account ACL check', {
      accountId,
      tenantSlug,
    });
    return isMemberOfTenant;
  }, [accountId, isMemberOfTenant, tenantSlug]);

  return {
    hasAccountAccess,
    isLoading: tenantLoading,
  };
}
