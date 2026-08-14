import { useMemo } from "react";
import { decideAuthorization } from "@/auth/authorizationSnapshot";
import { useAuthorizationSnapshot } from "./useAuthorizationSnapshot";

export function useUserPermissions(
  requiredPermissions: string[],
  tenantSlug?: string
) {
  const resolution = useAuthorizationSnapshot(tenantSlug);
  const decision = useMemo(
    () => decideAuthorization(resolution, { permissions: requiredPermissions }),
    [requiredPermissions, resolution]
  );
  return {
    decision,
    hasPermissions: decision.status === "allowed",
    isLoading: decision.status === "loading",
    grantedPermissions:
      resolution.status === "verified" ? resolution.permissions : [],
  };
}
