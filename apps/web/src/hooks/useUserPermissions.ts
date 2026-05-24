/**
 * useUserPermissions — Check if the current user has the required permissions.
 *
 * Maps user role/tier to permission grants. Backend remains authoritative;
 * this is a frontend convenience for UI gating.
 */

import { useMemo } from "react";
import { useUserTierStore } from "@/stores/userTierStore";

const TIER_PERMISSIONS: Record<string, string[]> = {
  standard: ["account:read", "intelligence:read", "signals:read"],
  advanced: [
    "account:read",
    "intelligence:read",
    "signals:read",
    "formulas:read",
    "formulas:write",
    "ontology:read",
  ],
  admin: [
    "account:read",
    "intelligence:read",
    "signals:read",
    "formulas:read",
    "formulas:write",
    "ontology:read",
    "user:manage",
    "billing:manage",
    "integration:manage",
    "api_key:manage",
    "governance:read",
    "audit:read",
  ],
};

export function useUserPermissions(requiredPermissions: string[]) {
  const currentTier = useUserTierStore((state) => state.currentTier);

  const grantedPermissions = useMemo(() => {
    return TIER_PERMISSIONS[currentTier] ?? TIER_PERMISSIONS.standard;
  }, [currentTier]);

  const hasPermissions = useMemo(() => {
    if (requiredPermissions.length === 0) return true;
    return requiredPermissions.every((p) => grantedPermissions.includes(p));
  }, [requiredPermissions, grantedPermissions]);

  return {
    hasPermissions,
    isLoading: false,
    grantedPermissions,
  };
}
