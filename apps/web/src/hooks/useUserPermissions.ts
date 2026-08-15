/** @deprecated Migrate callers to useAuthorizationSnapshot directly. Delete
 * after guard, navigation, actions, tests, and fixtures use the provider. */
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";

export function useUserPermissions(requiredPermissions: string[]) {
  const authorization = useAuthorizationSnapshot();
  return {
    hasPermissions: authorization.hasEveryPermission(requiredPermissions),
    isLoading: authorization.status === "loading",
    grantedPermissions:
      authorization.status === "verified"
        ? authorization.snapshot.permissions
        : authorization.status === "legacy"
          ? [...authorization.permissions]
          : [],
  };
}
