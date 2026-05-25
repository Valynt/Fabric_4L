/**
 * SessionService — cookie-based session management
 *
 * The access token is stored exclusively in the httpOnly Secure SameSite=Strict
 * `vf_session` cookie set by the backend. This file never reads or writes that
 * cookie — it is invisible to JavaScript by design.
 *
 * What this service manages:
 *   - Non-secret session metadata (user info, tenantId) in sessionStorage so
 *     the UI can render without a round-trip.
 *   - OIDC flow state (state, tenantSlug, postLoginRedirect) in sessionStorage
 *     for the duration of the authorization code exchange.
 *
 * The API client sends credentials automatically via `withCredentials: true`,
 * so no token attachment is needed here.
 */
import { z } from 'zod';
import { createFeatureLogger } from '@/lib/telemetry';
import { type UserInfo, UserInfoSchema } from '../schemas/auth';
import { isClerkAuthEnabled } from '@/auth/clerkConfig';

const log = createFeatureLogger('auth-session');

// sessionStorage keys
const SESSION_META_KEY = 'vf.auth.session.meta';
const OIDC_STORAGE_KEY = 'vf.auth.oidc';

// Legacy keys — read-only migration; never written after this version
const LEGACY_OIDC_STATE_KEY = 'oidcState';
const LEGACY_OIDC_TENANT_KEY = 'oidcTenantSlug';
const LEGACY_POST_LOGIN_REDIRECT_KEY = 'postLoginRedirect';

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export interface LocationLike {
  href: string;
  origin: string;
  pathname: string;
  replace(url: string): void;
}

export interface SessionServiceEnvironment {
  sessionStorage: StorageLike | null;
  location: LocationLike | null;
}

/**
 * Non-secret session metadata stored in sessionStorage.
 * Never contains the access token.
 */
const SessionMetaSchema = z.object({
  user: UserInfoSchema,
  tenantId: z.string().min(1, 'Tenant ID is required'),
});

const OidcFlowStateSchema = z.object({
  state: z.string().min(1, 'State is required'),
  tenantSlug: z.string().min(1, 'Tenant slug is required'),
  postLoginRedirect: z.string().min(1).optional(),
});

export type SessionMeta = z.infer<typeof SessionMetaSchema>;
export type OidcFlowState = z.infer<typeof OidcFlowStateSchema>;

function getWindowStorage(kind: 'sessionStorage'): StorageLike | null {
  if (typeof window === 'undefined') return null;
  return window[kind];
}

function getWindowLocation(): LocationLike | null {
  if (typeof window === 'undefined') return null;
  return window.location;
}

export class SessionService {
  private environment: SessionServiceEnvironment;

  constructor(environment: Partial<SessionServiceEnvironment> = {}) {
    this.environment = {
      sessionStorage: environment.sessionStorage ?? getWindowStorage('sessionStorage'),
      location: environment.location ?? getWindowLocation(),
    };
  }

  configure(environment: Partial<SessionServiceEnvironment>): void {
    this.environment = {
      sessionStorage: environment.sessionStorage ?? this.environment.sessionStorage,
      location: environment.location ?? this.environment.location,
    };
  }

  resetEnvironment(): void {
    this.environment = {
      sessionStorage: getWindowStorage('sessionStorage'),
      location: getWindowLocation(),
    };
  }

  // ---------------------------------------------------------------------------
  // Session metadata (user info + tenantId — no token)
  // ---------------------------------------------------------------------------

  getSessionMeta(): SessionMeta | null {
    const ss = this.environment.sessionStorage;
    if (!ss) return null;

    const raw = ss.getItem(SESSION_META_KEY);
    if (!raw) return null;

    const result = SessionMetaSchema.safeParse(this.safeParseJson(raw));
    if (!result.success) {
      this.clearSession();
      return null;
    }
    return result.data;
  }

  /**
   * Persist non-secret session metadata after a successful OIDC callback.
   * The access token is NOT stored here — it lives in the httpOnly cookie.
   */
  persistSessionMeta(user: UserInfo, tenantId: string): SessionMeta {
    const meta = SessionMetaSchema.parse({ user, tenantId });
    this.environment.sessionStorage?.setItem(SESSION_META_KEY, JSON.stringify(meta));
    return meta;
  }

  clearSession(): void {
    const ss = this.environment.sessionStorage;
    if (!ss) return;
    ss.removeItem(SESSION_META_KEY);
  }

  getCurrentUser(): UserInfo | null {
    return this.getSessionMeta()?.user ?? null;
  }

  /**
   * @deprecated Token is in the httpOnly cookie; always returns null.
   * Kept so the API client interceptor compiles — the cookie is sent automatically.
   */
  getAccessToken(): string | null {
    return null;
  }

