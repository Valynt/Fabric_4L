import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import {
  deniedAuthorization,
  expiredAuthorization,
  loadingAuthorization,
  parseAuthorizationSnapshot,
  type AuthorizationResolution,
  type AuthorizationSnapshot,
} from "@/auth/authorizationSnapshot";

export function useAuthorizationSnapshot(
  tenantSlug: string | undefined
): AuthorizationResolution {
  const [clock, setClock] = useState(Date.now());
  const refreshAttempted = useRef(false);
  const verifiedForTenant = useRef<string | null>(null);
  const query = useQuery({
    queryKey: ["authz", "snapshot", tenantSlug ?? null],
    queryFn: async () =>
      (
        await apiGet<AuthorizationSnapshot>(
          "l4",
          `/v1/authz/snapshot?tenant_slug=${encodeURIComponent(tenantSlug ?? "")}`
        )
      ).data,
    enabled: Boolean(tenantSlug),
    retry: false,
    staleTime: 0,
  });

  useEffect(() => {
    refreshAttempted.current = false;
    verifiedForTenant.current = null;
    setClock(Date.now());
  }, [tenantSlug]);

  const resolution = useMemo(() => {
    if (!tenantSlug || query.isLoading || (query.isFetching && !query.data))
      return loadingAuthorization;
    if (query.isError || !query.data) {
      return verifiedForTenant.current === tenantSlug
        ? expiredAuthorization
        : deniedAuthorization;
    }
    const parsed = parseAuthorizationSnapshot(query.data, tenantSlug, clock);
    if (parsed.status === "verified") verifiedForTenant.current = tenantSlug;
    return parsed;
  }, [
    clock,
    query.data,
    query.isError,
    query.isFetching,
    query.isLoading,
    tenantSlug,
  ]);

  useEffect(() => {
    if (resolution.status !== "verified") return;
    const delay = Math.max(
      0,
      Date.parse(resolution.snapshot.expiresAt) - Date.now()
    );
    const timer = window.setTimeout(() => setClock(Date.now()), delay);
    return () => window.clearTimeout(timer);
  }, [resolution]);

  useEffect(() => {
    if (resolution.status !== "expired" || refreshAttempted.current) return;
    refreshAttempted.current = true;
    void query.refetch().finally(() => setClock(Date.now()));
  }, [query, resolution.status]);

  if (resolution.status === "expired") return expiredAuthorization;
  return resolution;
}
