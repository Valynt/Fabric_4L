/**
 * <ClerkAuthBridge /> — keeps non-React modules in sync with Clerk.
 *
 * Responsibilities:
 *   1. Push the live Clerk `getToken` into the API client interceptor via
 *      `setClerkTokenGetter`.
 *   2. Track the active organization id and expose it to the API client
 *      via `setActiveClerkOrgId` (used internally by tests/diagnostics only;
 *      the gateway never trusts a browser-asserted tenant).
 *   3. On unmount, clear BOTH the token getter AND the active org id so no
 *      stale closures or org ids leak across HMR reloads, layout swaps,
 *      or sign-out flows.
 *
 * Race avoidance: Clerk's `useAuth().getToken` reference identity can churn
 * across renders. To prevent a brief null-getter window between effect
 * cleanup and re-registration, we register ONCE on first authenticated
 * mount and route through a stable ref. The effect re-runs only on
 * sign-in / sign-out transitions, not on every render.
 *
 * This component renders nothing. Mount it once near the root, inside
 * the ClerkProvider and AuthProvider.
 */
import { useEffect, useRef } from "react";
import { useAuth, useOrganization } from "@clerk/react";

import { setActiveClerkOrgId, setClerkTokenGetter } from "@/auth/clerkSession";

const FABRIC_AUTH_TEMPLATE_NAME =
  (import.meta.env.VITE_CLERK_JWT_TEMPLATE ?? "").toString().trim() || undefined;

export function ClerkAuthBridge(): null {
  const { isLoaded: authLoaded, isSignedIn, getToken } = useAuth();
  const { organization } = useOrganization();

  // Stable ref that always points at the latest Clerk getToken closure.
  // The registered token getter reads through this ref, so identity churn
  // on `getToken` does NOT cause us to unregister/re-register and never
  // leaves a null-getter race window.
  const getTokenRef = useRef(getToken);
  getTokenRef.current = getToken;

  // 1) Register the token getter on first authenticated mount; clear on
  //    sign-out and on unmount. We intentionally depend only on the
  //    boolean transitions, not on `getToken` identity.
  useEffect(() => {
    if (!authLoaded) return;
    if (!isSignedIn) {
      setClerkTokenGetter(null);
      return;
    }

    // Register the new getter immediately
    setClerkTokenGetter(async (options) => {
      const template = options?.template ?? FABRIC_AUTH_TEMPLATE_NAME;
      // Read the latest getToken via ref so re-renders never see a stale
      // closure and we never deregister mid-flight.
      const currentGetToken = getTokenRef.current;
      return currentGetToken({
        template,
        skipCache: options?.skipCache,
      });
    });

    // Effect cleanup runs on sign-in→sign-out transitions AND on unmount.
    // In either case we MUST drop the getter so a stale closure cannot
    // mint a Bearer header for a no-longer-signed-in session.
    return () => {
      setClerkTokenGetter(null);
    };
  }, [authLoaded, isSignedIn]);

  // 2) Track active org. Clear on unmount so HMR / layout swaps do not
  //    leak a stale org id into the module-scope bridge state.
  useEffect(() => {
    setActiveClerkOrgId(organization?.id ?? null);
    return () => {
      setActiveClerkOrgId(null);
    };
  }, [organization?.id]);

  return null;
}
