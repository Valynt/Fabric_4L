/**
 * Clerk + ValuePact Phase 2 frontend configuration.
 *
 * The frontend supports two auth providers, switched at build time via
 * VITE_AUTH_PROVIDER:
 *
 *   - "legacy" (default) — existing OIDC + httpOnly vf_session cookie path.
 *   - "clerk"            — Clerk-hosted sign-in/up; the API client attaches
 *                          a Clerk session JWT as Bearer to every request.
 *
 * Required env vars when AUTH_PROVIDER=clerk:
 *   VITE_CLERK_PUBLISHABLE_KEY     pk_test_... or pk_live_...
 *   VITE_CLERK_SIGN_IN_URL         default: "/sign-in"
 *   VITE_CLERK_SIGN_UP_URL         default: "/sign-up"
 *   VITE_CLERK_AFTER_SIGN_IN_URL   default: "/home"
 *   VITE_CLERK_AFTER_SIGN_UP_URL   default: "/home"
 *
 * Canonical Clerk defaults live in @fabric/platform-contract clerk-defaults.
 * The frontend and backend load the same file so defaults cannot diverge.
 *
 * SECURITY: the publishable key is safe to ship in the browser bundle.
 *           Never read CLERK_SECRET_KEY here — that is gateway-only and is
 *           enforced by the backend architecture sentinel.
 */

import clerkDefaults from "@fabric/platform-contract/clerk-defaults";

export const AUTH_PROVIDER_LEGACY = "legacy" as const;
export const AUTH_PROVIDER_CLERK = "clerk" as const;

export type AuthProvider =
  | typeof AUTH_PROVIDER_LEGACY
  | typeof AUTH_PROVIDER_CLERK;

/**
 * The configured auth provider for this build.
 *
 * Clerk is the canonical identity and organization boundary for Fabric_4L.
 * It is the default; legacy OIDC/cookie mode is opt-in only via
 * VITE_AUTH_PROVIDER=legacy and is intended for transitional use.
 */
export function getAuthProvider(): AuthProvider {
  const raw = (import.meta.env.VITE_AUTH_PROVIDER ?? "").toString().trim().toLowerCase();
  if (raw === AUTH_PROVIDER_LEGACY) return AUTH_PROVIDER_LEGACY;
  return AUTH_PROVIDER_CLERK;
}

export function isClerkAuthEnabled(): boolean {
  return getAuthProvider() === AUTH_PROVIDER_CLERK;
}

/**
 * Returns the Clerk publishable key when Clerk is enabled. Throws a helpful
 * error at runtime if Clerk is enabled but the key is missing or malformed.
 * Callers should gate this behind `isClerkAuthEnabled()` to avoid throwing
 * in legacy mode.
 */
const CLERK_PUBLISHABLE_KEY_RE = /^pk_(test|live)_[A-Za-z0-9]+$/;

export function getClerkPublishableKey(): string {
  const key = (import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ?? "").toString().trim();
  if (!key) {
    throw new Error(
      "VITE_CLERK_PUBLISHABLE_KEY is required when VITE_AUTH_PROVIDER=clerk. " +
        "Add it to your environment (Infisical: /apps/web)."
    );
  }
  if (!CLERK_PUBLISHABLE_KEY_RE.test(key)) {
    throw new Error(
      `VITE_CLERK_PUBLISHABLE_KEY has invalid format: expected pk_test_* or pk_live_*. ` +
        `Got prefix: ${key.slice(0, 12)}...`
    );
  }
  return key;
}

export function getClerkUrls() {
  return {
    signInUrl: (import.meta.env.VITE_CLERK_SIGN_IN_URL ?? clerkDefaults.clerk.signInUrl).toString(),
    signUpUrl: (import.meta.env.VITE_CLERK_SIGN_UP_URL ?? clerkDefaults.clerk.signUpUrl).toString(),
    afterSignInUrl: (import.meta.env.VITE_CLERK_AFTER_SIGN_IN_URL ?? clerkDefaults.clerk.afterSignInUrl).toString(),
    afterSignUpUrl: (import.meta.env.VITE_CLERK_AFTER_SIGN_UP_URL ?? clerkDefaults.clerk.afterSignUpUrl).toString(),
    selectOrgUrl: (import.meta.env.VITE_CLERK_SELECT_ORG_URL ?? "/workspaces").toString(),
  } as const;
}
