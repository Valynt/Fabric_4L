import { decideAuthorization } from "@/auth/authorizationSnapshot";
import { useAuthContext } from "@/contexts/AuthContext";
import { useAuthorizationSnapshot } from "./useAuthorizationSnapshot";

export function useEntitlements(requiredEntitlements: string[]) {
  const { currentTenantSlug } = useAuthContext();
  const resolution = useAuthorizationSnapshot(currentTenantSlug ?? undefined);
  const decision = decideAuthorization(resolution, {
    entitlements: requiredEntitlements,
  });
  return {
    entitlementsMet: decision.status === "allowed",
    denialReasons: {},
    isLoading: decision.status === "loading",
    isError: false,
  };
}
