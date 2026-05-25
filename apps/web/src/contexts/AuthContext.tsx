/**
 * Auth Context — Clerk-only authentication state
 *
 * Thin wrapper around Clerk's useAuth/useUser hooks that exposes a
 * legacy-compatible interface so existing consumers (UnifiedRouteGuard,
 * AppHeader, settings pages) continue to work without modification.
 */

import { createContext, useContext, useMemo } from 'react';
import { useAuth as useClerkAuth, useUser as useClerkUser, useOrganization } from '@clerk/react';
import { createFeatureLogger } from '@/lib/telemetry';
import { type UserInfo, UserInfoSchema } from '../schemas/auth';

export type { UserInfo } from '../schemas/auth';

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
    window.location.href = path;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { isLoaded: authLoaded, isSignedIn } = useClerkAuth();
  const { isLoaded: userLoaded, user: clerkUser } = useClerkUser();
  const { organization } = useOrganization();

  const isLoading = !authLoaded || !userLoaded;

  const user: UserInfo | null = useMemo(() => {
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
      // Clerk doesn't support dev bypass in the same way as legacy auth
      // This is a no-op for Clerk mode but kept for interface compatibility
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
