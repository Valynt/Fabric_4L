import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { useLocation } from "react-router-dom";
import { useOrganization, useSession, useUser } from "@clerk/react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { useResolvedTenant } from "@/hooks/useResolvedTenant";
import { useAccountContextStore } from "@/stores/accountContextStore";
import {
  parseAuthorizationCandidate,
  type AuthorizationResolution,
} from "./authorizationSnapshotSchema";

type AuthorizationContextValue = AuthorizationResolution & {
  hasEveryPermission: (permissions: readonly string[]) => boolean;
  hasAnyPermission: (permissions: readonly string[]) => boolean;
  hasAnyRole: (roles: readonly string[]) => boolean;
  hasEveryEntitlement: (entitlements: readonly string[]) => boolean;
  hasAnyEntitlement: (entitlements: readonly string[]) => boolean;
  hasTenantMembership: (tenantSlug?: string) => boolean;
  hasAccountAccess: (accountId?: string) => boolean;
};

const AuthorizationContext = createContext<AuthorizationContextValue | null>(
  null
);
const empty = (): readonly string[] => [];

const ACCOUNT_SCOPE_PATH = /\/accounts\/([^/]+)(?:\/|$)/;

export function accountScopeFromPath(pathname: string): string | null {
  const match = ACCOUNT_SCOPE_PATH.exec(pathname);
  return match?.[1]?.trim() || null;
}

export function authorizationSnapshotQueryKey(
  sessionDiscriminator: string | null,
  fabricTenantId: string | null,
  accountId: string | null
) {
  return [
    "authorization-snapshot",
    "1",
    sessionDiscriminator,
    fabricTenantId,
    accountId ? `account:${accountId.trim()}` : "tenant",
  ] as const;
}

function valueFor(
  resolution: AuthorizationResolution
): AuthorizationContextValue {
  const roles =
    resolution.status === "verified" ? resolution.snapshot.roles : empty();
  const roleSet = new Set(roles);
  const permissions =
    resolution.status === "verified"
      ? resolution.snapshot.permissions
      : empty();
  const entitlements =
    resolution.status === "verified"
      ? resolution.snapshot.entitlements
      : empty();
  const permissionSet = new Set(permissions);
  const entitlementSet = new Set(entitlements);
  return {
    ...resolution,
    hasAnyRole: required =>
      resolution.status === "verified" &&
      required.some(value => roleSet.has(value)),
    hasEveryPermission: required =>
      resolution.status === "verified" &&
      required.every(
        value => permissionSet.has("*") || permissionSet.has(value)
      ),
    hasAnyPermission: required =>
      resolution.status === "verified" &&
      required.some(
        value => permissionSet.has("*") || permissionSet.has(value)
      ),
    hasEveryEntitlement: required =>
      resolution.status === "verified" &&
      required.every(value => entitlementSet.has(value)),
    hasAnyEntitlement: required =>
      resolution.status === "verified" &&
      required.some(value => entitlementSet.has(value)),
    hasTenantMembership: tenantSlug =>
      resolution.status === "verified" &&
      (!tenantSlug || resolution.snapshot.tenant.tenantSlug === tenantSlug),
    hasAccountAccess: accountId =>
      resolution.status === "verified" &&
      !!accountId &&
      resolution.snapshot.accountScope.scopeType === "account" &&
      resolution.snapshot.accountScope.accountId === accountId,
  };
}