  getTenantId(defaultTenantId = 'default'): string {
    return this.getSessionMeta()?.tenantId ?? defaultTenantId;
  }

  /**
   * Session validity is determined by the backend (cookie expiry).
   * Returns true when session metadata is present; the backend will return 401
   * when the cookie has expired.
   */
  isSessionValid(): boolean {
    return !!this.getSessionMeta();
  }

  // ---------------------------------------------------------------------------
  // OIDC flow state
  // ---------------------------------------------------------------------------

  persistOidcFlowState(flowState: OidcFlowState): OidcFlowState {
    const parsed = OidcFlowStateSchema.parse(flowState);
    this.environment.sessionStorage?.setItem(OIDC_STORAGE_KEY, JSON.stringify(parsed));
    return parsed;
  }

  getOidcFlowState(): OidcFlowState | null {
    const ss = this.environment.sessionStorage;
    if (!ss) return null;

    const stored = ss.getItem(OIDC_STORAGE_KEY);
    if (stored) {
      const result = OidcFlowStateSchema.safeParse(this.safeParseJson(stored));
      if (result.success) return result.data;
      this.clearOidcState();
      return null;
    }

    // Migrate legacy keys (read-once, then rewrite under new key)
    const state = ss.getItem(LEGACY_OIDC_STATE_KEY);
    const tenantSlug = ss.getItem(LEGACY_OIDC_TENANT_KEY);
    const postLoginRedirect = ss.getItem(LEGACY_POST_LOGIN_REDIRECT_KEY) ?? undefined;

    if (!state || !tenantSlug) {
      if (state || tenantSlug || postLoginRedirect) this.clearOidcState();
      return null;
    }

    return this.persistOidcFlowState({ state, tenantSlug, postLoginRedirect });
  }

  setPostLoginRedirect(redirect: string | null): void {
    const current = this.getOidcFlowState();
    if (current) {
      this.persistOidcFlowState({ ...current, postLoginRedirect: redirect ?? undefined });
      return;
    }
    const ss = this.environment.sessionStorage;
    if (!ss) return;
    if (redirect) {
      ss.setItem(LEGACY_POST_LOGIN_REDIRECT_KEY, redirect);
    } else {
      ss.removeItem(LEGACY_POST_LOGIN_REDIRECT_KEY);
    }
  }

  consumePostLoginRedirect(): string | null {
    const current = this.getOidcFlowState();
    const redirect =
      current?.postLoginRedirect ??
      this.environment.sessionStorage?.getItem(LEGACY_POST_LOGIN_REDIRECT_KEY) ??
      null;

    if (current) {
      this.persistOidcFlowState({ state: current.state, tenantSlug: current.tenantSlug });
    } else {
      this.environment.sessionStorage?.removeItem(LEGACY_POST_LOGIN_REDIRECT_KEY);
    }

    return redirect;
  }

  clearOidcState(): void {
    const ss = this.environment.sessionStorage;
    if (!ss) return;
    ss.removeItem(OIDC_STORAGE_KEY);
    ss.removeItem(LEGACY_OIDC_STATE_KEY);
    ss.removeItem(LEGACY_OIDC_TENANT_KEY);
    ss.removeItem(LEGACY_POST_LOGIN_REDIRECT_KEY);
  }

  // ---------------------------------------------------------------------------
  // Navigation helpers
  // ---------------------------------------------------------------------------

  getCallbackUrl(): string {
    return `${this.environment.location?.origin ?? ''}/login/callback`;
  }

  redirectTo(url: string): void {
    const loc = this.environment.location;
    if (loc) loc.href = url;
  }

  redirectToLogin(): void {
    const loc = this.environment.location;
    const loginPath = isClerkAuthEnabled() ? '/sign-in' : '/login';
    if (!loc || loc.pathname === loginPath) return;
    try {
      loc.replace(loginPath); // navigation-guardrail: ignore - service boundary auth redirect
    } catch (error) {
      log.warn('Login redirect failed after unauthorized response', {
        route: loc.pathname,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  handleUnauthorized(context: { traceId?: string | null; route?: string } = {}): void {
    const meta = this.getSessionMeta();
    log.warn('Unauthorized response received; clearing session', {
      route: context.route ?? this.environment.location?.pathname,
      tenantId: meta?.tenantId ?? null,
      userId: meta?.user.id ?? null,
      authPhase: 'unauthorized-response',
      traceId: context.traceId ?? null,
    });
    this.clearSession();
    this.redirectToLogin();
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  private safeParseJson(raw: string): unknown {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
}

export const sessionService = new SessionService();
