/**
 * SessionService — minimal redirect utilities for Clerk auth
 *
 * Legacy OIDC/cookie session management has been removed.
 * Clerk handles sessions, tokens, and refresh automatically.
 * This module now only provides navigation helpers for auth redirects.
 */

import { logWarn } from "@/lib/telemetry";
import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

export class SessionService {
  redirectTo(url: string): void {
    if (typeof window !== 'undefined') {
      window.location.href = url; // navigation-guardrail: ignore external Clerk redirect target
    }
  }

  redirectToLogin(): void {
    const loc = typeof window !== 'undefined' ? window.location : null;
    if (!loc) return;

    if (isClerkAuthEnabled()) {
      const urls = getClerkUrls();
      if (loc.pathname !== urls.selectOrgUrl) {
        try {
          loc.replace(urls.selectOrgUrl);
        } catch {
          /* noop */
        }
      }
      return;
    }

    if (loc.pathname.startsWith('/sign-in')) return;
    try {
      loc.replace('/sign-in');
    } catch {
      /* noop */
    }
  }

  handleUnauthorized(context: { traceId?: string | null; route?: string } = {}): void {
    logWarn('Unauthorized response received', context);
    this.redirectToLogin();
  }
}

export const sessionService = new SessionService();
