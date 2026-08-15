/** Snapshot selector. Callers may use useAuthorizationSnapshot directly. */
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";

export function useUserPermissions(requiredPermissions: string[]) {
  const authorization = useAuthorizationSnapshot();
  return {
    hasPermissions: authorization.hasEveryPermission(requiredPermissions),
    isLoading: authorization.status === "loading",
    grantedPermissions:
      authorization.status === "verified"
        ? authorization.snapshot.permissions
        : [],
  };
}
