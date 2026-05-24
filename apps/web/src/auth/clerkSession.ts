/**
 * Bridge between Clerk's runtime session and the API client.
 *
 * Why this indirection: the axios interceptor in `src/api/client.ts` is a
 * non-React module that runs outside the React tree. It cannot call
 * `useAuth()` directly. The `<ClerkAuthBridge />` component subscribes to
 * Clerk via hooks and pushes the latest token-getter through this module
 * so the interceptor can synchronously fetch a fresh JWT per request.
 *
 * The token getter accepts an optional template name (Clerk JWT templates).
 * Production may want a dedicated template (e.g. "fabric4l") that pins the
 * audience claim to match the gateway's CLERK_JWT_AUDIENCE.
 */

export interface ClerkTokenGetterOptions {
  /**
   * Clerk JWT template name. When set, Clerk issues a token signed for the
   * template's configured audience. Default: undefined (Clerk session token).
   */
  template?: string;
  /**
   * If true, force Clerk to refresh the cached token even if not expired.
   */
  skipCache?: boolean;
}

export type ClerkTokenGetter = (
  options?: ClerkTokenGetterOptions,
) => Promise<string | null>;

let tokenGetter: ClerkTokenGetter | null = null;
let activeOrgId: string | null = null;

/**
 * Set by `<ClerkAuthBridge />` whenever the Clerk session changes.
 * Pass `null` to clear the bridge (sign-out, provider unmount).
 */
export function setClerkTokenGetter(getter: ClerkTokenGetter | null): void {
  tokenGetter = getter;
}

/**
 * Set by `<ClerkAuthBridge />` whenever the active organization changes.
 * The API client uses this only as an observability hint header
 * (`X-Tenant-ID`); the gateway always trusts the verified envelope, never
 * the header.
 */
export function setActiveClerkOrgId(orgId: string | null): void {
  activeOrgId = orgId;
}

export function getActiveClerkOrgId(): string | null {
  return activeOrgId;
}

/**
 * Fetch a Clerk session JWT for the current user. Returns null when:
 *   - the user is signed out,
 *   - Clerk hasn't finished loading,
 *   - or the bridge is not mounted (e.g. test environments without Clerk).
 */
export async function getClerkSessionToken(
  options?: ClerkTokenGetterOptions,
): Promise<string | null> {
  if (!tokenGetter) return null;
  try {
    return await tokenGetter(options);
  } catch {
    // Token retrieval can fail mid-rotation; let the request proceed without
    // a header so the interceptor's normal 401 handling (sign-in redirect)
    // takes over.
    return null;
  }
}

/**
 * Test helper. Resets all bridge state so tests can run in isolation.
 */
export function _resetClerkSessionForTests(): void {
  tokenGetter = null;
  activeOrgId = null;
}
