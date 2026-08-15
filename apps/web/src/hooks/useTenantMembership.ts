/** @deprecated Temporary selectors over AuthorizationProvider. */
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";

export interface TenantMembership {
  isMemberOfTenant: boolean;
  isLoading: boolean;
}

function useSnapshotTenantMembership(
  tenantSlug: string | undefined
): TenantMembership {
  const authorization = useAuthorizationSnapshot();
  return {
    isMemberOfTenant: authorization.hasTenantMembership(tenantSlug),
    isLoading: authorization.status === "loading",
  };
}

export const useTenantMembershipClerk = useSnapshotTenantMembership;
export const useTenantMembershipLegacy = useSnapshotTenantMembership;