function ClerkAuthorizationProvider({ children }: { children: ReactNode }) {
  const { isLoaded: userLoaded, user } = useUser();
  const { isLoaded: sessionLoaded, session } = useSession();
  const { isLoaded: organizationLoaded, organization } = useOrganization();
  const { tenant, isLoading: tenantLoading } = useResolvedTenant();
  const location = useLocation();
  const routeAccountId = accountScopeFromPath(location.pathname);
  const ready = userLoaded && sessionLoaded && organizationLoaded;
  const identityReady =
    ready && !!user && !!session && !!organization && !!tenant?.fabricTenantId;
  const query = useQuery({
    queryKey: authorizationSnapshotQueryKey(
      session?.id ?? null,
      tenant?.fabricTenantId ?? null,
      routeAccountId
    ),
    queryFn: async () => {
      const response = await apiGet<unknown>(
        "api",
        "/auth/authorization-snapshot",
        routeAccountId
          ? {
              headers: {
                "X-Account-ID": routeAccountId,
                "X-Fabric-Skip-Auth-Redirect": "true",
              },
            }
          : { headers: { "X-Fabric-Skip-Auth-Redirect": "true" } }
      );
      return response.data;
    },
    enabled: identityReady,
    placeholderData: undefined,
    retry: false,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (query.data === undefined) return;
    const candidate = query.data as { expiresAt?: unknown };
    if (typeof candidate.expiresAt !== "string") return;
    const remaining = Date.parse(candidate.expiresAt) - Date.now();
    const delay = Math.max(0, remaining - 1_000);
    const timer = window.setTimeout(() => {
      void query.refetch();
    }, delay);
    return () => window.clearTimeout(timer);
  }, [query.data, query.refetch]);

  const resolution = useMemo<AuthorizationResolution>(() => {
    if (!ready || tenantLoading || (identityReady && query.isPending))
      return { status: "loading", snapshot: null };
    if (!identityReady)
      return { status: "denied", snapshot: null, reason: "unauthenticated" };
    if (query.isError)
      return { status: "denied", snapshot: null, reason: "unavailable" };
    if (query.data === undefined)
      return query.isFetching
        ? { status: "loading", snapshot: null }
        : { status: "denied", snapshot: null, reason: "unavailable" };
    const parsed = parseAuthorizationCandidate(query.data, {
      clerkUserId: user.id,
      sessionDiscriminator: session.id,
      clerkOrganizationId: organization.id,
      fabricTenantId: tenant.fabricTenantId,
      accountId: routeAccountId,
    });
    if (parsed.status === "expired" && query.isFetching)
      return { status: "loading", snapshot: null };
    return parsed;
  }, [
    identityReady,
    organization,
    query.data,
    query.isError,
    query.isFetching,
    query.isPending,
    ready,
    routeAccountId,
    session,
    tenant,
    tenantLoading,
    user,
  ]);

  useEffect(() => {
    const store = useAccountContextStore.getState();
    if (resolution.status === "verified") {
      store.authorizationVerified(resolution.snapshot.tenant.fabricTenantId);
      return;
    }
    if (resolution.status === "denied" || resolution.status === "expired") {
      store.authorizationUnavailable();
    }
  }, [resolution]);

  const value = useMemo(() => valueFor(resolution), [resolution]);
  return (
    <AuthorizationContext.Provider value={value}>
      {children}
    </AuthorizationContext.Provider>
  );
}

function LegacyAuthorizationProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const routeAccountId = accountScopeFromPath(location.pathname);
  const query = useQuery({
    queryKey: authorizationSnapshotQueryKey(
      "legacy",
      "legacy",
      routeAccountId
    ),
    queryFn: async () => {
      const response = await apiGet<unknown>(
        "api",
        "/auth/authorization-snapshot",
        routeAccountId
          ? {
              headers: {
                "X-Account-ID": routeAccountId,
                "X-Fabric-Skip-Auth-Redirect": "true",
              },
            }
          : { headers: { "X-Fabric-Skip-Auth-Redirect": "true" } }
      );
      return response.data;
    },
    placeholderData: undefined,
    retry: false,
    gcTime: 0,
  });

  const resolution = useMemo<AuthorizationResolution>(() => {
    if (query.isPending) return { status: "loading", snapshot: null };
    if (query.isError || query.data === undefined)
      return { status: "denied", snapshot: null, reason: "unavailable" };
    return parseAuthorizationCandidate(query.data, {
      clerkUserId: "legacy",
      sessionDiscriminator: "legacy",
      clerkOrganizationId: "legacy",
      fabricTenantId: "legacy",
      accountId: routeAccountId,
    });
  }, [query.data, query.isError, query.isPending, routeAccountId]);

  const value = useMemo(() => valueFor(resolution), [resolution]);
  return (
    <AuthorizationContext.Provider value={value}>
      {children}
    </AuthorizationContext.Provider>
  );
}

export function AuthorizationProvider({ children }: { children: ReactNode }) {
  if (!isClerkAuthEnabled()) {
    return (
      <LegacyAuthorizationProvider>{children}</LegacyAuthorizationProvider>
    );
  }
  return <ClerkAuthorizationProvider>{children}</ClerkAuthorizationProvider>;
}

export function useAuthorizationSnapshot(): AuthorizationContextValue {
  const value = useContext(AuthorizationContext);
  if (!value)
    throw new Error(
      "useAuthorizationSnapshot must be used within AuthorizationProvider"
    );
  return value;
}
