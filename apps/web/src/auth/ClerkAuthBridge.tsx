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
import {
  Fragment,
  useEffect,
  useLayoutEffect,
  useRef,
  type ReactElement,
  type ReactNode,
} from "react";
import { useAuth, useOrganization } from "@clerk/react";
import { useQueryClient } from "@tanstack/react-query";

import { setActiveClerkOrgId, setClerkTokenGetter } from "@/auth/clerkSession";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import clerkDefaults from "@fabric/platform-contract/clerk-defaults";

const FABRIC_AUTH_TEMPLATE_NAME =
  (import.meta.env.VITE_CLERK_JWT_TEMPLATE ?? clerkDefaults.clerk.jwtTemplate)
    .toString()
    .trim() || undefined;

function OrgSync({
  resetAccountContext,
}: {
  resetAccountContext: () => void;
}): null {
  // OrgSync is only rendered from <ClerkAuthBridge> after its isClerkAuthEnabled()
  // gate and an isSignedIn check, so <ClerkProvider> is guaranteed to be mounted
  // and the hook may be called unconditionally.
  const { organization } = useOrganization();
  const queryClient = useQueryClient();

  const resetAccountContextRef = useRef(resetAccountContext);
  resetAccountContextRef.current = resetAccountContext;
  const previousOrgIdRef = useRef(organization?.id ?? null);

  useLayoutEffect(() => {
    const nextOrgId = organization?.id ?? null;
    if (previousOrgIdRef.current !== nextOrgId) {
      resetAccountContextRef.current();
      previousOrgIdRef.current = nextOrgId;
    }
    setActiveClerkOrgId(nextOrgId);
    // Tenant/org switch: do not reuse any cached account or tenant-scoped data
    // from the previous organization. The gateway is the authority, but this
    // prevents the frontend from momentarily displaying stale data.
    queryClient.invalidateQueries();
    return () => {
      setActiveClerkOrgId(null);
    };
  }, [organization?.id, queryClient]);

  return null;
}

interface ClerkAuthBridgeProps {
  children?: ReactNode;
}

export function ClerkAuthBridge({
  children = null,
}: ClerkAuthBridgeProps = {}): ReactElement | null {
  // Legacy auth path: do not call Clerk hooks because <ClerkProvider> is not
  // mounted. The Clerk-enabled bridge lives in a separate component selected
  // by this flag so hook calls inside it stay unconditional (rules-of-hooks).
  if (!isClerkAuthEnabled()) {
    return <>{children}</>;
  }

  return <ClerkAuthBridgeClerk>{children}</ClerkAuthBridgeClerk>;
}

function ClerkAuthBridgeClerk({
  children = null,
}: ClerkAuthBridgeProps): ReactElement | null {
  const { isLoaded: authLoaded, isSignedIn, getToken } = useAuth();
  const authorizationIdentityChanged = useAccountContextStore(
    s => s.authorizationIdentityChanged
  );
  const previousSignedInRef = useRef(isSignedIn);

  useLayoutEffect(() => {
    if (previousSignedInRef.current !== isSignedIn) {
      authorizationIdentityChanged();
      previousSignedInRef.current = isSignedIn;
    }
  }, [authLoaded, isSignedIn, authorizationIdentityChanged]);

  // Stable ref that always points at the latest Clerk getToken closure.
  // The registered token getter reads through this ref, so identity churn
  // on `getToken` does NOT cause us to unregister/re-register and never
  // leaves a null-getter race window.
  const getTokenRef = useRef(getToken);
  // Keep the ref current from an effect (never mutate a ref during render).
  // Declared before the registration effect below so it runs first on every
  // commit; the registered getter only reads the ref at call time, so stale
  // closures are impossible and no null-getter race window opens.
  useEffect(() => {
    getTokenRef.current = getToken;
  });

  // 1) Register the token getter on first authenticated mount; clear on
  //    sign-out and on unmount. We intentionally depend only on the
  //    boolean transitions, not on `getToken` identity.
  useEffect(() => {
    if (!authLoaded) {
      return;
    }
    if (!isSignedIn) {
      setClerkTokenGetter(null);
      return;
    }

    // Register the new getter immediately
    setClerkTokenGetter(async options => {
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

  // 2) Track active org only when signed in to avoid Clerk useOrganization
  //    dev warning on the sign-in page. Clear on unmount so HMR / layout
  //    swaps do not leak a stale org id into the module-scope bridge state.
  //    Account context is synchronously invalidated before replacement tenant
  //    authorization resolves, so presentation state cannot cross identities.
  if (!authLoaded || !isSignedIn) {
    return <>{children}</>;
  }

  return (
    <Fragment>
      <OrgSync resetAccountContext={authorizationIdentityChanged} />
      {children}
    </Fragment>
  );
}
