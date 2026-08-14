import { decideAuthorization } from "@/auth/authorizationSnapshot";
import { useAuthorizationSnapshot } from "./useAuthorizationSnapshot";

export function useAccountAccess(
  accountId: string | undefined,
  tenantSlug: string | undefined
) {
  const resolution = useAuthorizationSnapshot(tenantSlug);
  const decision = decideAuthorization(resolution, { accountId });
  return {
    hasAccountAccess: decision.status === "allowed",
    denyReason: decision.status,
    isLoading: decision.status === "loading",
    isError: false,
  };
}
