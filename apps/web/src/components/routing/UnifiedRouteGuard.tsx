import { Navigate, useLocation, useParams, useMatches } from "react-router-dom";
import { useAuth as useClerkAuth } from "@clerk/react";
import { useAuthContext } from "@/contexts/AuthContext";
import { useTenantMembership } from "@/hooks/useTenantMembership";
import { useAccountAccess } from "@/hooks/useAccountAccess";
import { useUserPermissions } from "@/hooks/useUserPermissions";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { useEntitlements } from "@/hooks/useEntitlements";
import { type RouteAccessPolicy } from "@/routes/types";
import { ErrorBoundary } from "@/components";
import { createFeatureLogger } from "@/lib/telemetry";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";

const log = createFeatureLogger("route-guard");

interface UnifiedRouteGuardProps {
  children: React.ReactNode;
}

export function UnifiedRouteGuard({ children }: UnifiedRouteGuardProps) {
  const location = useLocation();
  const params = useParams();
  const matches = useMatches();
  const { isAuthenticated: legacyIsAuthenticated, isLoading: legacyIsLoading } = useAuthContext();

  // Phase 2: Clerk integration — when Clerk is the auth provider, derive auth
  // state from Clerk's useAuth() hook so the guard works for both legacy and
  // Clerk-driven sessions.
  const clerkEnabled = isClerkAuthEnabled();
  const { isLoaded: clerkLoaded, isSignedIn } = useClerkAuth();
  const isAuthenticated = clerkEnabled ? (clerkLoaded && !!isSignedIn) : legacyIsAuthenticated;
  const isLoading = clerkEnabled ? !clerkLoaded : legacyIsLoading;
  const loginPath = clerkEnabled ? "/sign-in" : "/login";

  // Walk up the match tree to find the most specific access policy
  const policy = matches
    .map((m) => (m.handle as Record<string, unknown> | undefined)?.accessPolicy as RouteAccessPolicy | undefined)
    .filter(Boolean)
    .pop();

  if (!policy) {
    return <ErrorBoundary>{children}</ErrorBoundary>;
  }

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

  // 2. Tenant membership guard
  const tenantSlug = params.tenantSlug;
  const { isMemberOfTenant, isLoading: tenantLoading } =
    useTenantMembership(tenantSlug);

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

  // 3. Account access guard
  const accountId = params.accountId;
  const { hasAccountAccess, isLoading: accountLoading } =
    useAccountAccess(accountId, tenantSlug);

  if (policy.accountScoped && accountId) {
    if (accountLoading) return <RouteGuardSkeleton />;
    if (!hasAccountAccess) {
      log.warn("Account access denied", { accountId, path: location.pathname });
      return (
        <Navigate to={`/t/${tenantSlug}/accounts`} replace />
      );
    }
  }

  // 4. Role/permission guard
  const { hasPermissions, isLoading: permLoading } = useUserPermissions(
    policy.requiredPermissions ?? []
  );
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

  // 5. Feature flag guard
  const { flagsEnabled } = useFeatureFlags(
    policy.requiredFeatureFlags ?? []
  );
  if (policy.requiredFeatureFlags && policy.requiredFeatureFlags.length > 0) {
    if (!flagsEnabled) {
      log.warn("Feature not enabled", {
        flags: policy.requiredFeatureFlags,
        path: location.pathname,
      });
      return <Navigate to={policy.fallbackRoute} replace />;
    }
  }

  // 6. Plan/entitlement guard
  const { entitlementsMet } = useEntitlements(
    policy.requiredEntitlements ?? []
  );
  if (policy.requiredEntitlements && policy.requiredEntitlements.length > 0) {
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
