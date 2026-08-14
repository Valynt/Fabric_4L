/** @deprecated Temporary selector over AuthorizationProvider. */
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";

export function useAccountAccess(
  accountId: string | undefined,
  _tenantSlug: string | undefined
) {
  const authorization = useAuthorizationSnapshot();
  return {
    hasAccountAccess: authorization.hasAccountAccess(accountId),
    denyReason:
      authorization.status === "verified" ? undefined : authorization.status,
    isLoading: authorization.status === "loading",
    isError:
      authorization.status === "denied" || authorization.status === "expired",
  };
}
