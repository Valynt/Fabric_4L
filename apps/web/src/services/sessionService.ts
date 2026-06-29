/**
 * SessionService — minimal redirect utilities for Clerk auth
 *
 * Legacy OIDC/cookie session management has been removed.
 * Clerk handles sessions, tokens, and refresh automatically.
 * This module now only provides navigation helpers for auth redirects.
 */

import { logWarn } from "@/lib/telemetry";
import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

function buildRedirectPath(loc: Location, signInUrl: string): string | null {
  if (
    loc.pathname.startsWith(signInUrl) ||
    loc.pathname.startsWith("/sso-callback")
  ) {
    return null;
  }

  return `${loc.pathname}${loc.search ?? ""}${loc.hash ?? ""}`;
}

export class SessionService {
  redirectTo(url: string): void {
    if (typeof window !== "undefined") {
      window.location.href = url; // navigation-guardrail: ignore external Clerk redirect target
    }
  }

  redirectToLogin(): void {
    const loc = typeof window !== "undefined" ? window.location : null;
    if (!loc) return;

    if (isClerkAuthEnabled()) {
      const urls = getClerkUrls();
      if (!loc.pathname.startsWith(urls.signInUrl)) {
        const redirectPath = buildRedirectPath(loc, urls.signInUrl);
        const destination = redirectPath
          ? `${urls.signInUrl}?redirect_url=${encodeURIComponent(redirectPath)}`
          : urls.signInUrl;
        try {
          loc.replace(destination);
        } catch {
          /* noop */
        }
      }
      return;
    }

    if (loc.pathname.startsWith("/sign-in")) return;
    try {
      loc.replace("/sign-in");
    } catch {
      /* noop */
    }
  }

  handleUnauthorized(
    context: { traceId?: string | null; route?: string } = {}
  ): void {
    logWarn("Unauthorized response received", context);
    this.redirectToLogin();
  }

  handleForbidden(
    context: { traceId?: string | null; route?: string } = {}
  ): void {
    logWarn("Forbidden response received", context);
    const loc = typeof window !== "undefined" ? window.location : null;
    if (!loc) return;
    if (loc.pathname === "/forbidden") return;
    try {
      loc.replace("/forbidden");
    } catch {
      /* noop */
    }
  }
}

export const sessionService = new SessionService();
