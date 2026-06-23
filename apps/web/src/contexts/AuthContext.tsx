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
import { useAuth as useClerkAuth, useUser as useClerkUser, useOrganization, useClerk } from '@clerk/react';
import { createFeatureLogger } from '@/lib/telemetry';
import { isClerkAuthEnabled } from '@/auth/clerkConfig';
import { getClerkTenantRouteSlug } from '@/auth/clerkTenant';
import { UserInfoSchema, type UserInfo } from '../schemas/auth';
import {
  type AuthContextType,
  createLegacyAuthContextValue,
  isMockAuthEnabled,
  normalizeClerkRole,
  safeNavigate,
} from './AuthContextCompat';

export type { UserInfo } from '../schemas/auth';

// Production guard: fail if mock auth is enabled in production builds
if (import.meta.env.PROD && import.meta.env.VITE_ENABLE_MOCK_AUTH === 'true') {
  throw new Error(
    'VITE_ENABLE_MOCK_AUTH is enabled in production build. ' +
    'Mock authentication is not allowed in production. ' +
    'Disable VITE_ENABLE_MOCK_AUTH and rebuild.'
  );
}

export const AuthContext = createContext<import('./AuthContextCompat').AuthContextType | undefined>(undefined);
const log = createFeatureLogger('auth-context');

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Mock auth must never override Clerk auth state. If both are configured,
  // prefer Clerk and treat mock auth as disabled to avoid redirect loops.
  const clerkMode = isClerkAuthEnabled();
  const mockAuthEnabled = isMockAuthEnabled(clerkMode);

  // Legacy / mock-auth path: do not call any Clerk hooks, because <ClerkProvider>
  // is not mounted in legacy mode. Calling them here crashes the app with
  // "useAuth can only be used within the <ClerkProvider /> component".
  if (!clerkMode) {
    return <AuthContext.Provider value={createLegacyAuthContextValue(mockAuthEnabled)}>{children}</AuthContext.Provider>;
  }

  return <ClerkAuthProvider>{children}</ClerkAuthProvider>;
}

function ClerkAuthProvider({ children }: { children: React.ReactNode }) {
  const { isLoaded: authLoaded, isSignedIn } = useClerkAuth();
  const { isLoaded: userLoaded, user: clerkUser } = useClerkUser();
  const { signOut } = useClerk();

  const initiateLogin = async () => {
    safeNavigate('/sign-in');
  };

  const handleCallback = async () => {
    // Clerk handles OAuth callbacks internally; no-op here
    return true;
  };

  const logout = async () => {
    try {
      await signOut({ redirectUrl: '/' });
    } catch (error) {
      log.error('Sign out failed', { error: String(error) });
      safeNavigate('/');
    }
  };

  const refreshToken = async () => {
    // Clerk handles token refresh automatically
    return true;
  };

  if (!authLoaded || !userLoaded || !isSignedIn) {
    const value: AuthContextType = {
      isAuthenticated: authLoaded && !!isSignedIn,
      isLoading: !authLoaded || !userLoaded,
      user: null,
      currentTenantSlug: null,
      accessToken: null,
      initiateLogin,
      handleCallback,
      logout,
      refreshToken,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
  }

  return (
    <SignedInClerkAuthProvider
      clerkUser={clerkUser}
      initiateLogin={initiateLogin}
      handleCallback={handleCallback}
      logout={logout}
      refreshToken={refreshToken}
    >
      {children}
    </SignedInClerkAuthProvider>
  );
}

function SignedInClerkAuthProvider({
  children,
  clerkUser,
  initiateLogin,
  handleCallback,
  logout,
  refreshToken,
}: {
  children: React.ReactNode;
  clerkUser: ReturnType<typeof useClerkUser>['user'];
  initiateLogin: AuthContextType['initiateLogin'];
  handleCallback: AuthContextType['handleCallback'];
  logout: AuthContextType['logout'];
  refreshToken: AuthContextType['refreshToken'];
}) {
  const { organization, isLoaded: organizationLoaded } = useOrganization();

  const user: UserInfo | null = useMemo(() => {
    // Clerk mode: map Clerk user to UserInfo
    if (!clerkUser) return null;

    // Users without organization membership are not fully authenticated for our multi-tenant app.
    // Clerk org slug can be absent for newly-created orgs, so tenant routes fall back to org id.
    const tenantRouteSlug = getClerkTenantRouteSlug(organization);
    if (!organization || !organization.id || !tenantRouteSlug) {
      return null;
    }

    const primaryEmail = clerkUser.primaryEmailAddress?.emailAddress ?? '';

    const orgMembership = clerkUser.organizationMemberships?.find(
      (m) => m.organization.id === organization.id
    );
    const role = normalizeClerkRole(orgMembership?.role);

    const mapped: UserInfo = {
      id: clerkUser.id,
      email: primaryEmail,
      role,
      tenantId: organization.id,
      tenantSlug: tenantRouteSlug,
    };
    const parsed = UserInfoSchema.safeParse(mapped);
    return parsed.success ? parsed.data : null;
  }, [clerkUser, organization]);

  const currentTenantSlug = getClerkTenantRouteSlug(organization);

  const value: AuthContextType = {
    isAuthenticated: true,
    isLoading: !organizationLoaded,
    user,
    currentTenantSlug,
    accessToken: null,
    initiateLogin,
    handleCallback,
    logout,
    refreshToken,
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
