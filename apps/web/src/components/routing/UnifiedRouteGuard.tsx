import { Navigate, useLocation, useMatches, useParams } from "react-router-dom";
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";
import { ErrorBoundary } from "@/components";
import { useAuthContext } from "@/contexts/AuthContext";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { createFeatureLogger } from "@/lib/telemetry";
import { type RouteAccessPolicy } from "@/routes/types";

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

export function UnifiedRouteGuard({ children }: UnifiedRouteGuardProps) {
  const location = useLocation();
  const { tenantSlug, accountId } = useParams();
  const matches = useMatches();
  const { isAuthenticated, isLoading: authLoading } = useAuthContext();
  const authorization = useAuthorizationSnapshot();

  const policy =
    matches
      .flatMap(match => {
        const accessPolicy = (
          match.handle as Record<string, unknown> | undefined
        )?.accessPolicy as RouteAccessPolicy | undefined;
        return accessPolicy ? [accessPolicy] : [];
      })
      .pop() ?? FAIL_CLOSED_ACCESS_POLICY;

  // Feature flags are presentation controls only. They are evaluated after the
  // verified snapshot and can restrict access, never grant it.
  const { flagsEnabled } = useFeatureFlags(
    policy.requiredFeatureFlags ?? []
  );

  if (authLoading) {
    return <RouteGuardLoading />;
  }

  if (policy.requiresAuth && !isAuthenticated) {
    return (
      <Navigate
        to="/sign-in"
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  }

  const requiresVerifiedAuthorization =
    policy.tenantScoped ||
    policy.accountScoped ||
    !!policy.requiredPermissions?.length ||
    !!policy.requiredEntitlements?.length;

  if (requiresVerifiedAuthorization && authorization.status === "loading") {
    return <RouteGuardLoading />;
  }

  if (requiresVerifiedAuthorization && authorization.status !== "verified") {
    if (
      authorization.status === "denied" &&
      authorization.reason === "unavailable"
    ) {
      return <RouteGuardError />;
    }

    log.warn("Verified authorization unavailable", {
      authorizationStatus: authorization.status,
      path: location.pathname,
    });
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  if (
    policy.tenantScoped &&
    (!tenantSlug || !authorization.hasTenantMembership(tenantSlug))
  ) {
    log.warn("Tenant scope denied", {
      tenantSlug,
      path: location.pathname,
    });
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  if (
    policy.accountScoped &&
    (!accountId || !authorization.hasAccountAccess(accountId))
  ) {
    log.warn("Account scope denied", {
      accountId,
      path: location.pathname,
    });
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  if (
    policy.requiredPermissions?.length &&
    !authorization.hasEveryPermission(policy.requiredPermissions)
  ) {
    log.warn("Permission denied", {
      permissions: policy.requiredPermissions,
      path: location.pathname,
    });
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  if (
    policy.requiredEntitlements?.length &&
    !authorization.hasEveryEntitlement(policy.requiredEntitlements)
  ) {
    log.warn("Entitlement denied", {
      entitlements: policy.requiredEntitlements,
      path: location.pathname,
    });
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  if (policy.requiredFeatureFlags?.length && !flagsEnabled) {
    log.warn("Feature restricted", {
      flags: policy.requiredFeatureFlags,
      path: location.pathname,
    });
    return <Navigate to={policy.fallbackRoute} replace />;
  }

  return <ErrorBoundary>{children}</ErrorBoundary>;
}

function RouteGuardLoading() {
  return (
    <div className="flex h-full min-h-[400px] items-center justify-center">
      <div className="flex flex-col items-center gap-3" role="status">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
        <p className="text-sm text-muted-foreground">Verifying access...</p>
      </div>
    </div>
  );
}

function RouteGuardError() {
  return (
    <div
      className="flex h-full min-h-[400px] items-center justify-center"
      role="alert"
    >
      <p className="text-sm text-destructive">
        Unable to verify access. Please try again.
      </p>
    </div>
  );
}
