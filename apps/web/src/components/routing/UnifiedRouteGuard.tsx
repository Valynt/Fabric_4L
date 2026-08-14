import { Navigate, useLocation, useParams, useMatches } from "react-router-dom";
import { useAuthContext } from "@/contexts/AuthContext";
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
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

function UnifiedRouteGuardInner({ children }: UnifiedRouteGuardProps) {
  const location = useLocation();
  const params = useParams();
  const matches = useMatches();

  // Derive auth state from the app's AuthContext, which is the single source of
  // truth for both Clerk and mock/dev mode (VITE_ENABLE_MOCK_AUTH). Calling Clerk's
  // useAuth() directly here would hang on "Verifying access..." in mock mode because
  // Clerk never finishes loading without a real publishable key/session.
  const authContext = useAuthContext();
  const { isAuthenticated, isLoading } = authContext;
  const loginPath = "/sign-in";

  // Walk up the match tree to find the most specific access policy
  const policy =
    matches
      .flatMap(m => {
        const p = (m.handle as Record<string, unknown> | undefined)
          ?.accessPolicy as RouteAccessPolicy | undefined;
        return p ? [p] : [];
      })
      .pop() ?? FAIL_CLOSED_ACCESS_POLICY;

  // ALL hooks must be called before any conditional return (Rules of Hooks).
  // Use optional chaining so hooks are unconditionally invoked even when policy
  // is undefined; the conditional guard logic below still short-circuits safely.
  const authorization = useAuthorizationSnapshot();

  const tenantSlug = params.tenantSlug;
  // Legacy (AuthContext) membership is always resolved here; in Clerk mode the
  // outer ClerkUnifiedRouteGuard supplies a Clerk-derived override, mirroring
  // authStateOverride, so Clerk hooks never run without <ClerkProvider>.
  const accountId = params.accountId;

  const { flagsEnabled } = useFeatureFlags(policy?.requiredFeatureFlags ?? []);

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
  if (policy.requiresAuth && authorization.status === "loading") {
    return <RouteGuardSkeleton />;
  }
  if (policy.requiresAuth && authorization.status !== "verified") {
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  if (
    policy.requiredTier &&
    !authorization.hasEveryPermission([`tier:${policy.requiredTier}:access`])
  ) {
    log.warn("Tier access denied", {
      requiredTier: policy.requiredTier,
      path: location.pathname,
    });
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  // 3. Tenant membership guard
  if (policy.tenantScoped && tenantSlug) {
    if (!authorization.hasTenantMembership(tenantSlug)) {
      log.warn("Tenant access denied", {
        tenantSlug,
        path: location.pathname,
      });
      return <Navigate to="/home" replace />;
    }
  }

  // 4. Account access guard
  if (policy.accountScoped && accountId) {
    if (!authorization.hasAccountAccess(accountId)) {
      log.warn("Account access denied", { accountId, path: location.pathname });
      return <Navigate to={`/t/${tenantSlug}/accounts`} replace />;
    }
  }

  // 5. Role/permission guard
  if (policy.requiredPermissions && policy.requiredPermissions.length > 0) {
    if (!authorization.hasEveryPermission(policy.requiredPermissions)) {
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
    if (!authorization.hasEveryEntitlement(policy.requiredEntitlements)) {
      log.warn("Entitlement not met", {
        entitlements: policy.requiredEntitlements,
        path: location.pathname,
      });
      return <Navigate to="/home" replace />;
    }
  }

  return <ErrorBoundary>{children}</ErrorBoundary>;
}

export function UnifiedRouteGuard(props: UnifiedRouteGuardProps) {
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
