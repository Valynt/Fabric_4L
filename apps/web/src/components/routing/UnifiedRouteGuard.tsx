import { Navigate, useLocation, useMatches, useParams } from "react-router-dom";
import { useAuth as useClerkAuth } from "@clerk/react";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { useAuthContext } from "@/contexts/AuthContext";
import { useUserPermissions } from "@/hooks/useUserPermissions";
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
  fallback?: React.ReactNode;
}

interface RouteGuardAuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
}

function UnifiedRouteGuardInner({
  children,
  fallback,
  authStateOverride,
}: UnifiedRouteGuardProps & { authStateOverride?: RouteGuardAuthState }) {
  const location = useLocation();
  const params = useParams();
  const matches = useMatches();
  const authContext = useAuthContext();
  const { isAuthenticated, isLoading } = authStateOverride ?? authContext;
  const policy =
    matches
      .flatMap(match => {
        const candidate = (match.handle as Record<string, unknown> | undefined)
          ?.accessPolicy as RouteAccessPolicy | undefined;
        return candidate ? [candidate] : [];
      })
      .pop() ?? FAIL_CLOSED_ACCESS_POLICY;

  const permissionResult = useUserPermissions(
    policy.requiredPermissions ?? [],
    params.tenantSlug
  );
  const { flagsEnabled } = useFeatureFlags(policy.requiredFeatureFlags ?? []);
  const { decision, snapshot } = permissionResult;

  if (isLoading) return <RouteGuardSkeleton />;
  if (policy.requiresAuth && !isAuthenticated) {
    return (
      <Navigate
        to="/sign-in"
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  }
  if (decision.status === "loading") return <RouteGuardSkeleton />;
  if (decision.status === "expired") return <ExpiredAuthorizationState />;
  if (decision.status === "denied") {
    log.warn("Snapshot authorization denied", {
      reason: decision.reason,
      path: location.pathname,
    });
    return <>{fallback ?? <AccessDeniedState />}</>;
  }

  // All route scope and entitlement checks use the same verified snapshot.
  if (snapshot.status !== "verified")
    return <>{fallback ?? <AccessDeniedState />}</>;
  const authorized =
    (!policy.tenantScoped || snapshot.snapshot.tenantMember) &&
    (!policy.accountScoped ||
      (Boolean(params.accountId) &&
        snapshot.snapshot.accountIds.includes(params.accountId ?? ""))) &&
    (policy.requiredEntitlements ?? []).every(key =>
      snapshot.entitlements.includes(key)
    );

  // Feature flags are deliberately separate and may only further restrict a
  // snapshot-authorized route: featureEnabled && snapshotAuthorized.
  if (!authorized || !flagsEnabled) {
    return <>{fallback ?? <AccessDeniedState />}</>;
  }
  return <ErrorBoundary>{children}</ErrorBoundary>;
}

function ClerkUnifiedRouteGuard(props: UnifiedRouteGuardProps) {
  const { isLoaded, isSignedIn } = useClerkAuth();
  return (
    <UnifiedRouteGuardInner
      {...props}
      authStateOverride={{
        isLoading: !isLoaded,
        isAuthenticated: isLoaded && !!isSignedIn,
      }}
    />
  );
}

export function UnifiedRouteGuard(props: UnifiedRouteGuardProps) {
  return isClerkAuthEnabled() ? (
    <ClerkUnifiedRouteGuard {...props} />
  ) : (
    <UnifiedRouteGuardInner {...props} />
  );
}

function RouteGuardSkeleton() {
  return (
    <div
      className="flex h-full min-h-[400px] items-center justify-center"
      role="status"
    >
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
        <p className="text-sm text-muted-foreground">Verifying access...</p>
      </div>
    </div>
  );
}

function AccessDeniedState() {
  return (
    <div className="flex min-h-[400px] items-center justify-center px-6">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold text-foreground">Access denied</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your verified access does not include this resource. Contact your
          workspace administrator if you believe this is an error.
        </p>
      </div>
    </div>
  );
}

function ExpiredAuthorizationState() {
  return (
    <div className="flex min-h-[400px] items-center justify-center px-6">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold text-foreground">
          Session verification expired
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          We could not refresh your access. Sign in again to continue.
        </p>
        <a
          className="mt-4 inline-flex text-sm font-medium text-primary underline-offset-4 hover:underline"
          href="/sign-in"
        >
          Sign in again
        </a>
      </div>
    </div>
  );
}
