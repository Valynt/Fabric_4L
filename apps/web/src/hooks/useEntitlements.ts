import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import { createFeatureLogger } from "@/lib/telemetry";

const log = createFeatureLogger("use-entitlements");

type EntitlementDecision = {
  allowed: boolean;
  reason: string;
};

type EntitlementsCheckResponse = {
  decisions: Record<string, EntitlementDecision>;
};

export function useEntitlements(requiredEntitlements: string[]) {
  const uniqueRequired = useMemo(
    () => Array.from(new Set(requiredEntitlements.filter(Boolean))).sort(),
    [requiredEntitlements]
  );

  const query = useQuery({
    queryKey: ["authz", "entitlements", uniqueRequired],
    queryFn: async () => {
      const response = await apiGet<EntitlementsCheckResponse>(
        "l4",
        `/v1/authz/entitlements/check?entitlements=${encodeURIComponent(uniqueRequired.join(","))}`
      );
      return response.data;
    },
    enabled: uniqueRequired.length > 0,
    retry: false,
  });

  const entitlementsMet = useMemo(() => {
    if (uniqueRequired.length === 0) return true;
    if (query.isLoading || query.isError || !query.data?.decisions) return false;
    return uniqueRequired.every((key) => query.data.decisions[key]?.allowed === true);
  }, [query.data, query.isError, query.isLoading, uniqueRequired]);

  const denialReasons = useMemo(() => {
    if (!query.data?.decisions) return {} as Record<string, string>;
    return Object.fromEntries(
      Object.entries(query.data.decisions).reduce((acc, [key, value]) => {
        if (value.allowed !== true) {
          acc.push([key, value.reason]);
        }
        return acc;
      }, [] as [string, string][])
    );
  }, [query.data]);

  if (query.isError) {
    log.warn("Entitlement verification failed; denying by default", {
      requiredEntitlements: uniqueRequired,
    });
  }

  return {
    entitlementsMet,
    denialReasons,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
