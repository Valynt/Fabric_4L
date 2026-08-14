import { Navigate, useLocation, useMatches, useParams } from "react-router-dom";
import { useAuth as useClerkAuth } from "@clerk/react";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { decideAuthorization } from "@/auth/authorizationSnapshot";
import { useAuthContext } from "@/contexts/AuthContext";
import { useAuthorizationSnapshot } from "@/hooks/useAuthorizationSnapshot";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import type { RouteAccessPolicy } from "@/routes/types";
import { ErrorBoundary } from "@/components";

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

function Guard({
  children,
  fallback,
  clerkAuth,
}: UnifiedRouteGuardProps & {
  clerkAuth?: { isLoaded: boolean; isSignedIn?: boolean };
}) {
  const location = useLocation();
  const params = useParams();
  const matches = useMatches();
  const legacy = useAuthContext();
  const isLoading = clerkAuth ? !clerkAuth.isLoaded : legacy.isLoading;
  const isAuthenticated = clerkAuth
    ? clerkAuth.isLoaded && Boolean(clerkAuth.isSignedIn)
    : legacy.isAuthenticated;
  const policy =
    matches
      .flatMap(match => {
        const value = (match.handle as Record<string, unknown> | undefined)
          ?.accessPolicy as RouteAccessPolicy | undefined;
        return value ? [value] : [];
      })
      .pop() ?? FAIL_CLOSED_ACCESS_POLICY;
  const resolution = useAuthorizationSnapshot(
    params.tenantSlug ?? legacy.currentTenantSlug ?? undefined
  );
  const { flagsEnabled } = useFeatureFlags(policy.requiredFeatureFlags ?? []);
  const decision = decideAuthorization(
    resolution,
    {
      permissions: policy.requiredPermissions,
      entitlements: policy.requiredEntitlements,
      tenantMember: policy.tenantScoped,
      accountId: policy.accountScoped ? params.accountId : undefined,
    },
    flagsEnabled
  );

  if (isLoading) return <VerificationState />;
  if (policy.requiresAuth && !isAuthenticated) {
    return (
      <Navigate
        to="/sign-in"
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  }
  if (decision.status === "loading") return <VerificationState />;
  if (decision.status === "expired") return <ExpiredState />;
  if (decision.status === "denied")
    return (
      <>
        {fallback ?? (
          <AccessDeniedState
            attemptedUrl={location.pathname + location.search}
          />
        )}
      </>
    );
  return <ErrorBoundary>{children}</ErrorBoundary>;
}

function ClerkGuard(props: UnifiedRouteGuardProps) {
  const auth = useClerkAuth();
  return <Guard {...props} clerkAuth={auth} />;
}

export function UnifiedRouteGuard(props: UnifiedRouteGuardProps) {
  return isClerkAuthEnabled() ? (
    <ClerkGuard {...props} />
  ) : (
    <Guard {...props} />
  );
}

function VerificationState() {
  return (
    <div
      className="flex min-h-[400px] items-center justify-center"
      role="status"
    >
      Verifying access...
    </div>
  );
}

function AccessDeniedState({ attemptedUrl }: { attemptedUrl: string }) {
  return (
    <div
      className="flex min-h-[400px] flex-col items-center justify-center"
      data-attempted-url={attemptedUrl}
    >
      <h1>Access denied</h1>
      <p>You do not have access to this resource.</p>
    </div>
  );
}

function ExpiredState() {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center">
      <h1>Session expired</h1>
      <p>Sign in again to continue.</p>
    </div>
  );
}
