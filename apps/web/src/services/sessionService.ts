/**
 * SessionService — minimal redirect utilities for Clerk auth
 *
 * Legacy OIDC/cookie session management has been removed.
 * Clerk handles sessions, tokens, and refresh automatically.
 * This module now only provides navigation helpers for auth redirects.
 */

export class SessionService {
  redirectTo(url: string): void {
    if (typeof window !== 'undefined') {
      window.location.href = url;
    }
  }

  redirectToLogin(): void {
    const loc = typeof window !== 'undefined' ? window.location : null;
    if (!loc || loc.pathname === '/sign-in') return;
    try {
      loc.replace('/sign-in');
    } catch {
      /* noop */
    }
  }

  handleUnauthorized(context: { traceId?: string | null; route?: string } = {}): void {
    console.warn('Unauthorized response received', context);
    this.redirectToLogin();
  }
}

export const sessionService = new SessionService();
