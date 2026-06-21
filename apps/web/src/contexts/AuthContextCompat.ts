/**
 * Auth context compatibility layer — legacy OIDC / mock-auth state only.
 *
 * This module is intentionally separate from the live Clerk auth context so
 * legacy and dev-only compatibility code does not leak into the production
 * Clerk authentication path. The live AuthContext.tsx imports from here when
 * Clerk auth is disabled; it never touches these helpers in Clerk mode.
 */

import { type UserInfo } from '../schemas/auth';

export interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  currentTenantSlug: string | null;
  accessToken: null;
  initiateLogin: () => Promise<void>;
  handleCallback: () => Promise<boolean>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
}

// Mock identity for dev/test mode (using valid UUID format to match production expectations)
export const MOCK_USER_ID = '00000000-0000-0000-0000-000000000001';
export const MOCK_TENANT_ID = '00000000-0000-0000-0000-000000000001';
export const MOCK_TENANT_SLUG = 'demo';
export const MOCK_ACCOUNT_ID = '00000000-0000-0000-0000-000000000001';

export const MOCK_USER_INFO: UserInfo = {
  id: MOCK_USER_ID,
  email: 'demo@valuepact.ai',
  role: 'admin',
  tenantId: MOCK_TENANT_ID,
  tenantSlug: MOCK_TENANT_SLUG,
};

export function safeNavigate(path: string) {
  if (typeof window !== 'undefined') {
    window.location.href = path; // navigation-guardrail: ignore auth provider redirect fallback
  }
}

export function normalizeClerkRole(role: string | null | undefined): UserInfo['role'] {
  switch (role?.trim().toLowerCase()) {
    case 'admin':
    case 'org:admin':
      return 'tenant_admin';
    case 'basic_member':
    case 'org:member':
    case 'member':
      return 'analyst';
    case 'guest_member':
    case 'org:guest':
    case 'guest':
      return 'read_only';
    default:
      return 'analyst';
  }
}

export function isMockAuthEnabled(clerkMode: boolean): boolean {
  return import.meta.env.DEV && import.meta.env.VITE_ENABLE_MOCK_AUTH === 'true' && !clerkMode;
}

export function createLegacyAuthContextValue(mockAuthEnabled: boolean): AuthContextType {
  return {
    isAuthenticated: mockAuthEnabled,
    isLoading: false,
    user: mockAuthEnabled ? MOCK_USER_INFO : null,
    currentTenantSlug: mockAuthEnabled ? MOCK_TENANT_SLUG : null,
    accessToken: null,
    initiateLogin: async () => {
      if (mockAuthEnabled) return;
      safeNavigate('/login');
    },
    handleCallback: async () => true,
    logout: async () => {
      safeNavigate('/');
    },
    refreshToken: async () => true,
  };
}
