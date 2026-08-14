/** @deprecated Snapshot selector retained until all callers use
 * useAuthorizationSnapshot directly. It performs no authorization fetch. */
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";

export function useEntitlements(requiredEntitlements: string[]) {
  const authorization = useAuthorizationSnapshot();
  return {
    entitlementsMet: authorization.hasEveryEntitlement(requiredEntitlements),
    denialReasons: {},
    isLoading: authorization.status === "loading",
    isError:
      authorization.status === "denied" || authorization.status === "expired",
  };
}
