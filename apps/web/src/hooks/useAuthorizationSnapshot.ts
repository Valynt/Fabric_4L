import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiGet } from "@/api/typedClient";
import { useAuthContext } from "@/contexts/AuthContext";

const EMPTY_GRANTS = [] as const;
const KNOWN_CLERK_ROLES = new Set([
  "org:admin",
  "org:member",
  "admin",
  "super_admin",
  "tenant_admin",
  "content_admin",
  "analyst",
  "editor",
  "advanced",
  "read_only",
  "viewer",
  "user",
  "standard",
]);

const snapshotSchema = z.object({
  tenantId: z.string().min(1),
  tenantSlug: z.string().min(1),
  role: z.string().min(1),
  expiresAt: z.iso.datetime(),
  permissions: z.array(z.string().min(1)),
  entitlements: z.array(z.string().min(1)),
  tenantMember: z.literal(true),
  accountIds: z.array(z.string().min(1)),
});

export type VerifiedAuthorizationSnapshot = z.infer<typeof snapshotSchema>;

export type AuthorizationSnapshotState =
  | {
      status: "loading";
      permissions: typeof EMPTY_GRANTS;
      entitlements: typeof EMPTY_GRANTS;
    }
  | {
      status: "denied";
      reason: string;
      permissions: typeof EMPTY_GRANTS;
      entitlements: typeof EMPTY_GRANTS;
    }
  | {
      status: "expired";
      reason: string;
      permissions: typeof EMPTY_GRANTS;
      entitlements: typeof EMPTY_GRANTS;
    }
  | {
      status: "verified";
      snapshot: VerifiedAuthorizationSnapshot;
      permissions: readonly string[];
      entitlements: readonly string[];
    };

type SnapshotResponse = { snapshot?: unknown };

const noGrants = (
  status: "loading" | "denied" | "expired",
  reason?: string
): AuthorizationSnapshotState =>
  status === "loading"
    ? { status, permissions: EMPTY_GRANTS, entitlements: EMPTY_GRANTS }
    : {
        status,
        reason: reason ?? status,
        permissions: EMPTY_GRANTS,
        entitlements: EMPTY_GRANTS,
      };

export function parseAuthorizationSnapshot(
  value: unknown,
  expectedTenantSlug: string | undefined,
  now = Date.now()
): AuthorizationSnapshotState {
  if (!expectedTenantSlug) return noGrants("denied", "missing_tenant");
  const parsed = snapshotSchema.safeParse(value);
  if (!parsed.success) return noGrants("denied", "malformed_snapshot");
  if (!KNOWN_CLERK_ROLES.has(parsed.data.role))
    return noGrants("denied", "unknown_role");
  if (parsed.data.tenantSlug !== expectedTenantSlug)
    return noGrants("denied", "tenant_mismatch");
  if (Date.parse(parsed.data.expiresAt) <= now)
    return noGrants("expired", "snapshot_expired");
  return {
    status: "verified",
    snapshot: parsed.data,
    permissions: parsed.data.permissions,
    entitlements: parsed.data.entitlements,
  };
}

export function useAuthorizationSnapshot(
  tenantSlug?: string
): AuthorizationSnapshotState {
  const auth = useAuthContext();
  const activeTenant = tenantSlug ?? auth.currentTenantSlug ?? undefined;
  const refreshAttempted = useRef(false);
  const query = useQuery({
    queryKey: ["authz", "snapshot", activeTenant ?? null],
    queryFn: async () => {
      const response = await apiGet<SnapshotResponse>(
        "l4",
        `/v1/authz/snapshot?tenant_slug=${encodeURIComponent(activeTenant ?? "")}`
      );
      return response.data.snapshot;
    },
    enabled: auth.isAuthenticated && Boolean(activeTenant),
    retry: false,
  });

  const state = useMemo<AuthorizationSnapshotState>(() => {
    if (auth.isLoading || query.isLoading) return noGrants("loading");
    if (!auth.isAuthenticated || !activeTenant)
      return noGrants("denied", "snapshot_unavailable");
    if (query.isError || query.data === undefined)
      return noGrants("denied", "snapshot_fetch_failed");
    return parseAuthorizationSnapshot(query.data, activeTenant);
  }, [
    activeTenant,
    auth.isAuthenticated,
    auth.isLoading,
    query.data,
    query.isError,
    query.isLoading,
  ]);

  useEffect(() => {
    if (state.status === "expired" && !refreshAttempted.current) {
      refreshAttempted.current = true;
      void query.refetch();
    }
    if (state.status === "verified") refreshAttempted.current = false;
  }, [query, state.status]);

  if (state.status === "expired" && query.isFetching)
    return noGrants("loading");
  return state;
}
