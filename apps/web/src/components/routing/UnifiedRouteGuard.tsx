import { Navigate, useLocation, useParams, useMatches } from "react-router-dom";
import { useAuth as useClerkAuth } from "@clerk/react";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { useAuthContext } from "@/contexts/AuthContext";
import {
  useTenantMembershipClerk,
  useTenantMembershipLegacy,
  type TenantMembership,
} from "@/hooks/useTenantMembership";
import { useAccountAccess } from "@/hooks/useAccountAccess";
import { useUserPermissions } from "@/hooks/useUserPermissions";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { useEntitlements } from "@/hooks/useEntitlements";
import { useUserTierStore } from "@/stores";
import { type RouteAccessPolicy } from "@/routes/types";
import { ErrorBoundary } from "@/components";
import { createFeatureLogger } from "@/lib/telemetry";

const log = createFeatureLogger("route-guard");

const FAIL_CLOSED_ACCESS_POLICY: RouteAccessPolicy = {
  requiresAuth: true,
  tenantScoped: false,
  fallbackRoute: "/sign-in",
  analyticsRouteId: "route.unclassified",
};

interface UnifiedRouteGuardProps {
  children: React.ReactNode;
}

interface RouteGuardAuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
}

type PrivilegedPersistedTier = "advanced" | "admin";



function UnifiedRouteGuardInner({
  children,
  authStateOverride,
  tenantMembershipOverride,
}: UnifiedRouteGuardProps & {
  authStateOverride?: RouteGuardAuthState;
  tenantMembershipOverride?: TenantMembership;
}) {
  const location = useLocation();
  const params = useParams();
  const matches = useMatches();

  // Derive auth state from the app's AuthContext, which is the single source of
  // truth for both Clerk and mock/dev mode (VITE_ENABLE_MOCK_AUTH). Calling Clerk's
  // useAuth() directly here would hang on "Verifying access..." in mock mode because
  // Clerk never finishes loading without a real publishable key/session.
  const authContext = useAuthContext();
  const { isAuthenticated, isLoading } = authStateOverride ?? authContext;
  const loginPath = "/sign-in";

  // Walk up the match tree to find the most specific access policy
  const policy = matches
    .flatMap((m) => {
      const p = (m.handle as Record<string, unknown> | undefined)?.accessPolicy as RouteAccessPolicy | undefined;
      return p ? [p] : [];
    })
    .pop() ?? FAIL_CLOSED_ACCESS_POLICY;

  // ALL hooks must be called before any conditional return (Rules of Hooks).
  // Use optional chaining so hooks are unconditionally invoked even when policy
  // is undefined; the conditional guard logic below still short-circuits safely.
  const { canAccessRoute, isRehydrated } = useUserTierStore();
  const tierStoreHydrated = isRehydrated || useUserTierStore.persist.hasHydrated();

  const tenantSlug = params.tenantSlug;
  // Legacy (AuthContext) membership is always resolved here; in Clerk mode the
  // outer ClerkUnifiedRouteGuard supplies a Clerk-derived override, mirroring
  // authStateOverride, so Clerk hooks never run without <ClerkProvider>.
  const legacyTenantMembership = useTenantMembershipLegacy(tenantSlug);
  const { isMemberOfTenant, isLoading: tenantLoading } =
    tenantMembershipOverride ?? legacyTenantMembership;

  const accountId = params.accountId;
  const { hasAccountAccess, isLoading: accountLoading } =
    useAccountAccess(accountId, tenantSlug);

  const { hasPermissions, isLoading: permLoading } = useUserPermissions(
    policy?.requiredPermissions ?? []
  );

  const { flagsEnabled } = useFeatureFlags(
    policy?.requiredFeatureFlags ?? []
  );

  const { entitlementsMet, isLoading: entitlementsLoading } = useEntitlements(
    policy?.requiredEntitlements ?? []
  );

  if (isLoading) {
    return <RouteGuardSkeleton />;
  }



  // 1. Authentication guard
  if (policy.requiresAuth && !isAuthenticated) {
    return (
      <Navigate
        to={loginPath}
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  }

  // 2. Tier guard
  if (policy.requiredTier && !canAccessRoute(policy.requiredTier)) {
    log.warn("Tier access denied", {
      requiredTier: policy.requiredTier,
      path: location.pathname,
    });
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  // 3. Tenant membership guard
  if (policy.tenantScoped && tenantSlug) {
    if (tenantLoading) return <RouteGuardSkeleton />;
    if (!isMemberOfTenant) {
      log.warn("Tenant access denied", {
        tenantSlug,
        path: location.pathname,
      });
      return <Navigate to="/home" replace />;
    }
  }

  // 4. Account access guard
  if (policy.accountScoped && accountId) {
    if (accountLoading) return <RouteGuardSkeleton />;
    if (!hasAccountAccess) {
      log.warn("Account access denied", { accountId, path: location.pathname });
      return (
        <Navigate to={`/t/${tenantSlug}/accounts`} replace />
      );
    }
  }

  // 5. Role/permission guard
  if (policy.requiredPermissions && policy.requiredPermissions.length > 0) {
    if (permLoading) return <RouteGuardSkeleton />;
    if (!hasPermissions) {
      log.warn("Permission denied", {
        permissions: policy.requiredPermissions,
        path: location.pathname,
      });
      return <Navigate to={policy.fallbackRoute} replace />;
    }
  }

  // 6. Feature flag guard
  if (policy.requiredFeatureFlags && policy.requiredFeatureFlags.length > 0) {
    if (!flagsEnabled) {
      log.warn("Feature not enabled", {
        flags: policy.requiredFeatureFlags,
        path: location.pathname,
      });
      return <Navigate to={policy.fallbackRoute} replace />;
    }
  }

  // 7. Plan/entitlement guard
  if (policy.requiredEntitlements && policy.requiredEntitlements.length > 0) {
    if (entitlementsLoading) return <RouteGuardSkeleton />;
    if (!entitlementsMet) {
      log.warn("Entitlement not met", {
        entitlements: policy.requiredEntitlements,
        path: location.pathname,
      });
      return <Navigate to="/home" replace />;
    }
  }

  return <ErrorBoundary>{children}</ErrorBoundary>;
}

function ClerkUnifiedRouteGuard(props: UnifiedRouteGuardProps) {
  const { isLoaded, isSignedIn } = useClerkAuth();
  // Only rendered when Clerk is enabled and <ClerkProvider> is mounted (see
  // UnifiedRouteGuard below), so the Clerk membership hook is safe here.
  const { tenantSlug } = useParams();
  const tenantMembership = useTenantMembershipClerk(tenantSlug);

  return (
    <UnifiedRouteGuardInner
      {...props}
      authStateOverride={{
        isLoading: !isLoaded,
        isAuthenticated: isLoaded && !!isSignedIn,
      }}
      tenantMembershipOverride={tenantMembership}
    />
  );
}

export function UnifiedRouteGuard(props: UnifiedRouteGuardProps) {
  if (isClerkAuthEnabled()) {
    return <ClerkUnifiedRouteGuard {...props} />;
  }

  return <UnifiedRouteGuardInner {...props} />;
}

function RouteGuardSkeleton() {
  return (
    <div className="flex h-full min-h-[400px] items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
        <p className="text-sm text-muted-foreground">Verifying access...</p>
      </div>
    </div>
  );
}
