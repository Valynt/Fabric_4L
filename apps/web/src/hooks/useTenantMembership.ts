import { decideAuthorization } from "@/auth/authorizationSnapshot";
import { useAuthorizationSnapshot } from "./useAuthorizationSnapshot";

export interface TenantMembership {
  isMemberOfTenant: boolean;
  isLoading: boolean;
}

function useSnapshotMembership(
  tenantSlug: string | undefined
): TenantMembership {
  const resolution = useAuthorizationSnapshot(tenantSlug);
  const decision = decideAuthorization(resolution, { tenantMember: true });
  return {
    isMemberOfTenant: decision.status === "allowed",
    isLoading: decision.status === "loading",
  };
}

export const useTenantMembershipClerk = useSnapshotMembership;
export const useTenantMembershipLegacy = useSnapshotMembership;
