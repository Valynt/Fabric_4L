/**
 * Test utilities for auth and session service tests.
 *
 * The session service no longer uses localStorage — tokens live in the
 * httpOnly cookie (backend-managed) and only non-secret metadata is kept
 * in sessionStorage.  These utilities reflect that model.
 */
import { sessionService, type LocationLike, type SessionMeta, type StorageLike, type OidcFlowState } from '@/services/sessionService';
import type { UserInfo } from '@/schemas/auth';

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

export function applySessionServiceTestEnvironment(options: {
  sessionStorage?: MemoryStorage;
  location?: MutableLocationLike;
} = {}) {
  const sessionStorage = options.sessionStorage ?? new MemoryStorage();
  const location = options.location ?? createLocationMock();

  sessionService.configure({ sessionStorage, location });

  return {
    sessionStorage,
    location,
    reset() {
      sessionStorage.clear();
      location.href = 'http://localhost:3000/';
      location.pathname = '/';
      sessionService.configure({ sessionStorage, location });
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

  /** Returns a well-formed SessionMeta for tests that seed localStorage. */
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
