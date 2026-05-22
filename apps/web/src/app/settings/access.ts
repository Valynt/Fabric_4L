import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuthContext } from "@/contexts/AuthContext";
import { apiClient } from "@/api/client";

export type SettingsCapability =
  | "personal"
  | "billing"
  | "team"
  | "integrations"
  | "governance"
  | "super_admin";

export type DenialReasonCode = "missing_role" | "scope_mismatch" | "feature_disabled" | "super_admin_only";

export interface CapabilityDecision {
  allowed: boolean;
  reasons: DenialReasonCode[];
  source: "server" | "fallback";
}

const ROLE_CAPABILITIES: Record<string, SettingsCapability[]> = {
  super_admin: ["personal", "billing", "team", "integrations", "governance", "super_admin"],
  tenant_admin: ["personal", "billing", "team", "integrations", "governance"],
  content_admin: ["personal", "governance"],
  analyst: ["personal"],
  read_only: ["personal"],
  admin: ["personal", "billing", "team", "integrations", "governance"],
  advanced: ["personal"],
  standard: ["personal"],
  viewer: ["personal"],
  user: ["personal"],
};

export interface EffectivePermissionsResponse {
  capabilities: Partial<Record<SettingsCapability, CapabilityDecision>>;
}

function normalizeRole(role: string | null | undefined): string {
  return role?.trim().toLowerCase() || "user";
}

export function getCapabilitiesForRole(role: string | null | undefined): Set<SettingsCapability> {
  return new Set(ROLE_CAPABILITIES[normalizeRole(role)] ?? ["personal"]);
}

export async function fetchEffectivePermissions(): Promise<EffectivePermissionsResponse> {
  const response = await apiClient.get<EffectivePermissionsResponse>("l4", "/me/permissions");
  return response.data;
}

export function buildFallbackDecision(role: string, capability: SettingsCapability): CapabilityDecision {
  const has = getCapabilitiesForRole(role).has(capability);
  return { allowed: has, reasons: has ? [] : ["missing_role"], source: "fallback" };
}

export function resolveCapabilityDecision(
  role: string,
  capability: SettingsCapability,
  serverCapabilities: Partial<Record<SettingsCapability, CapabilityDecision>>
): CapabilityDecision {
  const serverDecision = serverCapabilities[capability];
  if (serverDecision) return { ...serverDecision, source: "server" };
  return buildFallbackDecision(role, capability);
}

export function useSettingsAccess() {
  const { user } = useAuthContext();
  const role = normalizeRole(user?.role);
  const permissionsQuery = useQuery({
    queryKey: ["settings", "effective-permissions", user?.id, user?.tenantId],
    queryFn: fetchEffectivePermissions,
    staleTime: 60_000,
    retry: 1,
    enabled: Boolean(user),
  });

  return useMemo(() => {
    const serverCapabilities = permissionsQuery.data?.capabilities ?? {};

    const getCapabilityDecision = (capability: SettingsCapability): CapabilityDecision => {
      return resolveCapabilityDecision(role, capability, serverCapabilities);
    };

    return {
      role,
      getCapabilityDecision,
      capabilities: new Set((Object.keys(serverCapabilities) as SettingsCapability[]).filter((cap) => getCapabilityDecision(cap).allowed)),
      hasCapability: (capability: SettingsCapability) => getCapabilityDecision(capability).allowed,
      isUsingServerPolicy: Object.keys(serverCapabilities).length > 0,
    };
  }, [permissionsQuery.data?.capabilities, role]);
}

export function describeDenialReason(reason: DenialReasonCode): string {
  switch (reason) {
    case "missing_role":
      return "Missing required role";
    case "scope_mismatch":
      return "Tenant/workspace scope mismatch";
    case "feature_disabled":
      return "Feature flag is disabled for this tenant";
    case "super_admin_only":
      return "This path is restricted to super admins";
  }
}
