import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useOrganization, useSession, useUser } from "@clerk/react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { apiGet } from "@/api/typedClient";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { useAuthContext } from "@/contexts/AuthContext";
import { useAccountContextStore } from "@/stores/accountContextStore";
import {
  parseAuthorizationCandidate,
  type AuthorizationResolution,
} from "./authorizationSnapshotSchema";

type LegacyAuthorizationResolution = {
  status: "legacy";
  snapshot: null;
  permissions: readonly string[];
  entitlements: readonly string[];
  tenantSlug: string | null;
  accountId: string | null;
};

type AuthorizationContextValue = (
  AuthorizationResolution | LegacyAuthorizationResolution
) & {
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

export function authorizationSnapshotQueryKey(
  sessionDiscriminator: string | null,
  clerkOrganizationId: string | null,
  accountId: string | null
) {
  return [
    "authorization-snapshot",
    "1",
    sessionDiscriminator,
    clerkOrganizationId,
    accountId ? `account:${accountId.trim()}` : "tenant",
  ] as const;
}

function valueFor(
  resolution: AuthorizationResolution | LegacyAuthorizationResolution
): AuthorizationContextValue {
  const roles =
    resolution.status === "verified" ? resolution.snapshot.roles : empty();
  const roleSet = new Set(roles);
  const permissions =
    resolution.status === "verified"
      ? resolution.snapshot.permissions
      : resolution.status === "legacy"
        ? resolution.permissions
        : empty();
  const entitlements =
    resolution.status === "verified"
      ? resolution.snapshot.entitlements
      : resolution.status === "legacy"
        ? resolution.entitlements
        : empty();
  const permissionSet = new Set(permissions);
  const entitlementSet = new Set(entitlements);
  return {
    ...resolution,
    hasAnyRole: required =>
      resolution.status === "verified" &&
      required.some(value => roleSet.has(value)),
    hasEveryPermission: required =>
      (resolution.status === "verified" || resolution.status === "legacy") &&
      required.every(
        value => permissionSet.has("*") || permissionSet.has(value)
      ),
    hasAnyPermission: required =>
      (resolution.status === "verified" || resolution.status === "legacy") &&
      required.some(
        value => permissionSet.has("*") || permissionSet.has(value)
      ),
    hasEveryEntitlement: required =>
      (resolution.status === "verified" || resolution.status === "legacy") &&
      required.every(
        value => entitlementSet.has("*") || entitlementSet.has(value)
      ),
    hasAnyEntitlement: required =>
      (resolution.status === "verified" || resolution.status === "legacy") &&
      required.some(
        value => entitlementSet.has("*") || entitlementSet.has(value)
      ),
    hasTenantMembership: tenantSlug =>
      resolution.status === "verified"
        ? !tenantSlug || resolution.snapshot.tenant.tenantSlug === tenantSlug
        : resolution.status === "legacy" &&
          (!tenantSlug || resolution.tenantSlug === tenantSlug),
    hasAccountAccess: accountId =>
      resolution.status === "verified"
        ? !!accountId &&
          resolution.snapshot.accountScope.scopeType === "account" &&
          resolution.snapshot.accountScope.accountId === accountId
        : resolution.status === "legacy" &&
          !!accountId &&
          resolution.accountId === accountId,
  };
}

function LegacyAuthorizationProvider({ children }: { children: ReactNode }) {
  const auth = useAuthContext();
  const { accountId } = useParams<{ accountId: string }>();
  const isAdmin =
    auth.user?.role === "admin" || auth.user?.role === "tenant_admin";
  const value = valueFor({
    status: "legacy",
    snapshot: null,
    permissions: isAdmin ? ["*"] : [],
    entitlements: isAdmin ? ["*"] : [],
    tenantSlug: auth.currentTenantSlug,
    accountId: accountId ?? null,
  });
  return (
    <AuthorizationContext.Provider value={value}>
      {children}
    </AuthorizationContext.Provider>
  );
}

function ClerkAuthorizationProvider({ children }: { children: ReactNode }) {
  const [clock, setClock] = useState(() => Date.now());
  const { isLoaded: userLoaded, user } = useUser();
  const { isLoaded: sessionLoaded, session } = useSession();
  const { isLoaded: organizationLoaded, organization } = useOrganization();
  const selectedAccountId = useAccountContextStore(
    state => state.selectedAccountId
  );
  const { accountId: routeAccountId } = useParams<{ accountId: string }>();
  const accountId = routeAccountId?.trim() || selectedAccountId?.trim() || null;
  const ready = userLoaded && sessionLoaded && organizationLoaded;
  const identityReady = ready && !!user && !!session && !!organization;
  const query = useQuery({
    queryKey: authorizationSnapshotQueryKey(
      session?.id ?? null,
      organization?.id ?? null,
      accountId
    ),
    queryFn: async () => {
      const response = await apiGet<unknown>(
        "api",
        "/auth/authorization-snapshot",
        accountId
          ? {
              headers: {
                "X-Account-ID": accountId,
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
  });

  useEffect(() => {
    if (query.data === undefined) return;
    const candidate = query.data as { expiresAt?: unknown };
    if (typeof candidate.expiresAt !== "string") return;
    const remaining = Date.parse(candidate.expiresAt) - Date.now();
    const timer = window.setTimeout(
      () => {
        setClock(Date.now());
        void query.refetch();
      },
      Math.max(0, remaining) + 1
    );
    return () => window.clearTimeout(timer);
  }, [query.data, query.refetch]);

  const resolution = useMemo<AuthorizationResolution>(() => {
    if (!ready || (identityReady && query.isPending))
      return { status: "loading", snapshot: null };
    if (!identityReady)
      return { status: "denied", snapshot: null, reason: "unauthenticated" };
    if (query.isError || query.data === undefined)
      return { status: "denied", snapshot: null, reason: "unavailable" };
    return parseAuthorizationCandidate(query.data, {
      clerkUserId: user.id,
      sessionDiscriminator: session.id,
      clerkOrganizationId: organization.id,
      accountId,
      now: new Date(clock),
    });
  }, [
    clock,
    identityReady,
    organization,
    query.data,
    query.isError,
    query.isPending,
    ready,
    accountId,
    session,
    user,
  ]);
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
