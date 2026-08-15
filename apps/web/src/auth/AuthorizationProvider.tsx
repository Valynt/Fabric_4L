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
import { useMatches } from "react-router-dom";
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

type AuthorizationContextValue =
  (AuthorizationResolution | LegacyAuthorizationResolution) & {
  hasEveryPermission: (permissions: readonly string[]) => boolean;
  hasAnyPermission: (permissions: readonly string[]) => boolean;
  hasEveryEntitlement: (entitlements: readonly string[]) => boolean;
  hasAnyEntitlement: (entitlements: readonly string[]) => boolean;
  hasTenantMembership: (tenantSlug?: string) => boolean;
  hasAccountAccess: (accountId?: string) => boolean;
};

const AuthorizationContext = createContext<AuthorizationContextValue | null>(
  null
);
const empty = (): readonly string[] => [];

type RouteMatchWithParams = {
  params: Record<string, string | undefined>;
};

type AccountAuthorizationActions = Pick<
  ReturnType<typeof useAccountContextStore.getState>,
  "authorizationVerified" | "authorizationUnavailable"
>;

type AccountAuthorizationResolution =
  | {
      status: "verified";
      snapshot: { tenant: { fabricTenantId: string } };
    }
  | {
      status: "loading" | "denied" | "expired";
      snapshot: null;
    };

export function resolveRouteAccountId(
  matches: readonly RouteMatchWithParams[],
  selectedAccountId: string | null
): string | null {
  for (let index = matches.length - 1; index >= 0; index -= 1) {
    const accountId = matches[index]?.params.accountId?.trim();
    if (accountId) return accountId;
  }
  return selectedAccountId?.trim() || null;
}

export function shouldHoldAuthorizationLoading({
  ready,
  identityReady,
  isPending,
  isFetching,
}: {
  ready: boolean;
  identityReady: boolean;
  isPending: boolean;
  isFetching: boolean;
}): boolean {
  return !ready || (identityReady && (isPending || isFetching));
}

export function synchronizeAccountAuthorization(
  resolution: AccountAuthorizationResolution,
  actions: AccountAuthorizationActions
): void {
  if (resolution.status === "verified") {
    actions.authorizationVerified(resolution.snapshot.tenant.fabricTenantId);
  } else if (
    resolution.status === "denied" ||
    resolution.status === "expired"
  ) {
    actions.authorizationUnavailable();
  }
}

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
      (resolution.status === "verified"
        ? !tenantSlug || resolution.snapshot.tenant.tenantSlug === tenantSlug
        : resolution.status === "legacy" &&
          (!tenantSlug || resolution.tenantSlug === tenantSlug)),
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
  const matches = useMatches();
  const accountId = resolveRouteAccountId(matches, null);
  const isAdmin = auth.user?.role === "admin" || auth.user?.role === "tenant_admin";
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
  const matches = useMatches();
  const accountId = resolveRouteAccountId(matches, selectedAccountId);
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
    const timer = window.setTimeout(() => {
      setClock(Date.now());
      void query.refetch();
    }, Math.max(0, remaining) + 1);
    return () => window.clearTimeout(timer);
  }, [query.data, query.refetch]);

  const resolution = useMemo<AuthorizationResolution>(() => {
    if (
      shouldHoldAuthorizationLoading({
        ready,
        identityReady,
        isPending: query.isPending,
        isFetching: query.isFetching,
      })
    )
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
    query.isFetching,
    query.isPending,
    ready,
    accountId,
    session,
    user,
  ]);

  useEffect(() => {
    useAccountContextStore.getState().authorizationIdentityChanged();
  }, [session?.id, organization?.id, user?.id]);

  useEffect(() => {
    synchronizeAccountAuthorization(
      resolution,
      useAccountContextStore.getState()
    );
  }, [resolution]);

  const value = useMemo(() => valueFor(resolution), [resolution]);
  return (
    <AuthorizationContext.Provider value={value}>
      {children}
    </AuthorizationContext.Provider>
  );
}

export function AuthorizationProvider({ children }: { children: ReactNode }) {
  if (!isClerkAuthEnabled()) {
    return <LegacyAuthorizationProvider>{children}</LegacyAuthorizationProvider>;
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
