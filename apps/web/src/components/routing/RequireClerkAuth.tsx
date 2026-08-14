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
import { useLocation } from "react-router-dom";
import { useNavigation } from "@/hooks/useNavigation";
import { useLayoutEffect, useRef, type ReactNode } from "react";

import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";

interface RequireClerkAuthProps {
  children: ReactNode;
  /**
   * When true (default), users must have an active Clerk organization. Set
   * to false for routes that are valid before an org is selected (e.g. the
   * org picker itself).
   */
  requireOrganization?: boolean;
}

function buildSafeRedirectPath(pathname: string, search: string): string {
  if (!search) {
    return pathname;
  }

  const params = new URLSearchParams(search);
  const keysToDelete: string[] = [];
  params.forEach((_value, key) => {
    if (key.toLowerCase().startsWith("__clerk_")) {
      keysToDelete.push(key);
    }
  });
  keysToDelete.forEach(key => params.delete(key));

  const normalized = params.toString();
  return normalized ? `${pathname}?${normalized}` : pathname;
}

function RequireClerkAuthOrgCheck({
  children,
  requireOrganization,
}: {
  children: ReactNode;
  requireOrganization: boolean;
}) {
  const { navigateTo } = useNavigation();
  const location = useLocation();
  const urls = getClerkUrls();
  // This component is only rendered behind the <RequireClerkAuth> gate, which
  // guarantees Clerk is enabled and <ClerkProvider> is mounted. Hooks may be
  // called unconditionally here.
  const { isLoaded: orgLoaded, organization } = useOrganization();
  const authorization = useAuthorizationSnapshot();
  const hasNavigated = useRef(false);

  // All hooks must run on every render before any conditional return, so the
  // redirect effect is registered before the loading/redirect short-circuits
  // below (orgLoaded transitions false→true as Clerk loads).
  useLayoutEffect(() => {
    if (
      requireOrganization &&
      orgLoaded &&
      !organization &&
      !hasNavigated.current
    ) {
      hasNavigated.current = true;
      navigateTo(urls.selectOrgUrl, { replace: true });
    }
  }, [
    requireOrganization,
    orgLoaded,
    organization,
    navigateTo,
    urls.selectOrgUrl,
  ]);

  useLayoutEffect(() => {
    if (
      !requireOrganization ||
      !orgLoaded ||
      !organization ||
      authorization.status !== "denied" ||
      hasNavigated.current
    ) {
      return;
    }
    hasNavigated.current = true;
    navigateTo("forbidden", undefined, {
      query: { wfStep: "0" },
      replace: true,
    });
  }, [
    authorization.status,
    orgLoaded,
    organization,
    requireOrganization,
    navigateTo,
  ]);

  if (requireOrganization && !orgLoaded) {
    // Render nothing while org state loads to prevent UI flash
    return null;
  }

  if (requireOrganization && !organization) {
    // Redirect in progress — render nothing to prevent UI flash
    return null;
  }

  if (requireOrganization && authorization.status === "loading") {
    // Render nothing while the backend resolves the authorization snapshot.
    return null;
  }

  if (requireOrganization && authorization.status !== "verified") {
    // Redirect in progress; the effect above decides the destination.
    return null;
  }

  return <>{children}</>;
}

function RequireClerkAuthInner({
  children,
  requireOrganization = true,
}: RequireClerkAuthProps) {
  const { navigateTo } = useNavigation();
  const location = useLocation();
  const urls = getClerkUrls();
  // This component is only rendered behind the <RequireClerkAuth> gate, which
  // guarantees Clerk is enabled and <ClerkProvider> is mounted. Hooks may be
  // called unconditionally here.
  const { isLoaded: authLoaded, isSignedIn } = useAuth();
  const hasNavigated = useRef(false);

  // Redirect synchronously before paint to prevent ANY protected UI from flashing.
  // useLayoutEffect runs after DOM mutations but before the browser paints,
  // so the user never sees the protected route content.
  useLayoutEffect(() => {
    if (authLoaded && !isSignedIn && !hasNavigated.current) {
      hasNavigated.current = true;
      const safeCurrentPath = buildSafeRedirectPath(
        location.pathname,
        location.search
      );
      const redirectTo = `${urls.signInUrl}?redirect_url=${encodeURIComponent(
        safeCurrentPath
      )}`;
      navigateTo(redirectTo, { replace: true });
    }
  }, [
    authLoaded,
    isSignedIn,
    navigateTo,
    urls.signInUrl,
    location.pathname,
    location.search,
  ]);

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
  // No-op under legacy auth — let downstream <ProtectedRoute /> own the gate.
  if (!isClerkAuthEnabled()) {
    return <>{props.children}</>;
  }
  return <RequireClerkAuthInner {...props} />;
}
