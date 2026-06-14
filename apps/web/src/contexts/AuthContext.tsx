/**
 * Auth Context — Clerk-only authentication state with mock/dev mode
 *
 * Thin wrapper around Clerk's useAuth/useUser hooks that exposes a
 * legacy-compatible interface so existing consumers (UnifiedRouteGuard,
 * AppHeader, settings pages) continue to work without modification.
 *
 * Mock/dev mode: When VITE_ENABLE_MOCK_AUTH=true (dev/test only), provides
 * a mock authenticated user for local development and Playwright testing without
 * requiring real Clerk credentials. Production builds fail closed if this is enabled.
 */

import { createContext, useContext, useMemo } from 'react';
import { useAuth as useClerkAuth, useUser as useClerkUser, useOrganization } from '@clerk/react';
import { createFeatureLogger } from '@/lib/telemetry';
import { isClerkAuthEnabled } from '@/auth/clerkConfig';
import { type UserInfo, UserInfoSchema } from '../schemas/auth';

export type { UserInfo } from '../schemas/auth';

// Production guard: fail if mock auth is enabled in production builds
if (import.meta.env.PROD && import.meta.env.VITE_ENABLE_MOCK_AUTH === 'true') {
  throw new Error(
    'VITE_ENABLE_MOCK_AUTH is enabled in production build. ' +
    'Mock authentication is not allowed in production. ' +
    'Disable VITE_ENABLE_MOCK_AUTH and rebuild.'
  );
}

// Mock identity for dev/test mode (using valid UUID format to match production expectations)
const MOCK_USER_ID = '00000000-0000-0000-0000-000000000001';
const MOCK_TENANT_ID = '00000000-0000-0000-0000-000000000001';
const MOCK_TENANT_SLUG = 'demo';
const MOCK_ACCOUNT_ID = '00000000-0000-0000-0000-000000000001';

const MOCK_USER_INFO: UserInfo = {
  id: MOCK_USER_ID,
  email: 'demo@valuepact.ai',
  role: 'admin',
  tenantId: MOCK_TENANT_ID,
  tenantSlug: MOCK_TENANT_SLUG,
};

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  currentTenantSlug: string | null;
  accessToken: null;
  initiateLogin: () => Promise<void>;
  handleCallback: () => Promise<boolean>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  devBypass?: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
const log = createFeatureLogger('auth-context');

function safeNavigate(path: string) {
  if (typeof window !== 'undefined') {
    window.location.href = path; // navigation-guardrail: ignore auth provider redirect fallback
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Mock auth must never override Clerk auth state. If both are configured,
  // prefer Clerk and treat mock auth as disabled to avoid redirect loops.
  const clerkMode = isClerkAuthEnabled();
  const mockAuthEnabled = import.meta.env.DEV && import.meta.env.VITE_ENABLE_MOCK_AUTH === 'true' && !clerkMode;

  // Legacy / mock-auth path: do not call any Clerk hooks, because <ClerkProvider>
  // is not mounted in legacy mode. Calling them here crashes the app with
  // "useAuth can only be used within the <ClerkProvider /> component".
  if (!clerkMode) {
    const devBypass: AuthContextType['devBypass'] =
      import.meta.env.DEV || import.meta.env.MODE === 'test'
        ? () => {
            log.info('devBypass called in legacy auth mode - no-op');
          }
        : undefined;

    const value: AuthContextType = {
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
      ...(import.meta.env.DEV || import.meta.env.MODE === 'test' ? { devBypass } : {}),
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
  }

  // Clerk hooks (only used when Clerk is enabled)
  const { isLoaded: authLoaded, isSignedIn } = useClerkAuth();
  const { isLoaded: userLoaded, user: clerkUser } = useClerkUser();
  const { organization } = useOrganization();

  // Determine loading state and user info based on mode
  const isLoading = !authLoaded || !userLoaded;

  const user: UserInfo | null = useMemo(() => {
    // Clerk mode: map Clerk user to UserInfo
    if (!clerkUser) return null;

    // Users without organization membership are not fully authenticated for our multi-tenant app
    // They need to join or create an organization before accessing tenant-scoped features
    if (!organization || !organization.id || !organization.slug) {
      return null;
    }

    const primaryEmail = clerkUser.primaryEmailAddress?.emailAddress ?? '';

    // Map Clerk organization role to frontend tier
    // Clerk roles: 'admin', 'basic_member', 'guest_member'
    // Frontend tiers: 'standard', 'advanced', 'admin'
    let role: 'standard' | 'advanced' | 'admin' = 'standard';
    const orgMembership = clerkUser.organizationMemberships?.find(
      (m) => m.organization.id === organization.id
    );
    if (orgMembership?.role === 'admin') {
      role = 'admin';
    } else if (orgMembership?.role === 'basic_member') {
      role = 'standard';
    }

    const mapped: UserInfo = {
      id: clerkUser.id,
      email: primaryEmail,
      role,
      tenantId: organization.id,
      tenantSlug: organization.slug,
    };
    const parsed = UserInfoSchema.safeParse(mapped);
    return parsed.success ? parsed.data : null;
  }, [clerkUser, organization]);

  const currentTenantSlug = organization?.slug ?? null;

  const initiateLogin = async () => {
    safeNavigate('/sign-in');
  };

  const handleCallback = async () => {
    // Clerk handles OAuth callbacks internally; no-op here
    return true;
  };

  const logout = async () => {
    try {
      const { useClerk } = await import('@clerk/react');
      const clerk = useClerk();
      await clerk.signOut({ redirectUrl: '/' });
    } catch (error) {
      log.error('Sign out failed', { error: String(error) });
      safeNavigate('/');
    }
  };

  const refreshToken = async () => {
    // Clerk handles token refresh automatically
    return true;
  };

  /**
   * Local auth shortcut is compiled only into development and test bundles.
   * Production builds do not receive the implementation, mock identity, flag path,
   * or context field; this makes bypass leakage detectable by bundle scanning.
   */
  let devBypass: AuthContextType['devBypass'];

  if (import.meta.env.DEV || import.meta.env.MODE === 'test') {
    devBypass = () => {
      log.warn('devBypass called in Clerk mode - not supported');
    };
  }

  const value: AuthContextType = {
    isAuthenticated: authLoaded && !!isSignedIn,
    isLoading,
    user,
    currentTenantSlug,
    accessToken: null,
    initiateLogin,
    handleCallback,
    logout,
    refreshToken,
    ...(import.meta.env.DEV || import.meta.env.MODE === 'test' ? { devBypass } : {}),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}
