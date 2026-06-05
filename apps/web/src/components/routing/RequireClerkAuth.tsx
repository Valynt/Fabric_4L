/**
 * <RequireClerkAuth /> — Phase 2 route guard layered on top of the legacy
 * <ProtectedRoute />.
 *
 * Behavior:
 *   - When AUTH_PROVIDER=legacy: renders children unconditionally. The
 *     existing <ProtectedRoute /> guards remain authoritative, so this
 *     component is a no-op and zero-risk to add to existing routes.
 *   - When AUTH_PROVIDER=clerk:
 *       - If Clerk is still loading, render nothing (null) to prevent any
 *         protected UI from flashing on screen.
 *       - If the user is not signed in, redirect to the configured sign-in
 *         URL with the original location preserved. The redirect happens
 *         synchronously via useLayoutEffect before the browser paints.
 *       - If the user has no active organization (and the route requires
 *         one), redirect to the org-picker page.
 *
 * Tenant authority remains server-side: the gateway always trusts the
 * verified Fabric4L envelope, never anything from the browser.
 */
import { useAuth, useOrganization } from "@clerk/react";
import { useNavigate, useLocation } from "react-router-dom";
import { useLayoutEffect, useRef, type ReactNode } from "react";

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
  const hasNavigated = useRef(false);

  if (requireOrganization && !orgLoaded) {
    // Render nothing while org state loads to prevent UI flash
    return null;
  }

  useLayoutEffect(() => {
    if (requireOrganization && !organization && !hasNavigated.current) {
      hasNavigated.current = true;
      navigate(urls.selectOrgUrl, { replace: true });
    }
  }, [requireOrganization, organization, navigate, urls.selectOrgUrl]);

  if (requireOrganization && !organization) {
    // Redirect in progress — render nothing to prevent UI flash
    return null;
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
  const hasNavigated = useRef(false);

  // DEBUG: log auth state
  // eslint-disable-next-line no-console
  console.log('[RequireClerkAuth]', { path: location.pathname, authLoaded, isSignedIn });

  // Redirect synchronously before paint to prevent ANY protected UI from flashing.
  // useLayoutEffect runs after DOM mutations but before the browser paints,
  // so the user never sees the protected route content.
  useLayoutEffect(() => {
    // eslint-disable-next-line no-console
    console.log('[RequireClerkAuth] useLayoutEffect', { path: location.pathname, authLoaded, isSignedIn, hasNavigated: hasNavigated.current });
    if (authLoaded && !isSignedIn && !hasNavigated.current) {
      hasNavigated.current = true;
      const redirectTo = `${urls.signInUrl}?redirect_url=${encodeURIComponent(
        location.pathname + location.search,
      )}`;
      // eslint-disable-next-line no-console
      console.log('[RequireClerkAuth] navigating to', redirectTo);
      navigate(redirectTo, { replace: true });
    }
  }, [authLoaded, isSignedIn, navigate, urls.signInUrl, location.pathname, location.search]);

  // While Clerk is still loading OR the user is not signed in (redirect pending),
  // render absolutely nothing. This guarantees zero UI flash.
  if (!authLoaded || !isSignedIn) {
    return null;
  }

  return (
    <RequireClerkAuthOrgCheck requireOrganization={requireOrganization}>
      {children}
    </RequireClerkAuthOrgCheck>
  );
}

export function RequireClerkAuth(props: RequireClerkAuthProps) {
  // eslint-disable-next-line no-console
  console.log('[RequireClerkAuth] render', { clerkEnabled: isClerkAuthEnabled() });
  // No-op under legacy auth — let downstream <ProtectedRoute /> own the gate.
  if (!isClerkAuthEnabled()) {
    return <>{props.children}</>;
  }
  return <RequireClerkAuthInner {...props} />;
}
