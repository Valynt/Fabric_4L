/**
 * Mock fixtures for authentication hook tests.
 *
 * This file provides reusable mock objects and test data for useAuth,
 * useRequireAuth, and useAuthRedirect hook tests. These fixtures eliminate
 * duplication and ensure consistency across auth-related tests.
 */

import { vi } from 'vitest';
import type { UserInfo } from '@/contexts/AuthContext';

// ---------------------------------------------------------------------------
// Base Mock Data
// ---------------------------------------------------------------------------

/**
 * Standard user info fixture for authenticated state.
 * Can be customized via the factory function below.
 */
const baseUserInfo: UserInfo = {
  id: 'user-1',
  email: 'test@example.com',
  role: 'standard',
  tenantId: 'tenant-1',
  tenantSlug: 'test-tenant',
};

/**
 * Auth context state factory.
 * Creates mock auth context objects with customizable state.
 */
export interface AuthContextState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  /** @deprecated Token is in the httpOnly cookie; always null. */
  accessToken: null;
  initiateLogin: ReturnType<typeof import('vitest').vi.fn>;
  handleCallback: ReturnType<typeof import('vitest').vi.fn>;
  logout: ReturnType<typeof import('vitest').vi.fn>;
  refreshToken: ReturnType<typeof import('vitest').vi.fn>;
}

/**
 * Factory function to create auth context mock objects.
 * @param overrides - Optional partial state to override defaults
 * @returns A complete auth context mock object
 */
export function createAuthContextMock(
  overrides: Partial<AuthContextState> = {}
): AuthContextState {
  return {
    isAuthenticated: false,
    isLoading: false,
    user: null,
    accessToken: null, // Always null - token is in httpOnly cookie
    initiateLogin: vi.fn(),
    handleCallback: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    ...overrides,
  };
}

/**
 * Pre-configured auth context states for common test scenarios.
 */
export const authContextFixtures = {
  /**
   * Authenticated user state with full user info.
   */
  authenticated: (user: UserInfo = baseUserInfo): AuthContextState =>
    createAuthContextMock({
      isAuthenticated: true,
      isLoading: false,
      user,
      accessToken: null,
    }),

  /**
   * Unauthenticated state (not logged in).
   */
  unauthenticated: (): AuthContextState =>
    createAuthContextMock({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      accessToken: null,
    }),

  /**
   * Loading state (auth check in progress).
   */
  loading: (): AuthContextState =>
    createAuthContextMock({
      isAuthenticated: false,
      isLoading: true,
      user: null,
      accessToken: null,
    }),

  /**
   * Authenticated with custom user info.
   */
  withUser: (user: UserInfo): AuthContextState =>
    createAuthContextMock({
      isAuthenticated: true,
      isLoading: false,
      user,
      accessToken: null,
    }),
};

/**
 * User info fixtures for common user types.
 */
export const userFixtures = {
  /**
   * Standard user with default values.
   */
  standard: (overrides: Partial<UserInfo> = {}): UserInfo => ({
    ...baseUserInfo,
    ...overrides,
  }),

  /**
   * Admin user with elevated role.
   */
  admin: (overrides: Partial<UserInfo> = {}): UserInfo =>
    userFixtures.standard({
      role: 'admin',
      ...overrides,
    }),

  /**
   * Tenant admin user.
   */
  tenantAdmin: (overrides: Partial<UserInfo> = {}): UserInfo =>
    userFixtures.standard({
      role: 'tenant_admin',
      ...overrides,
    }),

  /**
   * Minimal user object for basic tests.
   */
  minimal: (): UserInfo => ({
    id: 'user-1',
    email: 'test@example.com',
    role: 'standard',
    tenantId: 'tenant-1',
    tenantSlug: 'test-tenant',
  }),
};

/**
 * CSRF token fixtures for cookie tests.
 */
export const csrfFixtures = {
  /**
   * Valid CSRF token value.
   */
  validToken: 'test-csrf-abc123',

  /**
   * Another valid CSRF token for token rotation tests.
   */
  rotatedToken: 'test-csrf-xyz789',

  /**
   * Empty CSRF token (absent cookie).
   */
  empty: '',
};

/**
 * Navigation path fixtures for redirect tests.
 */
export const pathFixtures = {
  /**
   * Protected route that requires authentication.
   */
  protected: '/protected',

  /**
   * Login page with workflow step parameter.
   */
  login: '/login?wfStep=0',

  /**
   * Dashboard route (authenticated user destination).
   */
  dashboard: '/dashboard',

  /**
   * Settings page.
   */
  settings: '/settings',
};
