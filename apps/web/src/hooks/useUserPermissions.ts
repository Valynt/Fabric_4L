import { useMemo } from "react";
import {
  useAuthorizationSnapshot,
  type AuthorizationSnapshotState,
} from "@/hooks/useAuthorizationSnapshot";

export type AuthorizationDecision =
  | { status: "loading" }
  | { status: "allowed" }
  | { status: "denied"; reason: string }
  | { status: "expired"; reason: string };

export function decideUserPermissions(
  snapshot: AuthorizationSnapshotState,
  requiredPermissions: readonly string[]
): AuthorizationDecision {
  if (snapshot.status === "loading") return { status: "loading" };
  if (snapshot.status === "expired")
    return { status: "expired", reason: snapshot.reason };
  if (snapshot.status === "denied")
    return { status: "denied", reason: snapshot.reason };
  const grants = new Set(snapshot.permissions);
  return requiredPermissions.every(permission => grants.has(permission))
    ? { status: "allowed" }
    : { status: "denied", reason: "missing_permission" };
}

export function useUserPermissions(
  requiredPermissions: string[],
  tenantSlug?: string
) {
  const snapshot = useAuthorizationSnapshot(tenantSlug);
  const decision = useMemo(
    () => decideUserPermissions(snapshot, requiredPermissions),
    [requiredPermissions, snapshot]
  );
  return {
    snapshot,
    decision,
    hasPermissions: decision.status === "allowed",
    isLoading: decision.status === "loading",
    grantedPermissions:
      snapshot.status === "verified" ? snapshot.permissions : [],
  };
}
