/**
 * useEntitlements — Check if the current plan has required entitlements.
 *
 * SECURITY WARNING: This hook currently returns true for all entitlements.
 * This is a TEMPORARY placeholder until billing/plan integration is implemented.
 *
 * TODO: Integrate with billing service to check active entitlements based on:
 *   1. User's subscription tier
 *   2. Feature flags
 *   3. Usage limits
 *
 * Placeholder for future billing/plan integration.
 */

import { useMemo } from "react";
import { logWarn } from "@/lib/telemetry";

export function useEntitlements(requiredEntitlements: string[]) {
  const entitlementsMet = useMemo(() => {
    if (requiredEntitlements.length === 0) return true;
    // SECURITY: Placeholder implementation - all entitlements pass
    // This MUST be replaced with billing integration before production use
    logWarn('useEntitlements: Using placeholder implementation - no actual entitlement check', {
      requiredEntitlements,
    });
    return true;
  }, [requiredEntitlements]);

  return {
    entitlementsMet,
    isLoading: false,
  };
}
