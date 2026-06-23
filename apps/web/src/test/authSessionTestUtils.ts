/**
 * Test utilities for auth fixtures.
 *
 * Legacy session service test helpers are retained as no-ops for test
 * compatibility while the codebase transitions to Clerk-only auth.
 */
import type { UserInfo } from '@/schemas/auth';

// ---------------------------------------------------------------------------
// No-op session environment (Clerk handles sessions automatically)
// ---------------------------------------------------------------------------

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

export interface SessionMeta {
  user: UserInfo;
  tenantId: string;
}

export interface OidcFlowState {
  state: string;
  tenantSlug: string;
  postLoginRedirect?: string;
}

export class MemoryStorage implements StorageLike {
  private store = new Map<string, string>();

  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }
}

export interface MutableLocationLike extends LocationLike {
  href: string;
  pathname: string;
}

export function createLocationMock(
  initialUrl = 'http://localhost:3000/'
): MutableLocationLike {
  const parsed = new URL(initialUrl);

  return {
    href: parsed.toString(),
    origin: parsed.origin,
    pathname: parsed.pathname,
    replace(url: string) {
      const nextUrl = new URL(url, this.origin);
      this.href = nextUrl.toString();
      this.pathname = nextUrl.pathname;
    },
  };
}

export function applySessionServiceTestEnvironment(_options: {
  sessionStorage?: MemoryStorage;
  location?: MutableLocationLike;
} = {}) {
  // No-op: Clerk handles sessions; legacy sessionService is stateless.
  const sessionStorage = _options.sessionStorage ?? new MemoryStorage();
  const location = _options.location ?? createLocationMock();

  return {
    sessionStorage,
    location,
    reset() {
      sessionStorage.clear();
      location.href = 'http://localhost:3000/';
      location.pathname = '/';
    },
  };
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const baseUser: UserInfo = {
  id: 'user-123',
  email: 'user@example.com',
  role: 'tenant_admin',
  tenantId: 'tenant-123',
  tenantSlug: 'tenant-123',
};

export const authFixtures = {
  user(overrides: Partial<UserInfo> = {}): UserInfo {
    return { ...baseUser, ...overrides };
  },

  sessionMeta(overrides: Partial<SessionMeta> = {}): SessionMeta {
    const user = overrides.user ?? baseUser;
    return {
      user,
      tenantId: overrides.tenantId ?? user.tenantId,
    };
  },

  validSession(overrides: Partial<SessionMeta> = {}): SessionMeta {
    return {
      user: overrides.user ?? baseUser,
      tenantId: overrides.tenantId ?? baseUser.tenantId,
    };
  },

  malformedUserPayload(): string {
    return 'invalid-json{';
  },

  oidcFlow(overrides: Partial<OidcFlowState> = {}): OidcFlowState {
    return {
      state: overrides.state ?? 'oidc-state-123',
      tenantSlug: overrides.tenantSlug ?? 'test-tenant',
      postLoginRedirect: overrides.postLoginRedirect,
    };
  },
};
