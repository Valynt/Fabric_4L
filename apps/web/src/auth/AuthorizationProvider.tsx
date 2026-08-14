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
import { apiGet } from "@/api/typedClient";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { useAccountContextStore } from "@/stores/accountContextStore";
import {
  parseAuthorizationCandidate,
  type AuthorizationResolution,
} from "./authorizationSnapshotSchema";

type AuthorizationContextValue = AuthorizationResolution & {
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
  resolution: AuthorizationResolution
): AuthorizationContextValue {
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
  const [clock, setClock] = useState(() => Date.now());
  const { isLoaded: userLoaded, user } = useUser();
  const { isLoaded: sessionLoaded, session } = useSession();
  const { isLoaded: organizationLoaded, organization } = useOrganization();
  const selectedAccountId = useAccountContextStore(
    state => state.selectedAccountId
  );
  const ready = userLoaded && sessionLoaded && organizationLoaded;
  const identityReady = ready && !!user && !!session && !!organization;
  const query = useQuery({
    queryKey: authorizationSnapshotQueryKey(
      session?.id ?? null,
      organization?.id ?? null,
      selectedAccountId
    ),
    queryFn: async () => {
      const response = await apiGet<unknown>(
        "api",
        "/auth/authorization-snapshot",
        selectedAccountId
          ? {
              headers: { "X-Account-ID": selectedAccountId.trim() },
            }
          : undefined
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
    if (remaining <= 0) {
      setClock(Date.now());
      return;
    }
    const timer = window.setTimeout(() => setClock(Date.now()), remaining + 1);
    return () => window.clearTimeout(timer);
  }, [query.data]);

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
      accountId: selectedAccountId?.trim() || null,
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
    selectedAccountId,
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
      <AuthorizationContext.Provider
        value={valueFor({
          status: "denied",
          snapshot: null,
          reason: "unauthenticated",
        })}
      >
        {children}
      </AuthorizationContext.Provider>
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
