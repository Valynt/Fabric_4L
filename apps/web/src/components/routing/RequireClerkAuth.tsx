/**
 * <RequireClerkAuth /> — Phase 2 route guard layered on top of the legacy
 * <ProtectedRoute />.
 *
 * Behavior:
 *   - When AUTH_PROVIDER=legacy: renders children unconditionally. The
 *     existing <ProtectedRoute /> guards remain authoritative, so this
 *     component is a no-op and zero-risk to add to existing routes.
 *   - When AUTH_PROVIDER=clerk:
 *       - If Clerk is still loading, render a small spinner.
 *       - If the user is not signed in, redirect to the configured sign-in
 *         URL with the original location preserved.
 *       - If the user has no active organization (and the route requires
 *         one), redirect to the org-picker page.
 *
 * Tenant authority remains server-side: the gateway always trusts the
 * verified Fabric4L envelope, never anything from the browser.
 */
import { useAuth, useOrganization } from "@clerk/react";
import { useNavigate, useLocation } from "react-router-dom";
import { useEffect, type ReactNode } from "react";

import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

interface RequireClerkAuthProps {
  children: ReactNode;
  /**
   * When true (default), users must have an active Clerk organization. Set
   * to false for routes that are valid before an org is selected (e.g. the
   * org picker itself).
   */
  requireOrganization?: boolean;
}

function ClerkLoadingFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex h-full min-h-[400px] items-center justify-center"
    >
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
        <p className="text-sm text-muted-foreground">Verifying session...</p>
      </div>
    </div>
  );
}

function RequireClerkAuthOrgCheck({
  children,
  requireOrganization,
}: {
  children: ReactNode;
  requireOrganization: boolean;
}) {
  const navigate = useNavigate();
  const urls = getClerkUrls();
  const { isLoaded: orgLoaded, organization } = useOrganization();

  if (requireOrganization && !orgLoaded) {
    return <ClerkLoadingFallback />;
  }

  useEffect(() => {
    if (requireOrganization && !organization) {
      navigate(urls.selectOrgUrl, { replace: true });
    }
  }, [requireOrganization, organization, navigate, urls.selectOrgUrl]);

  if (requireOrganization && !organization) {
    return <ClerkLoadingFallback />;
  }

  return <>{children}</>;
}

function RequireClerkAuthInner({
  children,
  requireOrganization = true,
}: RequireClerkAuthProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const urls = getClerkUrls();
  const { isLoaded: authLoaded, isSignedIn } = useAuth();

  if (!authLoaded) {
    return <ClerkLoadingFallback />;
  }

  useEffect(() => {
    if (!isSignedIn) {
      const redirectTo = `${urls.signInUrl}?redirect_url=${encodeURIComponent(
        location.pathname + location.search,
      )}`;
      navigate(redirectTo, { replace: true });
    }
  }, [isSignedIn, navigate, urls.signInUrl, location.pathname, location.search]);

  if (!isSignedIn) {
    return <ClerkLoadingFallback />;
  }

  return (
    <RequireClerkAuthOrgCheck requireOrganization={requireOrganization}>
      {children}
    </RequireClerkAuthOrgCheck>
  );
}

export function RequireClerkAuth(props: RequireClerkAuthProps) {
  // No-op under legacy auth — let downstream <ProtectedRoute /> own the gate.
  if (!isClerkAuthEnabled()) {
    return <>{props.children}</>;
  }
  return <RequireClerkAuthInner {...props} />;
}
